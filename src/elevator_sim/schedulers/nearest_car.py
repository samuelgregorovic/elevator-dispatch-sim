"""Nearest-car baseline with a direction check."""

from __future__ import annotations

from collections.abc import Sequence

from ..model import Direction, Elevator, Request
from .base import require_feasible


class NearestCarScheduler:
    """Pick the car with the smallest distance to the origin, penalising cars that would
    have to reverse first. Ignores queued stops, which is its documented weakness."""

    name = "nearest_car"

    def assign(self, request: Request, cars: Sequence[Elevator], now: int) -> int:
        best_index, best_cost = -1, float("inf")
        for car in require_feasible(request, cars):
            distance = abs(car.floor - request.source)
            cost = distance if _approaching(car, request) else distance + 2 * _span(cars)
            if cost < best_cost:
                best_index, best_cost = car.index, cost
        return best_index


def _approaching(car: Elevator, request: Request) -> bool:
    """True if the car is idle, or moving toward the origin in the passenger's direction."""
    if car.direction == Direction.IDLE:
        return True
    toward = (car.direction == Direction.UP and request.source >= car.floor) or (
        car.direction == Direction.DOWN and request.source <= car.floor
    )
    return toward and car.direction == request.direction


def _span(cars: Sequence[Elevator]) -> int:
    """Rough building height, used only to scale the reversal penalty."""
    stops = {f for c in cars for f in c.pending_stops()} | {c.floor for c in cars}
    return max(stops) - min(stops) + 1 if stops else 1
