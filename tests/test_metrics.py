from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from citemap.dataset import load_dataset
from citemap.graph import build_citation_graph
from citemap.metrics import network_summary, rank_papers
from citemap.models import Paper


def test_two_node_pagerank_matches_analytical_solution() -> None:
    """A cites B. Solving the PageRank equations by hand with d = 0.85
    (B is dangling and redistributes uniformly) gives
    p(B) = 0.13875 / 0.21375 and p(A) = 1 - p(B).
    """
    graph = build_citation_graph([Paper("A", "a", references=("B",)), Paper("B", "b")])
    ranking = {r.id: r.pagerank for r in rank_papers(graph, top=None)}
    expected_b = 0.13875 / 0.21375
    assert ranking["B"] == pytest.approx(expected_b, abs=1e-6)
    assert ranking["A"] == pytest.approx(1 - expected_b, abs=1e-6)


def test_scores_form_a_probability_distribution(sample_path: Path) -> None:
    graph = build_citation_graph(load_dataset(sample_path))
    ranking = rank_papers(graph, top=None)
    assert len(ranking) == 14
    assert sum(r.pagerank for r in ranking) == pytest.approx(1.0)
    assert all(r.pagerank > 0 for r in ranking)


def test_most_cited_foundational_paper_ranks_first(sample_path: Path) -> None:
    graph = build_citation_graph(load_dataset(sample_path))
    top = rank_papers(graph, top=1)[0]
    assert top.id == "P01"
    assert top.local_citations == 4
    assert top.global_citations == 5200


def test_pagerank_differs_from_raw_citation_count(sample_path: Path) -> None:
    """P02 and P03 have the same local citation count, but P03 is cited by
    papers that are themselves cited more, so PageRank puts it higher."""
    graph = build_citation_graph(load_dataset(sample_path))
    order = [r.id for r in rank_papers(graph, top=None)]
    assert graph.in_degree("P02") == graph.in_degree("P03") == 3
    assert order.index("P03") < order.index("P02")


def test_ties_are_broken_deterministically() -> None:
    papers = [
        Paper("Z", "z", references=("X",)),
        Paper("Y", "y", references=("X",)),
        Paper("X", "x"),
    ]
    ids = [r.id for r in rank_papers(build_citation_graph(papers), top=None)]
    assert ids == ["X", "Y", "Z"]


def test_top_limits_results(small_papers: list[Paper]) -> None:
    graph = build_citation_graph(small_papers)
    assert len(rank_papers(graph, top=2)) == 2
    assert len(rank_papers(graph, top=None)) == 4


def test_empty_graph_gives_empty_ranking() -> None:
    assert rank_papers(nx.DiGraph()) == []


@pytest.mark.parametrize(
    ("kwargs", "message"), [({"damping": 1.0}, "damping"), ({"top": 0}, "top")]
)
def test_invalid_arguments(
    small_papers: list[Paper], kwargs: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        rank_papers(build_citation_graph(small_papers), **kwargs)  # type: ignore[arg-type]


def test_summary_of_sample(sample_path: Path) -> None:
    summary = network_summary(build_citation_graph(load_dataset(sample_path)))
    assert summary.papers == 14
    assert summary.citations == 26
    assert summary.components == 1
    assert summary.isolated_papers == 0
    assert (summary.year_min, summary.year_max) == (1998, 2023)
    assert summary.density == pytest.approx(26 / (14 * 13))


def test_summary_counts_isolated_papers_and_unknown_years(small_papers: list[Paper]) -> None:
    papers = [*small_papers, Paper("E", "lonely")]
    summary = network_summary(build_citation_graph(papers))
    assert summary.isolated_papers == 1
    assert summary.components == 2
    assert (summary.year_min, summary.year_max) == (2000, 2020)


def test_summary_of_empty_graph() -> None:
    summary = network_summary(nx.DiGraph())
    assert (summary.papers, summary.citations, summary.components) == (0, 0, 0)
    assert summary.density == 0.0
    assert summary.year_min is None
