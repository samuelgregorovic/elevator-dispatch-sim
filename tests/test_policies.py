"""Bonus policies: fairness weight, express cars, park-at-lobby.

The last three tests are empirical: they pin findings from the committed
scenarios (see docs/DESIGN.md) so that a change in behaviour is noticed. Only
findings that also held across fresh seeds (docs/results/robustness.md) are
pinned.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import req, run
from elevator_sim.compare import Variant, load_manifest, parse_floors, run_matrix
from elevator_sim.schedulers import ETDScheduler, make_scheduler
from elevator_sim.schedulers.base import NoFeasibleCarError

ROOT = Path(__file__).parent.parent
MANIFEST = ROOT / "scenarios" / "manifest.json"


def scenario(name):
    return next(s for s in load_manifest(MANIFEST) if s.name == name)


def test_parse_floors():
    assert parse_floors("1,27-30") == {1, 27, 28, 29, 30}
    assert parse_floors("5") == {5}


def test_fairness_weight_names_the_variant_and_rejects_negative():
    assert ETDScheduler().name == "etd"
    assert ETDScheduler(fairness=0.5).name == "etd_f0.5"
    assert make_scheduler("etd", fairness=1).name == "etd_f1"
    with pytest.raises(ValueError):
        ETDScheduler(fairness=-1)


def test_fairness_weight_protects_a_long_waiting_passenger():
    # One car at floor 1. "old" has waited at floor 10 (down) for a while; a burst of new
    # lobby passengers going up arrives. With fairness, the delay to "old" costs more, so
    # the scheduler is at least as kind to them as without it.
    requests = [req(0, "old", 10, 2)] + [req(8 + i, f"n{i}", 1, 4 + i) for i in range(4)]
    plain = run(requests, elevators=2, floors=12, fairness=0.0)
    fair = run(requests, elevators=2, floors=12, fairness=2.0)
    old_plain = next(p for p in plain.passengers if p.id == "old").wait
    old_fair = next(p for p in fair.passengers if p.id == "old").wait
    assert old_fair <= old_plain


def test_cross_zone_request_is_rejected_with_a_clear_error():
    served = {0: frozenset({1, 2, 3}), 1: frozenset({1, 4, 5})}
    with pytest.raises(NoFeasibleCarError, match="no elevator serves both floor 2 and floor 5"):
        run([req(0, "x", 2, 5)], elevators=2, floors=5, served_floors=served)


def test_zoned_scenario_serves_everyone_and_respects_zones(scheduler_name):
    zoned = scenario("tall_lobby_zoned")
    assert zoned.served_floors  # manifest carries the express configuration
    rows = run_matrix([zoned], [Variant(scheduler_name)])
    assert rows[0]["wait"]["count"] == rows[0]["passengers"]


def test_parking_at_lobby_reduces_up_peak_wait_for_etd():
    rows = run_matrix(
        [scenario("morning_up_peak"), scenario("morning_up_peak_parked")], [Variant("etd")]
    )
    unparked, parked = rows
    assert parked["wait"]["mean"] < unparked["wait"]["mean"]


def test_fairness_weight_lowers_max_wait_under_the_capacity_burst():
    # The one committed scenario where the effect held across fresh seeds as well
    # (docs/results/robustness.md: 14 of 20). The tall-building version of this test was
    # dropped after the seed study showed it pinned a coincidence.
    rows = run_matrix([scenario("capacity_stress")], [Variant("etd"), Variant("etd", fairness=0.5)])
    plain, fair = rows
    assert fair["wait"]["max"] < plain["wait"]["max"]
