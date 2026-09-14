"""The tick loop. Order of operations per tick is fixed by docs/ASSUMPTIONS.md A3."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .config import SimulationConfig
from .feed import RequestFeed
from .model import Elevator, Passenger, Request
from .schedulers.base import NoFeasibleCarError, Scheduler


@dataclass(slots=True)
class SimulationResult:
    config: SimulationConfig
    scheduler: str
    positions: list[list[int]] = field(default_factory=list)  # positions[t][car]
    passengers: list[Passenger] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    car_states: list[list[dict[str, int]]] = field(default_factory=list)  # per tick, per car
    cars: list[Elevator] = field(default_factory=list)

    @property
    def ticks(self) -> int:
        return len(self.positions)


class Simulation:
    def __init__(
        self, config: SimulationConfig, scheduler: Scheduler, requests: Iterable[Request]
    ) -> None:
        self.config = config
        self.scheduler = scheduler
        self.feed = RequestFeed(requests)
        self.cars = [
            Elevator(
                index=i,
                floor=config.start_floor,
                capacity=config.capacity,
                dwell_ticks=config.dwell_ticks,
                served_floors=config.served_floors.get(i),
                park_floor=config.park_floor,
            )
            for i in range(config.elevators)
        ]
        self.result = SimulationResult(config=config, scheduler=scheduler.name, cars=self.cars)
        self._request_count = 0

    def run(self, max_ticks: int | None = None) -> SimulationResult:
        now = 0
        while True:
            finished = self._tick(now)
            if finished:
                return self.result
            now += 1
            if max_ticks is not None and now > max_ticks:
                raise RuntimeError(f"simulation did not finish within {max_ticks} ticks")

    # -- one tick ------------------------------------------------------------

    def _tick(self, now: int) -> bool:
        """Run one tick; return True when the simulation is complete at this tick."""
        res = self.result
        for request in self.feed.release(now):
            self._request_count += 1
            res.events.append(
                {
                    "t": now,
                    "type": "request",
                    "id": request.id,
                    "floor": request.source,
                    "dest": request.dest,
                }
            )
            passenger = Passenger.from_request(request)
            car_index = self.scheduler.assign(request, self.cars, now)
            car = self._checked_car(request, car_index)
            passenger.car = car.index
            car.waiting.append(passenger)
            res.passengers.append(passenger)
            res.events.append({"t": now, "type": "assign", "id": request.id, "car": car.index})

        for car in self.cars:
            alighted, boarded = car.serve_floor(now)
            for p in alighted:
                res.events.append(
                    {"t": now, "type": "alight", "id": p.id, "car": car.index, "floor": car.floor}
                )
            for p in boarded:
                res.events.append(
                    {"t": now, "type": "board", "id": p.id, "car": car.index, "floor": car.floor}
                )

        res.positions.append([car.floor for car in self.cars])
        res.car_states.append(
            [
                {
                    "floor": c.floor,
                    "dir": int(c.direction),
                    "load": c.load,
                    "dwell": c.dwell_remaining,
                    "waiting": len(c.waiting),
                }
                for c in self.cars
            ]
        )

        if self._finished():
            return True
        # Advance toward the state at now + 1 (movement happens between ticks).
        for car in self.cars:
            car.move()
        return False

    def _checked_car(self, request: Request, car_index: int) -> Elevator:
        if not 0 <= car_index < len(self.cars):
            raise NoFeasibleCarError(
                f"scheduler {self.scheduler.name} returned invalid car index {car_index}"
            )
        car = self.cars[car_index]
        if not (car.serves(request.source) and car.serves(request.dest)):
            raise NoFeasibleCarError(
                f"scheduler {self.scheduler.name} assigned {request.id} to elevator "
                f"{car_index}, which does not serve floors {request.source}->{request.dest}"
            )
        return car

    def _finished(self) -> bool:
        return self.feed.exhausted and all(car.at_rest for car in self.cars)
