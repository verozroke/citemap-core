from __future__ import annotations

import pytest

from citemap.models import Paper


def test_from_dict_full_record() -> None:
    paper = Paper.from_dict(
        {
            "id": "W1",
            "title": "T",
            "year": 2021,
            "authors": ["A", "B"],
            "cited_by_count": 7,
            "references": ["W2"],
        }
    )
    assert paper == Paper("W1", "T", 2021, ("A", "B"), 7, ("W2",))


def test_from_dict_minimal_record_uses_defaults() -> None:
    paper = Paper.from_dict({"id": "W1", "title": "T"})
    assert paper.year is None
    assert paper.authors == ()
    assert paper.cited_by_count == 0
    assert paper.references == ()


def test_to_dict_round_trip() -> None:
    original = Paper("W1", "T", 1999, ("A",), 3, ("W0",))
    assert Paper.from_dict(original.to_dict()) == original


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"id": "", "title": "T"}, "non-empty"),
        ({"id": "   ", "title": "T"}, "non-empty"),
        ({"id": "W1", "title": "T", "cited_by_count": -1}, "cited_by_count"),
        ({"id": "W1", "title": "T", "year": 1200}, "outside"),
        ({"id": "W1", "title": "T", "year": 2500}, "outside"),
    ],
)
def test_invalid_papers_are_rejected(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Paper(**kwargs)  # type: ignore[arg-type]


def test_from_dict_reports_missing_fields() -> None:
    with pytest.raises(ValueError, match="id, title"):
        Paper.from_dict({"year": 2000})


def test_paper_is_immutable() -> None:
    paper = Paper("W1", "T")
    with pytest.raises(AttributeError):
        paper.title = "changed"  # type: ignore[misc]
