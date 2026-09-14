"""Golden statistics for the sample from the brief. A behaviour change must change these."""

from __future__ import annotations

from pathlib import Path

import pytest

from elevator_sim.config import SimulationConfig
from elevator_sim.io import read_requests
from elevator_sim.metrics import summarize
from elevator_sim.schedulers import make_scheduler
from elevator_sim.simulation import Simulation

SAMPLE = Path(__file__).parent.parent / "scenarios" / "sample.csv"

GOLDEN = {
    # scheduler: (ticks, wait(min,max,mean), total(min,max,mean))
    "etd": (77, (0, 45, 15.0), (37, 65, 51.0)),
    "nearest_car": (54, (0, 19, 6.33), (37, 52, 42.67)),
    "round_robin": (105, (0, 73, 24.33), (37, 93, 60.33)),
}


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_sample_statistics_are_stable(name):
    config = SimulationConfig(elevators=2, floors=51, capacity=8, dwell_ticks=1)
    result = Simulation(config, make_scheduler(name), read_requests(SAMPLE, 51)).run()
    s = summarize(result)
    ticks, wait, total = GOLDEN[name]
    assert s.ticks == ticks
    assert (s.wait.min, s.wait.max, s.wait.mean) == wait
    assert (s.total.min, s.total.max, s.total.mean) == total
    assert s.passengers == 3
