"""The engine against elevator-traffic theory (docs/results/theory.md, scenarios/theory.py).

Two fast versions of the checks that script runs in full: the classical up-peak
round-trip-time formula, and Little's law as an exact identity.
"""

from __future__ import annotations

import random
import statistics
import sys
from pathlib import Path

import pytest

from conftest import req
from elevator_sim.config import SimulationConfig
from elevator_sim.model import Request
from elevator_sim.schedulers import make_scheduler
from elevator_sim.simulation import Simulation

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scenarios"))
import theory  # noqa: E402


@pytest.mark.parametrize(("floors", "capacity"), [(10, 4), (20, 8)])
def test_up_peak_round_trip_matches_barney_formula(floors: int, capacity: int) -> None:
    """One car, lobby full of passengers with uniform destinations: the measured round trip
    must match 2H + S + 1 (Barney & Al-Sharif) to within a few percent over a few seeds.
    The formula appears nowhere in the engine."""
    n = 120
    measured = []
    for seed in range(5):
        rng = random.Random(seed)
        reqs = [Request(0, f"p{i}", 1, rng.randint(2, floors)) for i in range(n)]
        config = SimulationConfig(elevators=1, floors=floors, capacity=capacity, park_floor=1)
        res = Simulation(config, make_scheduler("etd"), reqs).run(max_ticks=100_000)
        measured.append((res.ticks - 1) / -(-n // capacity))
    formula = theory.rtt_formula(floors, capacity, dwell=1)
    assert abs(statistics.fmean(measured) - formula) / formula < 0.03


def test_sum_of_waits_equals_integral_of_queue_length() -> None:
    """Little's law in its exact finite form, on a run with queues, capacity misses and
    idle stretches."""
    rng = random.Random(3)
    reqs = [req(rng.randint(0, 60), f"p{i}", *rng.sample(range(1, 13), 2)) for i in range(80)]
    config = SimulationConfig(elevators=2, floors=12, capacity=3)
    res = Simulation(config, make_scheduler("nearest_car"), reqs).run(max_ticks=100_000)
    assert sum(p.wait for p in res.passengers) == sum(theory.backlog(res))
