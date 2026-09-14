"""Scenario generator determinism and the compare command."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from elevator_sim.__main__ import main
from elevator_sim.compare import Variant, load_manifest, run_matrix

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scenarios"))
import generate  # noqa: E402


def test_generator_is_deterministic_and_matches_committed_files():
    for t in generate.SCENARIOS:
        rows = generate.generate(t)
        assert rows == generate.generate(t)
        committed = (ROOT / "scenarios" / f"{t.name}.csv").read_text().splitlines()[1:]
        assert committed == [f"{a},{b},{c},{d}" for a, b, c, d in rows]


def test_generated_requests_are_valid_for_their_building():
    for t in generate.SCENARIOS:
        for time, _, source, dest in generate.generate(t):
            assert time >= 0
            assert 1 <= source <= t.floors and 1 <= dest <= t.floors
            assert source != dest


def test_manifest_lists_every_scenario_file():
    scenarios = load_manifest(ROOT / "scenarios" / "manifest.json")
    names = {s.name for s in scenarios}
    assert "sample" in names
    assert {t.name for t in generate.SCENARIOS} <= names
    assert all(s.file.exists() for s in scenarios)


def test_run_matrix_serves_everyone_with_every_scheduler():
    scenarios = [
        s
        for s in load_manifest(ROOT / "scenarios" / "manifest.json")
        if s.name in {"sample", "capacity_stress"}
    ]
    rows = run_matrix(
        scenarios,
        [
            Variant("etd"),
            Variant("nearest_car"),
            Variant("round_robin"),
            Variant("etd", fairness=0.5),
        ],
    )
    assert len(rows) == 8
    for r in rows:
        assert r["wait"]["count"] == r["passengers"]
        assert r["total"]["count"] == r["passengers"]
        assert not any("not delivered" in o for o in r["observations"])
    labels = {r["scheduler"] for r in rows}
    assert labels == {"etd", "nearest_car", "round_robin", "etd_f0.5"}


def test_compare_cli_writes_outputs(tmp_path, capsys):
    code = main(
        [
            "compare",
            "--manifest",
            str(ROOT / "scenarios" / "manifest.json"),
            "--scenario",
            "sample",
            "--out",
            str(tmp_path),
            "--traces",
        ]
    )
    assert code == 0
    rows = json.loads((tmp_path / "comparison.json").read_text())
    assert {r["scheduler"] for r in rows} == {"etd", "nearest_car", "round_robin"}
    assert (tmp_path / "comparison.md").exists()
    assert (tmp_path / "traces" / "sample__etd.json").exists()
    assert "sample" in capsys.readouterr().out


def test_run_cli_rejects_invalid_input(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    bad.write_text("time,id,source,dest\n0,a,5,5\n")
    assert main(["run", str(bad), "--out", str(tmp_path / "o")]) == 2
    assert "source and dest are both 5" in capsys.readouterr().err


def test_report_renders_charts_when_matplotlib_is_available(tmp_path):
    import pytest

    pytest.importorskip("matplotlib")
    from elevator_sim.report import build_report

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "name": "morning_up_peak",
                    "file": str(ROOT / "scenarios" / "morning_up_peak.csv"),
                    "floors": 20,
                    "elevators": 4,
                    "capacity": 8,
                }
            ]
        )
    )
    written = build_report(manifest, tmp_path / "charts", fairness=[0.5])
    names = {p.name for p in written}
    assert "wait_by_scenario.png" in names
    assert "wait_distribution_morning_up_peak.png" in names
    assert "positions_morning_up_peak_etd.png" in names
    assert "fairness_sweep_morning_up_peak.png" in names
    assert all(p.stat().st_size > 1000 for p in written)
