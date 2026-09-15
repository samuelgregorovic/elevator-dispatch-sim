"""The committed comparison table is a golden file.

Every number quoted in the README, DESIGN.md, the whitepaper and the deck comes
from docs/results/comparison.json. This test re-runs the matrix and compares the
statistics field by field, so that any change in engine behaviour forces the
documents to be regenerated rather than silently orphaning their figures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from elevator_sim.compare import Variant, load_manifest, run_matrix

ROOT = Path(__file__).parent.parent
COMMITTED = json.loads((ROOT / "docs" / "results" / "comparison.json").read_text())
FIELDS = ("passengers", "ticks", "wait", "total", "cars", "balance")


@pytest.fixture(scope="module")
def fresh() -> dict[tuple[str, str], dict]:
    scenarios = load_manifest(ROOT / "scenarios" / "manifest.json")
    variants = [Variant(s) for s in ("etd", "nearest_car", "nearest_car_balanced", "round_robin")]
    variants.append(Variant("etd", fairness=0.5))
    return {(r["scenario"], r["scheduler"]): r for r in run_matrix(scenarios, variants)}


@pytest.mark.parametrize("row", COMMITTED, ids=lambda r: f"{r['scenario']}-{r['scheduler']}")
def test_committed_comparison_regenerates(row, fresh):
    key = (row["scenario"], row["scheduler"])
    assert key in fresh, "a committed row no longer exists; regenerate docs/results"
    for field in FIELDS:
        assert fresh[key][field] == row[field], f"{key} {field} drifted; regenerate docs/results"


def test_no_uncommitted_rows(fresh):
    assert {(r["scenario"], r["scheduler"]) for r in COMMITTED} == set(fresh)
