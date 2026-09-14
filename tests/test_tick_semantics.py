"""Order of operations within a tick (ASSUMPTIONS.md A1-A5)."""

from __future__ import annotations

from conftest import req, run


def passenger(result, ident):
    return next(p for p in result.passengers if p.id == ident)


def test_idle_car_on_the_request_floor_boards_in_the_same_tick():
    result = run([req(0, "a", 1, 5)])
    p = passenger(result, "a")
    assert p.board_time == 0
    assert p.wait == 0


def test_car_one_floor_away_arrives_next_tick():
    result = run([req(0, "a", 2, 5)])
    p = passenger(result, "a")
    assert p.board_time == 1
    assert p.wait == 1


def test_travel_is_floors_plus_one_dwell_at_boarding_with_default_dwell():
    result = run([req(0, "a", 1, 5)], dwell_ticks=1)
    p = passenger(result, "a")
    # board at t=0, dwell at t=1, floors 2..5 at t=2..5
    assert p.alight_time == 5
    assert p.travel == 5


def test_zero_dwell_reproduces_literal_brief():
    result = run([req(0, "a", 1, 5)], dwell_ticks=0)
    p = passenger(result, "a")
    assert p.alight_time == 4
    assert p.travel == 4


def test_positions_are_logged_from_tick_zero_one_row_per_tick():
    result = run([req(3, "a", 1, 3)])
    assert result.positions[0] == [1]
    assert len(result.positions) == result.ticks
    assert result.ticks >= 4  # ticks 0..3 at least, even though nothing happens before t=3


def test_simulation_ticks_through_idle_time_rather_than_jumping():
    result = run([req(10, "a", 1, 2)])
    assert result.positions[:10] == [[1]] * 10


def test_cars_move_at_most_one_floor_per_tick():
    result = run([req(0, "a", 1, 9), req(0, "b", 9, 1), req(4, "c", 5, 2)], elevators=2)
    for prev, cur in zip(result.positions, result.positions[1:], strict=False):
        for a, b in zip(prev, cur, strict=True):
            assert abs(a - b) <= 1


def test_metrics_definitions():
    result = run([req(2, "a", 3, 6)])
    p = passenger(result, "a")
    assert p.wait == p.board_time - 2
    assert p.travel == p.alight_time - p.board_time
    assert p.total == p.wait + p.travel


def test_empty_input_produces_single_tick():
    result = run([])
    assert result.positions == [[1]]
    assert result.passengers == []


def test_percentile_is_nearest_rank():
    from elevator_sim.metrics import percentile

    assert percentile([0, 2], 50) == 0
    assert percentile(list(range(1, 11)), 50) == 5
    assert percentile(list(range(1, 21)), 90) == 18
    assert percentile([7], 90) == 7
    assert percentile([], 50) == 0.0


def test_dwell_is_not_restarted_by_passengers_arriving_mid_stop():
    # One car, capacity 100, a lobby arrival every tick: without the one-stop-per-visit
    # rule the car would sit at the lobby for as long as arrivals continue.
    requests = [req(t, f"p{t}", 1, 5) for t in range(20)] + [req(0, "far", 9, 2)]
    result = run(requests, floors=10, capacity=100, dwell_ticks=1)
    car_positions = [row[0] for row in result.positions]
    first_departure = next(t for t, f in enumerate(car_positions) if f != 1)
    assert first_departure == 2  # boards at 0, dwells at 1, moves at 2
    assert result.cars[0].stops_made < 10  # physical stops, not boarding events
    far = next(p for p in result.passengers if p.id == "far")
    assert far.wait < 40


def test_idle_car_reports_idle_direction_after_its_last_stop():
    result = run([req(0, "a", 1, 3)])
    last = result.car_states[-1][0]
    assert last["dir"] == 0 and last["load"] == 0
