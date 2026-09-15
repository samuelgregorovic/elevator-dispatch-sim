"""Scheduling algorithms. All implement the ``Scheduler`` protocol in ``base``."""

from __future__ import annotations

from .base import NoFeasibleCarError, Scheduler
from .etd import ETDScheduler
from .nearest_car import NearestCarScheduler
from .round_robin import RoundRobinScheduler

SCHEDULERS: dict[str, type] = {
    "etd": ETDScheduler,
    "nearest_car": NearestCarScheduler,
    "nearest_car_balanced": NearestCarScheduler,
    "round_robin": RoundRobinScheduler,
}


def make_scheduler(name: str, fairness: float = 0.0) -> Scheduler:
    if name not in SCHEDULERS:
        raise ValueError(f"unknown scheduler {name!r}; choose from {sorted(SCHEDULERS)}")
    if name == "etd":
        return ETDScheduler(fairness=fairness)
    if name == "nearest_car_balanced":
        return NearestCarScheduler(balanced=True)
    return SCHEDULERS[name]()


__all__ = [
    "SCHEDULERS",
    "ETDScheduler",
    "NearestCarScheduler",
    "NoFeasibleCarError",
    "RoundRobinScheduler",
    "Scheduler",
    "make_scheduler",
]
