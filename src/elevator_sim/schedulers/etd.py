"""Estimated-time-to-destination (ETD) scheduler.

The cost of assigning a request to a car is the new passenger's projected time
to destination plus the delay the insertion inflicts on every passenger already
assigned to that car (Peters Research's "system degradation factor"). An
optional fairness weight scales each delay by how long that passenger has
already been waiting, so long waits are protected. See docs/DESIGN.md.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..model import Elevator, Passenger, Request
from .base import require_feasible


class ETDScheduler:
    name = "etd"

    def __init__(self, fairness: float = 0.0) -> None:
        if fairness < 0:
            raise ValueError("fairness weight must be >= 0")
        self.fairness = fairness
        if fairness:
            self.name = f"etd_f{fairness:g}"

    def assign(self, request: Request, cars: Sequence[Elevator], now: int) -> int:
        best_index, best_cost = -1, float("inf")
        for car in require_feasible(request, cars):
            cost = self._cost(car, request, now)
            if cost < best_cost:
                best_index, best_cost = car.index, cost
        return best_index

    def _cost(self, car: Elevator, request: Request, now: int) -> float:
        candidate = car.clone()
        candidate.waiting.append(Passenger.from_request(request))
        horizon = projection_horizon(candidate, now)
        before = project(car, now, horizon)
        after = project(candidate, now, horizon)

        cost = float(after[request.id] - now)
        for p in car.aboard + car.waiting:
            delay = after[p.id] - before[p.id]
            if delay <= 0:
                continue
            weight = 1.0
            if self.fairness and p.board_time is None:
                weight += self.fairness * (now - p.request_time)
            cost += weight * delay
        return cost


def projection_horizon(car: Elevator, now: int) -> int:
    """Upper bound on ticks a LOOK car needs to deliver everyone currently assigned to it.

    Each passenger is served within two full sweeps of the span, and each sweep
    costs at most span moves plus one dwell per stop. Generous on purpose.
    """
    stops = [car.floor, *car.pending_stops(), *(p.dest for p in car.waiting)]
    span = max(stops) - min(stops) + 1
    n = len(car.aboard) + len(car.waiting)
    return now + 2 * (n + 1) * (span + (car.dwell_ticks + 1) * (2 * n + 1)) + 4


def project(car: Elevator, now: int, horizon: int | None = None) -> dict[str, int]:
    """Simulate this car alone from ``now`` and return each passenger's alight tick.

    Uses the same movement and boarding rules as the real simulation, so the
    projection is exact for this car if no further requests arrive. Passengers
    not delivered within the horizon get the horizon as a penalty value.
    """
    sim = car.clone()
    ids = [p.id for p in sim.aboard + sim.waiting]
    if horizon is None:
        horizon = projection_horizon(sim, now)
    done: dict[str, int] = {}
    t = now
    while len(done) < len(ids) and t <= horizon:
        # Same order as Simulation._tick: serve the floor at t, then advance toward t + 1.
        alighted, _ = sim.serve_floor(t)
        for p in alighted:
            done[p.id] = t
        sim.move()
        t += 1
    for pid in ids:
        done.setdefault(pid, horizon)
    return done
