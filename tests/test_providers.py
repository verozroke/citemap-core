from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from citemap.providers import (
    JsonFileProvider,
    OpenAlexProvider,
    ProviderError,
    normalise_work_id,
    work_to_paper,
)


def work(work_id: str, refs: list[str] | None = None, cited: int = 0) -> dict[str, Any]:
    """Minimal OpenAlex Work object."""
    return {
        "id": f"https://openalex.org/{work_id}",
        "display_name": f"Title {work_id}",
        "publication_year": 2020,
        "cited_by_count": cited,
        "authorships": [{"author": {"display_name": f"Author {work_id}"}}],
        "referenced_works": [f"https://openalex.org/{r}" for r in refs or []],
    }


class FakeOpenAlex:
    """Stands in for the HTTP layer and records every requested URL."""

    def __init__(self, works: dict[str, dict[str, Any]], citing: list[str]) -> None:
        self.works = works
        self.citing = citing
        self.urls: list[str] = []

    def __call__(self, url: str) -> Mapping[str, Any]:
        self.urls.append(url)
        parsed = urlparse(url)
        if parsed.path.startswith("/works/"):
            return self.works[parsed.path.rsplit("/", 1)[-1]]
        flt = parse_qs(parsed.query)["filter"][0]
        if flt.startswith("openalex:"):
            ids = flt.removeprefix("openalex:").split("|")
            return {"results": [self.works[i] for i in ids if i in self.works]}
        if flt.startswith("cites:"):
            return {"results": [self.works[i] for i in self.citing]}
        raise AssertionError(f"unexpected request {url}")


# ---------------------------------------------------------------- JSON adapter
def test_json_provider_returns_ego_network(sample_path: Path) -> None:
    papers = JsonFileProvider(sample_path).fetch_network("P04")
    assert {p.id for p in papers} == {"P04", "P01", "P02", "P07", "P08", "P10"}


def test_json_provider_unknown_seed(sample_path: Path) -> None:
    with pytest.raises(ProviderError, match="not present"):
        JsonFileProvider(sample_path).fetch_network("NOPE")


# ---------------------------------------------------------------- mapping
@pytest.mark.parametrize(
    "raw", ["W123", "w123", "https://openalex.org/W123", " https://openalex.org/W123/ "]
)
def test_normalise_work_id(raw: str) -> None:
    assert normalise_work_id(raw) == "W123"


@pytest.mark.parametrize("raw", ["", "123", "A123", "https://openalex.org/authors/A1"])
def test_normalise_work_id_rejects_garbage(raw: str) -> None:
    with pytest.raises(ProviderError):
        normalise_work_id(raw)


def test_work_to_paper_maps_fields() -> None:
    paper = work_to_paper(work("W1", refs=["W2", "W3"], cited=9))
    assert paper.id == "W1"
    assert paper.title == "Title W1"
    assert paper.year == 2020
    assert paper.authors == ("Author W1",)
    assert paper.cited_by_count == 9
    assert paper.references == ("W2", "W3")


def test_work_to_paper_tolerates_missing_fields() -> None:
    raw = {
        "id": "https://openalex.org/W9",
        "title": None,
        "display_name": None,
        "authorships": [{"author": None}, {"author": {"display_name": "Kept"}}],
        "cited_by_count": None,
    }
    paper = work_to_paper(raw)
    assert paper.title == "(untitled)"
    assert paper.year is None
    assert paper.authors == ("Kept",)
    assert paper.cited_by_count == 0
    assert paper.references == ()


# ---------------------------------------------------------------- OpenAlex adapter
def test_openalex_fetches_seed_references_and_citing() -> None:
    works = {
        "W1": work("W1", refs=["W2", "W3"]),
        "W2": work("W2"),
        "W3": work("W3"),
        "W4": work("W4", refs=["W1"], cited=10),
    }
    fake = FakeOpenAlex(works, citing=["W4", "W2"])  # W2 is duplicated on purpose
    provider = OpenAlexProvider(api_key="", http_get=fake)

    papers = provider.fetch_network("https://openalex.org/W1")

    assert [p.id for p in papers] == ["W1", "W2", "W3", "W4"]
    assert len(fake.urls) == 3
    assert "filter=openalex:W2|W3" in fake.urls[1]
    assert "filter=cites:W1" in fake.urls[2]
    assert "sort=cited_by_count:desc" in fake.urls[2]


def test_openalex_sends_key_and_mailto() -> None:
    fake = FakeOpenAlex({"W1": work("W1")}, citing=[])
    OpenAlexProvider(api_key="secret", mailto="me@example.org", http_get=fake).fetch_network("W1")
    query = parse_qs(urlparse(fake.urls[0]).query)
    assert query["api_key"] == ["secret"]
    assert query["mailto"] == ["me@example.org"]


def test_openalex_reads_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "from-env")
    fake = FakeOpenAlex({"W1": work("W1")}, citing=[])
    OpenAlexProvider(http_get=fake).fetch_network("W1")
    assert "api_key=from-env" in fake.urls[0]


def test_openalex_splits_large_reference_lists() -> None:
    refs = [f"W{i}" for i in range(100, 350)]  # 250 references -> 3 batches
    works = {"W1": work("W1", refs=refs), **{r: work(r) for r in refs}}
    fake = FakeOpenAlex(works, citing=[])
    papers = OpenAlexProvider(api_key="", http_get=fake).fetch_network("W1")
    batch_calls = [u for u in fake.urls if "filter=openalex:" in u]
    assert len(batch_calls) == 3
    assert len(papers) == 251


@pytest.mark.parametrize("value", [0, 101])
def test_openalex_rejects_bad_max_citing(value: int) -> None:
    with pytest.raises(ValueError, match="max_citing"):
        OpenAlexProvider(max_citing=value)


@pytest.mark.network
def test_openalex_live_smoke() -> None:  # pragma: no cover - needs internet
    papers = OpenAlexProvider(max_citing=5).fetch_network("W2741809807")
    assert papers[0].id == "W2741809807"
    assert len(papers) > 1
