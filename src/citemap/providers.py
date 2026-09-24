"""Data providers: the only place where CiteMap knows where data comes from.

This module implements the *ports and adapters* idea from the CiteMap
architecture. :class:`CitationProvider` is the port. Two adapters implement it:

* :class:`JsonFileProvider` reads an offline dataset file. It is used in tests,
  in continuous integration and for fully reproducible analyses.
* :class:`OpenAlexProvider` talks to the public OpenAlex API. Its HTTP call is
  injectable, so tests never touch the network.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from citemap import __version__
from citemap.dataset import load_dataset
from citemap.models import Paper

OPENALEX_BASE_URL = "https://api.openalex.org"
OPENALEX_MAX_OR_VALUES = 100
_WORK_ID = re.compile(r"^W\d+$")

JsonGetter = Callable[[str], Mapping[str, Any]]


class ProviderError(RuntimeError):
    """Raised when a provider cannot return the requested network."""


class CitationProvider(Protocol):
    """Port: anything that can return the citation neighbourhood of a paper."""

    def fetch_network(self, seed_id: str) -> list[Paper]:
        """Return the seed paper, the papers it cites and papers that cite it."""
        ...


class JsonFileProvider:
    """Adapter that reads a local dataset file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def fetch_network(self, seed_id: str) -> list[Paper]:
        papers = load_dataset(self._path)
        by_id = {p.id: p for p in papers}
        if seed_id not in by_id:
            raise ProviderError(f"Paper {seed_id!r} is not present in {self._path}")

        seed = by_id[seed_id]
        keep = {seed_id}
        keep.update(ref for ref in seed.references if ref in by_id)
        keep.update(p.id for p in papers if seed_id in p.references)
        return [p for p in papers if p.id in keep]


def normalise_work_id(value: str) -> str:
    """Accept ``W123`` or ``https://openalex.org/W123`` and return ``W123``."""
    candidate = value.strip().rstrip("/").rsplit("/", 1)[-1].upper()
    if not _WORK_ID.match(candidate):
        raise ProviderError(f"Not a valid OpenAlex work id: {value!r}")
    return candidate


def work_to_paper(work: Mapping[str, Any]) -> Paper:
    """Map an OpenAlex *Work* object to a :class:`Paper`."""
    authorships = work.get("authorships") or []
    authors = tuple(
        str(a["author"]["display_name"])
        for a in authorships
        if isinstance(a, Mapping) and a.get("author") and a["author"].get("display_name")
    )
    references = tuple(normalise_work_id(r) for r in work.get("referenced_works") or [])
    return Paper(
        id=normalise_work_id(str(work["id"])),
        title=str(work.get("display_name") or work.get("title") or "(untitled)"),
        year=work.get("publication_year"),
        authors=authors,
        cited_by_count=int(work.get("cited_by_count") or 0),
        references=references,
    )


def _chunks(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


class OpenAlexProvider:
    """Adapter for the OpenAlex REST API (https://api.openalex.org).

    Args:
        api_key: Optional OpenAlex API key. Falls back to the
            ``OPENALEX_API_KEY`` environment variable. Requests work without a
            key, but with a much smaller daily budget.
        mailto: Optional contact e-mail sent with each request, as OpenAlex
            recommends for polite use of the API.
        max_citing: How many citing works to request (1..100). The most cited
            citing works are returned first.
        http_get: Function that takes a URL and returns decoded JSON. Injected
            in tests; defaults to a small ``urllib`` based client.
    """

    def __init__(
        self,
        api_key: str | None = None,
        mailto: str | None = None,
        max_citing: int = 50,
        timeout: float = 30.0,
        http_get: JsonGetter | None = None,
    ) -> None:
        if not 1 <= max_citing <= OPENALEX_MAX_OR_VALUES:
            raise ValueError(f"max_citing must be between 1 and {OPENALEX_MAX_OR_VALUES}")
        self._api_key = api_key if api_key is not None else os.environ.get("OPENALEX_API_KEY")
        self._mailto = mailto
        self._max_citing = max_citing
        self._timeout = timeout
        self._http_get: JsonGetter = http_get or self._urllib_get

    def fetch_network(self, seed_id: str) -> list[Paper]:
        work_id = normalise_work_id(seed_id)
        seed = work_to_paper(self._get(f"/works/{work_id}"))

        papers: dict[str, Paper] = {seed.id: seed}
        for paper in self._fetch_by_ids(list(seed.references)):
            papers.setdefault(paper.id, paper)
        for paper in self._fetch_citing(work_id):
            papers.setdefault(paper.id, paper)
        return list(papers.values())

    # -- internal helpers -------------------------------------------------

    def _fetch_by_ids(self, ids: Sequence[str]) -> list[Paper]:
        result: list[Paper] = []
        for chunk in _chunks(ids, OPENALEX_MAX_OR_VALUES):
            payload = self._get(
                "/works",
                {"filter": "openalex:" + "|".join(chunk), "per_page": str(len(chunk))},
            )
            result.extend(work_to_paper(w) for w in payload.get("results", []))
        return result

    def _fetch_citing(self, work_id: str) -> list[Paper]:
        payload = self._get(
            "/works",
            {
                "filter": f"cites:{work_id}",
                "per_page": str(self._max_citing),
                "sort": "cited_by_count:desc",
            },
        )
        return [work_to_paper(w) for w in payload.get("results", [])]

    def _get(self, path: str, params: Mapping[str, str] | None = None) -> Mapping[str, Any]:
        query = dict(params or {})
        if self._api_key:
            query["api_key"] = self._api_key
        if self._mailto:
            query["mailto"] = self._mailto
        url = OPENALEX_BASE_URL + path
        if query:
            url += "?" + urlencode(query, safe=":|,", quote_via=quote)
        return self._http_get(url)

    def _urllib_get(self, url: str) -> Mapping[str, Any]:  # pragma: no cover - real network
        request = Request(url, headers={"User-Agent": f"citemap-core/{__version__}"})
        try:
            with urlopen(request, timeout=self._timeout) as response:
                data: Mapping[str, Any] = json.loads(response.read().decode("utf-8"))
                return data
        except HTTPError as exc:
            if exc.code == 429:
                raise ProviderError(
                    "OpenAlex rate limit reached (HTTP 429). Wait and retry, or set "
                    "OPENALEX_API_KEY to use the larger keyed budget."
                ) from exc
            raise ProviderError(f"OpenAlex returned HTTP {exc.code} for {url}") from exc
        except URLError as exc:
            raise ProviderError(f"Could not reach OpenAlex: {exc.reason}") from exc
