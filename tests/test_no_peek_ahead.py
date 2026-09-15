"""No peek-ahead (A16): the scheduler only ever sees requests whose time has come."""

from __future__ import annotations

from collections.abc import Sequence

from conftest import req
from elevator_sim.config import SimulationConfig
from elevator_sim.feed import RequestFeed
from elevator_sim.model import Elevator, Request
from elevator_sim.simulation import Simulation


class SpyScheduler:
    name = "spy"

    def __init__(self) -> None:
        self.seen: list[tuple[int, Request]] = []

    def assign(self, request: Request, cars: Sequence[Elevator], now: int) -> int:
        self.seen.append((now, request))
        return 0


def test_scheduler_sees_each_request_exactly_at_its_time_and_never_earlier():
    requests = [req(7, "late", 1, 3), req(0, "early", 2, 5), req(3, "mid", 4, 1)]
    spy = SpyScheduler()
    Simulation(SimulationConfig(elevators=1, floors=10), spy, requests).run(max_ticks=1000)
    assert [(now, r.id) for now, r in spy.seen] == [(0, "early"), (3, "mid"), (7, "late")]
    for now, r in spy.seen:
        assert r.time == now


def test_feed_never_releases_future_requests():
    feed = RequestFeed([req(5, "a", 1, 2), req(2, "b", 1, 2), req(5, "c", 1, 2)])
    assert feed.release(1) == []
    assert [r.id for r in feed.release(2)] == ["b"]
    assert feed.release(3) == []
    assert feed.next_time == 5
    assert [r.id for r in feed.release(9)] == ["a", "c"]
    assert feed.exhausted


def test_scheduler_interface_carries_no_feed_and_no_future():
    # The only thing a scheduler is ever given is (request, cars, now): the protocol has no
    # parameter through which the feed or the request list could reach it, and the
    # simulation holds the feed privately. A scheduler cannot peek because there is nothing
    # to peek at.
    import inspect

    from elevator_sim.schedulers.base import Scheduler

    params = list(inspect.signature(Scheduler.assign).parameters)
    assert params == ["self", "request", "cars", "now"]
    sim = Simulation(SimulationConfig(elevators=1, floors=10), SpyScheduler(), [req(0, "a", 1, 2)])
    # The simulation's feed is the only path to requests, and nothing hands it to a scheduler:
    # the scheduler receives cars and the clock, never the simulation or the feed.
    assert not any(isinstance(v, Simulation) for v in vars(sim.scheduler).values())
    assert "feed" not in vars(sim.scheduler)
