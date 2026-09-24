"""Reading and writing citation datasets stored as JSON files.

File format::

    {
      "meta": {"source": "...", "description": "..."},
      "papers": [
        {"id": "P01", "title": "...", "year": 2019, "authors": ["..."],
         "cited_by_count": 42, "references": ["P00"]}
      ]
    }

The ``meta`` block is optional and is preserved for provenance.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from citemap.models import Paper


class DatasetError(ValueError):
    """Raised when a dataset file cannot be parsed into papers."""


def load_dataset(path: str | Path) -> list[Paper]:
    """Load all papers from a dataset file."""
    file_path = Path(path)
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DatasetError(f"Dataset file not found: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise DatasetError(f"Dataset file is not valid JSON: {file_path} ({exc})") from exc

    if not isinstance(raw, Mapping) or not isinstance(raw.get("papers"), list):
        raise DatasetError(f"Dataset must be an object with a 'papers' list: {file_path}")

    papers: list[Paper] = []
    for index, record in enumerate(raw["papers"]):
        if not isinstance(record, Mapping):
            raise DatasetError(f"Record #{index} in {file_path} is not an object")
        try:
            papers.append(Paper.from_dict(record))
        except (TypeError, ValueError) as exc:
            raise DatasetError(f"Record #{index} in {file_path} is invalid: {exc}") from exc
    return papers


def save_dataset(
    papers: Iterable[Paper],
    path: str | Path,
    meta: Mapping[str, Any] | None = None,
) -> None:
    """Write papers to a dataset file with stable ordering by id."""
    payload: dict[str, Any] = {
        "meta": dict(meta or {}),
        "papers": [p.to_dict() for p in sorted(papers, key=lambda p: p.id)],
    }
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
