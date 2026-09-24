from __future__ import annotations

import json
from pathlib import Path

import pytest

from citemap.dataset import DatasetError, load_dataset, save_dataset
from citemap.models import Paper


def test_load_sample_dataset(sample_path: Path) -> None:
    papers = load_dataset(sample_path)
    assert len(papers) == 14
    assert papers[0].id == "P01"
    assert all(isinstance(p, Paper) for p in papers)


def test_save_and_load_round_trip(tmp_path: Path, small_papers: list[Paper]) -> None:
    target = tmp_path / "nested" / "out.json"
    save_dataset(reversed(small_papers), target, meta={"source": "test"})

    raw = json.loads(target.read_text(encoding="utf-8"))
    assert raw["meta"] == {"source": "test"}
    assert [p["id"] for p in raw["papers"]] == ["A", "B", "C", "D"]  # sorted by id
    assert load_dataset(target) == small_papers


def test_save_preserves_unicode(tmp_path: Path) -> None:
    target = tmp_path / "u.json"
    save_dataset([Paper("W1", "Қазақ тілі и граф цитирования")], target)
    assert "Қазақ" in target.read_text(encoding="utf-8")


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="not found"):
        load_dataset(tmp_path / "absent.json")


def test_invalid_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(DatasetError, match="not valid JSON"):
        load_dataset(bad)


@pytest.mark.parametrize("content", ["[]", '{"papers": {}}', '{"items": []}'])
def test_wrong_top_level_shape(tmp_path: Path, content: str) -> None:
    bad = tmp_path / "shape.json"
    bad.write_text(content, encoding="utf-8")
    with pytest.raises(DatasetError, match="'papers' list"):
        load_dataset(bad)


def test_record_that_is_not_an_object(tmp_path: Path) -> None:
    bad = tmp_path / "rec.json"
    bad.write_text('{"papers": ["P01"]}', encoding="utf-8")
    with pytest.raises(DatasetError, match="#0"):
        load_dataset(bad)


def test_invalid_record_reports_its_index(tmp_path: Path) -> None:
    bad = tmp_path / "rec.json"
    records = [{"id": "A", "title": "ok"}, {"id": "B", "title": "x", "cited_by_count": -5}]
    bad.write_text(json.dumps({"papers": records}), encoding="utf-8")
    with pytest.raises(DatasetError, match="#1"):
        load_dataset(bad)
