from __future__ import annotations

from collections.abc import Iterable

import pytest

from elevator_sim.config import SimulationConfig
from elevator_sim.model import Request
from elevator_sim.schedulers import make_scheduler
from elevator_sim.simulation import Simulation, SimulationResult


def req(time: int, ident: str, source: int, dest: int) -> Request:
    return Request(time=time, id=ident, source=source, dest=dest)


def run(
    requests: Iterable[Request],
    scheduler: str = "etd",
    *,
    fairness: float = 0.0,
    max_ticks: int | None = 10_000,
    **config: object,
) -> SimulationResult:
    cfg = SimulationConfig(**{"elevators": 1, "floors": 10, "capacity": 4, **config})
    return Simulation(cfg, make_scheduler(scheduler, fairness=fairness), requests).run(
        max_ticks=max_ticks
    )


@pytest.fixture(params=["etd", "nearest_car", "round_robin"])
def scheduler_name(request: pytest.FixtureRequest) -> str:
    return request.param
