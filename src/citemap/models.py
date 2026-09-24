"""Core data model: a single paper in a citation network."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

MIN_YEAR = 1600
MAX_YEAR = 2100


@dataclass(frozen=True)
class Paper:
    """A scholarly work and the identifiers of the works it references.

    Attributes:
        id: Stable identifier of the work, for example an OpenAlex ID ``W2741809807``.
        title: Human readable title.
        year: Publication year, or ``None`` when unknown.
        authors: Author display names in the order given by the source.
        cited_by_count: Global citation count reported by the source. This is
            the count across the whole literature, not only inside the network.
        references: Identifiers of the works this paper cites.
    """

    id: str
    title: str
    year: int | None = None
    authors: tuple[str, ...] = ()
    cited_by_count: int = 0
    references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("Paper id must be a non-empty string")
        if self.cited_by_count < 0:
            raise ValueError(f"cited_by_count must be >= 0 for paper {self.id!r}")
        if self.year is not None and not MIN_YEAR <= self.year <= MAX_YEAR:
            raise ValueError(
                f"year {self.year} of paper {self.id!r} is outside {MIN_YEAR}..{MAX_YEAR}"
            )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Paper:
        """Build a paper from a plain mapping, as stored in a dataset file."""
        missing = [key for key in ("id", "title") if key not in data]
        if missing:
            raise ValueError(f"Paper record is missing required field(s): {', '.join(missing)}")

        year = data.get("year")
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            year=int(year) if year is not None else None,
            authors=tuple(str(a) for a in data.get("authors", ())),
            cited_by_count=int(data.get("cited_by_count", 0)),
            references=tuple(str(r) for r in data.get("references", ())),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the paper to a JSON friendly dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "year": self.year,
            "authors": list(self.authors),
            "cited_by_count": self.cited_by_count,
            "references": list(self.references),
        }
