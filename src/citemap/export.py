"""Export of graphs and rankings to formats consumed by other tools.

* Graph JSON uses the ``nodes`` / ``links`` layout understood directly by
  D3.js force layouts and easily mapped to Cytoscape.js, so the CiteMap
  frontend can render it without further transformation.
* Rankings are written as CSV so they open in a spreadsheet or can be
  imported into a reference manager.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import networkx as nx

from citemap.metrics import RankedPaper

CSV_COLUMNS = ("rank", "id", "title", "year", "pagerank", "local_citations", "global_citations")


def to_graph_json(graph: nx.DiGraph[str]) -> dict[str, Any]:
    """Convert a citation graph into a ``{"nodes": [...], "links": [...]}`` structure."""
    nodes = []
    for node in sorted(graph.nodes):
        data = graph.nodes[node]
        nodes.append(
            {
                "id": node,
                "title": data.get("title", ""),
                "year": data.get("year"),
                "authors": list(data.get("authors", ())),
                "cited_by_count": data.get("cited_by_count", 0),
                "local_citations": int(graph.in_degree(node)),
            }
        )
    links = [{"source": s, "target": t} for s, t in sorted(graph.edges())]
    return {"nodes": nodes, "links": links}


def write_graph_json(graph: nx.DiGraph[str], path: str | Path) -> None:
    """Write the graph JSON to a file."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(to_graph_json(graph), indent=2, ensure_ascii=False)
    file_path.write_text(text + "\n", encoding="utf-8")


def write_ranking_csv(ranking: Iterable[RankedPaper], path: str | Path) -> None:
    """Write a ranking to a UTF-8 CSV file with a header row."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for position, item in enumerate(ranking, start=1):
            writer.writerow(
                [
                    position,
                    item.id,
                    item.title,
                    "" if item.year is None else item.year,
                    f"{item.pagerank:.6f}",
                    item.local_citations,
                    item.global_citations,
                ]
            )
