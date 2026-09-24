"""Network level metrics: influence ranking and summary statistics."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass(frozen=True)
class RankedPaper:
    """A paper together with its influence scores inside the network."""

    id: str
    title: str
    year: int | None
    pagerank: float
    local_citations: int
    global_citations: int


@dataclass(frozen=True)
class NetworkSummary:
    """Descriptive statistics of a citation network."""

    papers: int
    citations: int
    density: float
    components: int
    isolated_papers: int
    year_min: int | None
    year_max: int | None


def rank_papers(
    graph: nx.DiGraph[str],
    top: int | None = 10,
    damping: float = 0.85,
) -> list[RankedPaper]:
    """Rank papers by PageRank on the citation graph.

    PageRank rewards papers that are cited by other influential papers, which
    is a better signal of structural importance than a raw citation count.
    Ties are broken by local citations and then by id, so the order is fully
    deterministic and reproducible.

    Args:
        graph: Citation graph with edges from citing to cited paper.
        top: Maximum number of results, or ``None`` for all papers.
        damping: PageRank damping factor, strictly between 0 and 1.
    """
    if not 0.0 < damping < 1.0:
        raise ValueError("damping must be strictly between 0 and 1")
    if top is not None and top < 1:
        raise ValueError("top must be a positive integer or None")
    if graph.number_of_nodes() == 0:
        return []

    scores: dict[str, float] = nx.pagerank(graph, alpha=damping)
    ranked = [
        RankedPaper(
            id=node,
            title=str(data.get("title", "")),
            year=data.get("year"),
            pagerank=scores[node],
            local_citations=int(graph.in_degree(node)),
            global_citations=int(data.get("cited_by_count", 0)),
        )
        for node, data in graph.nodes(data=True)
    ]
    ranked.sort(key=lambda r: (-round(r.pagerank, 12), -r.local_citations, r.id))
    return ranked if top is None else ranked[:top]


def network_summary(graph: nx.DiGraph[str]) -> NetworkSummary:
    """Compute descriptive statistics of the network."""
    years: list[int] = [d["year"] for _, d in graph.nodes(data=True) if d.get("year") is not None]
    papers = graph.number_of_nodes()
    return NetworkSummary(
        papers=papers,
        citations=graph.number_of_edges(),
        density=nx.density(graph) if papers > 1 else 0.0,
        components=nx.number_weakly_connected_components(graph) if papers else 0,
        isolated_papers=sum(1 for _ in nx.isolates(graph)),
        year_min=min(years) if years else None,
        year_max=max(years) if years else None,
    )
