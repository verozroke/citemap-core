from __future__ import annotations

from pathlib import Path

import pytest

from citemap.dataset import load_dataset
from citemap.graph import build_citation_graph, filter_by_min_citations, filter_by_year
from citemap.models import Paper


def test_edges_point_from_citing_to_cited(small_papers: list[Paper]) -> None:
    graph = build_citation_graph(small_papers)
    assert set(graph.edges()) == {("B", "A"), ("C", "B"), ("D", "A")}


def test_references_outside_the_dataset_are_ignored(small_papers: list[Paper]) -> None:
    graph = build_citation_graph(small_papers)
    assert "EXT" not in graph


def test_self_citations_are_ignored() -> None:
    graph = build_citation_graph([Paper("A", "a", references=("A",))])
    assert graph.number_of_edges() == 0


def test_duplicate_ids_keep_first_record() -> None:
    first = Paper("A", "first", cited_by_count=1)
    second = Paper("A", "second", cited_by_count=2)
    graph = build_citation_graph([first, second])
    assert graph.number_of_nodes() == 1
    assert graph.nodes["A"]["title"] == "first"


def test_node_attributes_are_copied(small_papers: list[Paper]) -> None:
    graph = build_citation_graph(small_papers)
    assert graph.nodes["B"] == {
        "title": "Beta",
        "year": 2010,
        "authors": (),
        "cited_by_count": 50,
    }


def test_sample_network_shape(sample_path: Path) -> None:
    graph = build_citation_graph(load_dataset(sample_path))
    assert graph.number_of_nodes() == 14
    assert graph.number_of_edges() == 26  # X99 is outside the dataset
    assert graph.in_degree("P01") == 4


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (None, None, {"A", "B", "C", "D"}),
        (2005, None, {"B", "C"}),
        (None, 2010, {"A", "B"}),
        (2005, 2015, {"B"}),
    ],
)
def test_filter_by_year(
    small_papers: list[Paper], start: int | None, end: int | None, expected: set[str]
) -> None:
    graph = build_citation_graph(small_papers)
    assert set(filter_by_year(graph, start, end)) == expected


def test_filter_by_year_returns_independent_copy(small_papers: list[Paper]) -> None:
    graph = build_citation_graph(small_papers)
    filtered = filter_by_year(graph)
    filtered.remove_node("A")
    assert "A" in graph


def test_filter_by_year_rejects_inverted_range(small_papers: list[Paper]) -> None:
    with pytest.raises(ValueError, match="after"):
        filter_by_year(build_citation_graph(small_papers), 2020, 2000)


def test_filter_by_min_citations(small_papers: list[Paper]) -> None:
    graph = build_citation_graph(small_papers)
    filtered = filter_by_min_citations(graph, 50)
    assert set(filtered) == {"A", "B"}
    assert set(filtered.edges()) == {("B", "A")}


def test_filter_by_min_citations_rejects_negative(small_papers: list[Paper]) -> None:
    with pytest.raises(ValueError, match=">= 0"):
        filter_by_min_citations(build_citation_graph(small_papers), -1)
