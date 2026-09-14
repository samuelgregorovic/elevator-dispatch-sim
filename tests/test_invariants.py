"""Property-based invariants that must hold for every scheduler on every input."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from conftest import run
from elevator_sim.model import Request


@st.composite
def scenarios(draw):
    floors = draw(st.integers(min_value=2, max_value=12))
    n = draw(st.integers(min_value=0, max_value=25))
    requests = []
    for i in range(n):
        source = draw(st.integers(min_value=1, max_value=floors))
        dest = draw(st.integers(min_value=1, max_value=floors).filter(lambda d, s=source: d != s))
        time = draw(st.integers(min_value=0, max_value=30))
        requests.append(Request(time=time, id=f"p{i}", source=source, dest=dest))
    config = {
        "floors": floors,
        "elevators": draw(st.integers(min_value=1, max_value=4)),
        "capacity": draw(st.integers(min_value=1, max_value=6)),
        "dwell_ticks": draw(st.integers(min_value=0, max_value=2)),
    }
    return requests, config


@pytest.mark.parametrize("scheduler_name", ["etd", "nearest_car", "round_robin"])
@settings(max_examples=60, deadline=None)
@given(scenarios())
def test_every_passenger_is_delivered(scheduler_name, scenario):
    requests, config = scenario
    result = run(requests, scheduler_name, **config)
    assert all(p.alight_time is not None for p in result.passengers)
    assert all(p.alight_time > p.board_time >= p.request_time for p in result.passengers)


@pytest.mark.parametrize("scheduler_name", ["etd", "nearest_car", "round_robin"])
@settings(max_examples=60, deadline=None)
@given(scenarios())
def test_cars_move_one_floor_per_tick_within_the_building(scheduler_name, scenario):
    requests, config = scenario
    result = run(requests, scheduler_name, **config)
    for row in result.positions:
        assert all(1 <= f <= config["floors"] for f in row)
    for prev, cur in zip(result.positions, result.positions[1:], strict=False):
        assert all(abs(a - b) <= 1 for a, b in zip(prev, cur, strict=True))


@pytest.mark.parametrize("scheduler_name", ["etd", "nearest_car", "round_robin"])
@settings(max_examples=60, deadline=None)
@given(scenarios())
def test_capacity_is_never_exceeded(scheduler_name, scenario):
    requests, config = scenario
    result = run(requests, scheduler_name, **config)
    assert all(c["load"] <= config["capacity"] for tick in result.car_states for c in tick)


@pytest.mark.parametrize("scheduler_name", ["etd", "nearest_car", "round_robin"])
@settings(max_examples=40, deadline=None)
@given(scenarios())
def test_runs_are_deterministic(scheduler_name, scenario):
    requests, config = scenario
    a = run(requests, scheduler_name, **config)
    b = run(requests, scheduler_name, **config)
    assert a.positions == b.positions
    assert a.events == b.events


@pytest.mark.parametrize("scheduler_name", ["etd", "nearest_car", "round_robin"])
@settings(max_examples=40, deadline=None)
@given(scenarios())
def test_positions_log_covers_every_tick_from_zero(scheduler_name, scenario):
    requests, config = scenario
    result = run(requests, scheduler_name, **config)
    last_request = max((r.time for r in requests), default=0)
    assert result.ticks >= last_request + 1
    assert all(len(row) == config["elevators"] for row in result.positions)
