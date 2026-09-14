"""Scheduler interface shared by every algorithm."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ..model import Elevator, Request


@runtime_checkable
class Scheduler(Protocol):
    """Assign a new request to a car index. Called once per request, at request time.

    The scheduler sees the current state of all cars and nothing about future
    requests. It must return the index of a car that serves both floors.
    """

    name: str

    def assign(self, request: Request, cars: Sequence[Elevator], now: int) -> int: ...


def feasible_cars(request: Request, cars: Sequence[Elevator]) -> list[Elevator]:
    """Cars that serve both the origin and the destination floor."""
    return [c for c in cars if c.serves(request.source) and c.serves(request.dest)]


class NoFeasibleCarError(RuntimeError):
    pass


def require_feasible(request: Request, cars: Sequence[Elevator]) -> list[Elevator]:
    candidates = feasible_cars(request, cars)
    if not candidates:
        raise NoFeasibleCarError(
            f"request {request.id}: no elevator serves both floor {request.source} "
            f"and floor {request.dest}"
        )
    return candidates
