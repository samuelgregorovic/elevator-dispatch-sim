"""Per-car usage and balance (ASSUMPTIONS.md A20)."""

from __future__ import annotations

import pytest

from conftest import req, run
from elevator_sim.metrics import balance, car_usage, summarize


def test_single_car_carries_everything_and_balance_is_flat():
    result = run([req(0, "a", 1, 5), req(0, "b", 1, 3)])
    (car,) = car_usage(result)
    assert car.car == 1
    assert car.carried == 2
    assert car.stops == 3  # board at 1, alight at 3, alight at 5
    assert car.floors_travelled == 4
    last = max(p.alight_time for p in result.passengers)
    # busy from t=0 up to (not including) the tick of the last alight, when the car is empty again
    assert car.busy_ticks == last
    assert car.busy_share == last / result.ticks
    b = balance([car], result.ticks)
    assert (b.busy_spread, b.carried_max_share, b.fair_share) == (0.0, 1.0, 1.0)


def test_idle_car_counts_as_unused():
    # One request, two cars: the nearer car takes it, the other never moves.
    result = run([req(0, "a", 1, 5)], elevators=2)
    cars = car_usage(result)
    assert sorted(c.carried for c in cars) == [0, 1]
    idle = next(c for c in cars if c.carried == 0)
    assert (idle.stops, idle.floors_travelled, idle.busy_ticks, idle.busy_share) == (0, 0, 0, 0.0)
    b = balance(cars, result.ticks)
    assert b.carried_max_share == 1.0
    assert b.fair_share == 0.5
    assert b.busy_spread == max(c.busy_share for c in cars)


def test_busy_means_aboard_or_assigned(scheduler_name):
    # A car is busy from the tick it is assigned a waiting passenger, not only while carrying.
    result = run([req(0, "a", 6, 8)], scheduler_name)
    (car,) = car_usage(result)
    p = result.passengers[0]
    assert car.busy_ticks == p.alight_time  # t=0 .. the tick before alight
    assert p.wait > 0  # so the assigned-but-waiting ticks are part of it


def test_round_robin_spreads_passengers_evenly_by_construction():
    reqs = [req(t, f"p{t}", 1, 2 + t % 3) for t in range(12)]
    cars = car_usage(run(reqs, "round_robin", elevators=3, capacity=1, floors=6))
    assert [c.carried for c in cars] == [4, 4, 4]
    assert balance(cars, 1).carried_max_share == 1 / 3


def test_summary_carries_cars_and_balance():
    s = summarize(run([req(0, "a", 1, 5)], elevators=2))
    d = s.to_dict()
    assert [c["car"] for c in d["cars"]] == [1, 2]
    assert set(d["balance"]) == {"busy_mean", "busy_spread", "carried_max_share", "fair_share"}
    assert any(note.startswith("work balance:") for note in s.observations)


def test_service_level_counts_long_waits():
    from elevator_sim.metrics import service

    # one car at the lobby, ten passengers wanting floor 10 one at a time: waits grow past 30
    reqs = [req(0, f"p{i}", 1, 10) for i in range(6)]
    result = run(reqs, capacity=1)
    sv = service(result)
    assert sv.threshold == 30
    waits = sorted(p.wait for p in result.passengers)
    assert sv.over == sum(1 for w in waits if w > 30)
    assert sv.over_share == sv.over / len(waits)
    assert service(result, threshold=10_000).over == 0


def test_efficiency_counts_intermediate_stops_and_travel():
    from elevator_sim.metrics import efficiency

    # a boards at 1 going to 6; b boards at 3 going to 5: a sits through b's boarding stop and
    # b's alighting stop; b sits through none.
    result = run([req(0, "a", 1, 6), req(0, "b", 3, 5)])
    ef = efficiency(result, car_usage(result))
    assert ef.stops_per_trip == (2 + 0) / 2
    assert ef.floors_per_passenger == 5 / 2


def test_park_schedule_moves_the_park_floor_with_time():
    from elevator_sim.config import SimulationConfig

    cfg = SimulationConfig(elevators=1, floors=10, capacity=4, park_schedule=((0, 1), (50, 8)))
    assert cfg.park_floor_at(0) == 1 and cfg.park_floor_at(49) == 1 and cfg.park_floor_at(50) == 8
    result = run([req(0, "a", 1, 3)], park_schedule=((0, 1), (5, 8)))
    # after delivering at tick 3 the schedule says floor 8 from tick 5: the car ends parked there
    assert result.positions[-1] == [8]
    with pytest.raises(ValueError):
        SimulationConfig(elevators=1, floors=10, park_schedule=((10, 1), (5, 2)))
    with pytest.raises(ValueError):
        SimulationConfig(elevators=1, floors=10, park_schedule=((0, 11),))
