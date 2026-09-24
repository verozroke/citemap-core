from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from citemap import cli
from citemap.models import Paper


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_summary(capsys: pytest.CaptureFixture[str], sample_path: Path) -> None:
    code, out, _ = run(capsys, "summary", str(sample_path))
    assert code == 0
    assert "papers            14" in out
    assert "years             1998..2023" in out


def test_summary_of_empty_selection(capsys: pytest.CaptureFixture[str], sample_path: Path) -> None:
    code, out, _ = run(capsys, "summary", str(sample_path), "--from-year", "2090")
    assert code == 0
    assert "years             n/a" in out


def test_rank_with_filters_and_csv(
    capsys: pytest.CaptureFixture[str], sample_path: Path, tmp_path: Path
) -> None:
    csv_path = tmp_path / "rank.csv"
    code, out, _ = run(
        capsys,
        "rank",
        str(sample_path),
        "--top",
        "3",
        "--from-year",
        "2010",
        "--min-citations",
        "100",
        "--csv",
        str(csv_path),
    )
    assert code == 0
    assert len([line for line in out.splitlines() if line[:3].strip().isdigit()]) == 3
    assert csv_path.read_text(encoding="utf-8").startswith("rank,id,title")


def test_rank_shows_unknown_year(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    dataset = tmp_path / "d.json"
    dataset.write_text(json.dumps({"papers": [{"id": "A", "title": "No year"}]}), encoding="utf-8")
    code, out, _ = run(capsys, "rank", str(dataset))
    assert code == 0
    assert "----" in out


def test_export(capsys: pytest.CaptureFixture[str], sample_path: Path, tmp_path: Path) -> None:
    target = tmp_path / "graph.json"
    code, out, _ = run(capsys, "export", str(sample_path), "--out", str(target))
    assert code == 0
    assert "14 papers, 26 links" in out
    assert len(json.loads(target.read_text(encoding="utf-8"))["nodes"]) == 14


def test_fetch_uses_openalex_provider(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeProvider:
        def __init__(self, mailto: str | None, max_citing: int) -> None:
            assert mailto == "me@example.org"
            assert max_citing == 5

        def fetch_network(self, seed_id: str) -> list[Paper]:
            return [Paper(seed_id, "Seed"), Paper("W2", "Ref")]

    monkeypatch.setattr(cli, "OpenAlexProvider", FakeProvider)
    target = tmp_path / "net.json"
    code, out, _ = run(
        capsys,
        "fetch",
        "W1",
        "--out",
        str(target),
        "--mailto",
        "me@example.org",
        "--max-citing",
        "5",
    )
    assert code == 0
    assert "2 papers saved" in out
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["meta"] == {"source": "OpenAlex", "seed": "W1"}


@pytest.mark.parametrize(
    "argv",
    [
        ["summary", "missing.json"],
        ["summary", "{sample}", "--from-year", "2020", "--to-year", "2000"],
        ["rank", "{sample}", "--top", "0"],
    ],
)
def test_errors_exit_with_code_1(
    capsys: pytest.CaptureFixture[str], sample_path: Path, argv: list[str]
) -> None:
    code, _, err = run(capsys, *[a.replace("{sample}", str(sample_path)) for a in argv])
    assert code == 1
    assert err.startswith("error:")


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert "citemap" in capsys.readouterr().out


def test_module_entry_point(sample_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "citemap", "summary", str(sample_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "papers            14" in result.stdout
