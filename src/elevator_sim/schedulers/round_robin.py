"""Round-robin baseline: cars take requests in rotation, ignoring position."""

from __future__ import annotations

from collections.abc import Sequence

from ..model import Elevator, Request
from .base import require_feasible


class RoundRobinScheduler:
    name = "round_robin"

    def __init__(self) -> None:
        self._next = 0

    def assign(self, request: Request, cars: Sequence[Elevator], now: int) -> int:
        candidates = require_feasible(request, cars)
        # Rotate over all cars, skipping infeasible ones, so the order is stable.
        for _ in range(len(cars)):
            car = cars[self._next % len(cars)]
            self._next += 1
            if car in candidates:
                return car.index
        return candidates[0].index  # unreachable: candidates is non-empty
