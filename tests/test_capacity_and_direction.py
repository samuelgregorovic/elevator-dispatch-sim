"""Capacity (A8), assignment immutability (A11) and LOOK direction discipline (A12)."""

from __future__ import annotations

from conftest import req, run
from elevator_sim.model import Direction, Elevator, Passenger


def test_load_never_exceeds_capacity():
    requests = [req(0, f"p{i}", 1, 8) for i in range(10)]
    result = run(requests, capacity=3)
    for tick in result.car_states:
        for car in tick:
            assert car["load"] <= 3


def test_passenger_left_behind_by_full_car_boards_on_a_later_pass_of_the_same_car():
    requests = [req(0, f"p{i}", 1, 8) for i in range(5)]
    result = run(requests, capacity=4)
    left = next(p for p in result.passengers if p.id == "p4")
    assert left.car == 0
    assert left.board_time is not None and left.board_time > 0
    assert left.alight_time is not None
    assert all(p.alight_time is not None for p in result.passengers)


def test_car_going_up_with_stops_ahead_does_not_pick_up_a_down_passenger():
    # Car carries "a" from 1 to 9. "b" at floor 5 wants to go down; car passes 5 going up.
    result = run([req(0, "a", 1, 9), req(1, "b", 5, 2)])
    a = next(p for p in result.passengers if p.id == "a")
    b = next(p for p in result.passengers if p.id == "b")
    assert b.board_time > a.alight_time  # picked up on the way back down
    assert b.alight_time is not None


def test_idle_car_adopts_direction_of_first_boarding_passenger():
    car = Elevator(index=0, floor=5, capacity=4, dwell_ticks=0)
    down = Passenger("d", 0, 5, 1)
    up = Passenger("u", 0, 5, 9)
    car.waiting = [down, up]
    _, boarded = car.serve_floor(0)
    assert [p.id for p in boarded] == ["d"]
    assert car.direction == Direction.DOWN
    assert car.waiting == [up]


def test_look_reverses_only_when_no_stops_remain_ahead():
    car = Elevator(index=0, floor=5, capacity=4, dwell_ticks=0, direction=Direction.UP)
    car.aboard = [Passenger("x", 0, 1, 7, board_time=0), Passenger("y", 0, 1, 3, board_time=0)]
    car.move()
    assert car.floor == 6  # keeps going up for x although y's stop is below
    car.move()
    car.serve_floor(1)
    car.move()
    assert car.floor == 6 and car.direction == Direction.DOWN  # reversed for y


def test_assignment_is_immutable():
    requests = [req(0, f"p{i}", 1, 8) for i in range(6)]
    result = run(requests, elevators=2, capacity=2)
    assigned = {e["id"]: e["car"] for e in result.events if e["type"] == "assign"}
    boarded = {e["id"]: e["car"] for e in result.events if e["type"] == "board"}
    assert boarded == assigned
    assert sum(1 for e in result.events if e["type"] == "assign") == 6


def test_park_floor_returns_idle_car_to_lobby():
    result = run([req(0, "a", 1, 6)], park_floor=1)
    assert result.positions[-1] == [1]
    assert max(row[0] for row in result.positions) == 6


def test_express_car_is_only_assigned_feasible_passengers(scheduler_name):
    served = {1: frozenset({1, *range(6, 11)})}
    requests = [req(0, "low", 2, 4), req(0, "high", 1, 9), req(1, "mid", 3, 8)]
    result = run(requests, scheduler_name, elevators=2, served_floors=served)
    car_of = {p.id: p.car for p in result.passengers}
    assert car_of["low"] == 0
    assert car_of["mid"] == 0
    assert all(p.alight_time is not None for p in result.passengers)
