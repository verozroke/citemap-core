"""Construction and filtering of directed citation graphs.

Edges point from the citing paper to the cited paper, so a paper's in-degree is
the number of times it is cited *inside* the network.
"""

from __future__ import annotations

from collections.abc import Iterable

import networkx as nx

from citemap.models import Paper


def build_citation_graph(papers: Iterable[Paper]) -> nx.DiGraph[str]:
    """Build a directed citation graph from papers.

    Rules:
        * Only references to papers present in the input become edges;
          references that point outside the dataset are ignored.
        * Self-citations are ignored.
        * If the same id appears more than once, the first record is kept.
    """
    graph: nx.DiGraph[str] = nx.DiGraph()
    ordered: list[Paper] = []
    for paper in papers:
        if paper.id in graph:
            continue
        graph.add_node(
            paper.id,
            title=paper.title,
            year=paper.year,
            authors=paper.authors,
            cited_by_count=paper.cited_by_count,
        )
        ordered.append(paper)

    for paper in ordered:
        for ref in paper.references:
            if ref != paper.id and ref in graph:
                graph.add_edge(paper.id, ref)
    return graph


def filter_by_year(
    graph: nx.DiGraph[str],
    start: int | None = None,
    end: int | None = None,
) -> nx.DiGraph[str]:
    """Return a copy of the graph restricted to papers published in ``[start, end]``.

    When at least one bound is given, papers with an unknown year are excluded,
    because they cannot be shown to satisfy the bound.
    """
    if start is not None and end is not None and start > end:
        raise ValueError(f"start year {start} is after end year {end}")
    if start is None and end is None:
        return graph.copy()

    keep = []
    for node, data in graph.nodes(data=True):
        year = data.get("year")
        if year is None:
            continue
        if (start is None or year >= start) and (end is None or year <= end):
            keep.append(node)
    return graph.subgraph(keep).copy()


def filter_by_min_citations(graph: nx.DiGraph[str], minimum: int) -> nx.DiGraph[str]:
    """Return a copy of the graph with papers whose global citation count is >= ``minimum``."""
    if minimum < 0:
        raise ValueError("minimum citation count must be >= 0")
    keep = [node for node, data in graph.nodes(data=True) if data["cited_by_count"] >= minimum]
    return graph.subgraph(keep).copy()
