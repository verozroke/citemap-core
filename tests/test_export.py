from __future__ import annotations

import csv
import json
from pathlib import Path

from citemap.export import CSV_COLUMNS, to_graph_json, write_graph_json, write_ranking_csv
from citemap.graph import build_citation_graph
from citemap.metrics import RankedPaper, rank_papers
from citemap.models import Paper


def test_graph_json_structure(small_papers: list[Paper]) -> None:
    data = to_graph_json(build_citation_graph(small_papers))
    assert [n["id"] for n in data["nodes"]] == ["A", "B", "C", "D"]
    assert data["links"] == [
        {"source": "B", "target": "A"},
        {"source": "C", "target": "B"},
        {"source": "D", "target": "A"},
    ]
    node_a = data["nodes"][0]
    assert node_a["local_citations"] == 2
    assert node_a["cited_by_count"] == 100


def test_every_link_endpoint_is_a_node(small_papers: list[Paper]) -> None:
    data = to_graph_json(build_citation_graph(small_papers))
    ids = {n["id"] for n in data["nodes"]}
    assert all(link["source"] in ids and link["target"] in ids for link in data["links"])


def test_write_graph_json(tmp_path: Path, small_papers: list[Paper]) -> None:
    graph = build_citation_graph(small_papers)
    target = tmp_path / "out" / "graph.json"
    write_graph_json(graph, target)
    assert json.loads(target.read_text(encoding="utf-8")) == to_graph_json(graph)


def test_write_ranking_csv(tmp_path: Path, small_papers: list[Paper]) -> None:
    ranking = rank_papers(build_citation_graph(small_papers), top=None)
    target = tmp_path / "ranking.csv"
    write_ranking_csv(ranking, target)

    with target.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert tuple(rows[0]) == CSV_COLUMNS
    assert len(rows) == 1 + len(ranking)
    assert rows[1][0] == "1"
    assert rows[1][1] == ranking[0].id


def test_csv_handles_unknown_year_and_unicode(tmp_path: Path) -> None:
    item = RankedPaper("W1", 'Граф, "цитат"', None, 0.5, 1, 2)
    target = tmp_path / "r.csv"
    write_ranking_csv([item], target)
    with target.open(encoding="utf-8", newline="") as handle:
        row = list(csv.reader(handle))[1]
    assert row[2] == 'Граф, "цитат"'
    assert row[3] == ""
    assert row[4] == "0.500000"
