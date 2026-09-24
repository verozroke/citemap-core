from __future__ import annotations

from pathlib import Path

import pytest

from citemap.models import Paper

SAMPLE_DATASET = Path(__file__).resolve().parents[1] / "data" / "sample_network.json"


@pytest.fixture
def sample_path() -> Path:
    return SAMPLE_DATASET


@pytest.fixture
def small_papers() -> list[Paper]:
    """Four papers: C cites B, B cites A, D cites A and an external paper."""
    return [
        Paper(id="A", title="Alpha", year=2000, cited_by_count=100),
        Paper(id="B", title="Beta", year=2010, cited_by_count=50, references=("A",)),
        Paper(id="C", title="Gamma", year=2020, cited_by_count=5, references=("B",)),
        Paper(id="D", title="Delta", year=None, cited_by_count=0, references=("A", "EXT")),
    ]
