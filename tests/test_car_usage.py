"""Per-car usage and balance (ASSUMPTIONS.md A20)."""

from __future__ import annotations

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
    b = balance([car])
    assert (b.busy_spread, b.carried_max_share, b.fair_share) == (0.0, 1.0, 1.0)


def test_idle_car_counts_as_unused():
    # One request, two cars: the nearer car takes it, the other never moves.
    result = run([req(0, "a", 1, 5)], elevators=2)
    cars = car_usage(result)
    assert sorted(c.carried for c in cars) == [0, 1]
    idle = next(c for c in cars if c.carried == 0)
    assert (idle.stops, idle.floors_travelled, idle.busy_ticks, idle.busy_share) == (0, 0, 0, 0.0)
    b = balance(cars)
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
    assert balance(cars).carried_max_share == 1 / 3


def test_summary_carries_cars_and_balance():
    s = summarize(run([req(0, "a", 1, 5)], elevators=2))
    d = s.to_dict()
    assert [c["car"] for c in d["cars"]] == [1, 2]
    assert set(d["balance"]) == {"busy_mean", "busy_spread", "carried_max_share", "fair_share"}
    assert any(note.startswith("work balance:") for note in s.observations)
