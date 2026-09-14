"""Domain model: requests, passengers and elevators.

Movement rules (LOOK discipline, see docs/ASSUMPTIONS.md A3, A8, A12) live on
``Elevator`` so that the simulation and the schedulers' route projections share
one implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import IntEnum


class Direction(IntEnum):
    DOWN = -1
    IDLE = 0
    UP = 1


@dataclass(frozen=True, slots=True)
class Request:
    """One row of the input: a passenger asking to travel from ``source`` to ``dest``."""

    time: int
    id: str
    source: int
    dest: int

    @property
    def direction(self) -> Direction:
        return Direction.UP if self.dest > self.source else Direction.DOWN


@dataclass(slots=True)
class Passenger:
    """A request plus its lifecycle. Times are ticks; ``None`` until the event happens."""

    id: str
    request_time: int
    source: int
    dest: int
    car: int | None = None
    board_time: int | None = None
    alight_time: int | None = None

    @classmethod
    def from_request(cls, request: Request) -> Passenger:
        return cls(request.id, request.time, request.source, request.dest)

    @property
    def direction(self) -> Direction:
        return Direction.UP if self.dest > self.source else Direction.DOWN

    @property
    def wait(self) -> int | None:
        return None if self.board_time is None else self.board_time - self.request_time

    @property
    def travel(self) -> int | None:
        if self.board_time is None or self.alight_time is None:
            return None
        return self.alight_time - self.board_time

    @property
    def total(self) -> int | None:
        return None if self.alight_time is None else self.alight_time - self.request_time


@dataclass(slots=True)
class Elevator:
    """One car. ``waiting`` are passengers assigned to it but not yet aboard."""

    index: int
    floor: int
    capacity: int
    dwell_ticks: int
    served_floors: frozenset[int] | None = None
    park_floor: int | None = None
    direction: Direction = Direction.IDLE
    dwell_remaining: int = 0
    aboard: list[Passenger] = field(default_factory=list)
    waiting: list[Passenger] = field(default_factory=list)
    stops_made: int = 0
    floors_travelled: int = 0
    stopped_here: bool = False  # a stop (dwell) has already been started at the current floor

    # -- queries -----------------------------------------------------------

    def serves(self, floor: int) -> bool:
        return self.served_floors is None or floor in self.served_floors

    @property
    def load(self) -> int:
        return len(self.aboard)

    @property
    def is_idle(self) -> bool:
        return not self.aboard and not self.waiting

    @property
    def at_rest(self) -> bool:
        """Idle, not dwelling, and parked if a park floor is configured."""
        return (
            self.is_idle
            and self.dwell_remaining == 0
            and (self.park_floor is None or self.floor == self.park_floor)
        )

    def pending_stops(self) -> set[int]:
        """Floors the car must still visit: destinations aboard and pickups waiting."""
        return {p.dest for p in self.aboard} | {p.source for p in self.waiting}

    def _next_direction(self, stops: set[int]) -> Direction:
        """LOOK: keep the current direction while a stop lies ahead, else reverse, else idle."""
        above = any(f > self.floor for f in stops)
        below = any(f < self.floor for f in stops)
        if self.direction == Direction.UP and above:
            return Direction.UP
        if self.direction == Direction.DOWN and below:
            return Direction.DOWN
        if above:
            return Direction.UP
        if below:
            return Direction.DOWN
        return Direction.IDLE

    def departure_direction(self) -> Direction:
        """Direction the car will leave its current floor in.

        LOOK with one refinement: a passenger waiting *here* who wants to travel in the
        car's current direction counts as a stop ahead, so the car does not reverse
        away from them. Without this, two waiting passengers on adjacent floors wanting
        opposite directions can make a single car oscillate forever.
        """
        ahead = {f for f in self.pending_stops() if f != self.floor}
        here = [p for p in self.waiting if p.source == self.floor]
        above = any(f > self.floor for f in ahead)
        below = any(f < self.floor for f in ahead)
        wants = {p.direction for p in here}
        if self.direction == Direction.UP and (above or Direction.UP in wants):
            return Direction.UP
        if self.direction == Direction.DOWN and (below or Direction.DOWN in wants):
            return Direction.DOWN
        if here:
            return here[0].direction  # request order: the longest-waiting passenger here decides
        if above:
            return Direction.UP
        if below:
            return Direction.DOWN
        return Direction.IDLE

    # -- state transitions (one tick each) -----------------------------------

    def move(self) -> None:
        """Tick step 3: dwell, or advance one floor toward the next stop, or park/idle."""
        if self.dwell_remaining > 0:
            self.dwell_remaining -= 1
            if not self.pending_stops():
                self.direction = Direction.IDLE
            return
        direction = self._next_direction(self.pending_stops())
        if direction == Direction.IDLE and self.park_floor not in (None, self.floor):
            direction = Direction.UP if self.park_floor > self.floor else Direction.DOWN
        self.direction = direction
        if direction != Direction.IDLE:
            self.floor += int(direction)
            self.floors_travelled += 1
            self.stopped_here = False
        else:
            self.stopped_here = False  # at rest: the next boarding here is a new stop

    def serve_floor(self, now: int) -> tuple[list[Passenger], list[Passenger]]:
        """Tick step 4: alight, then board in request order while capacity and direction allow.

        Returns ``(alighted, boarded)``. Starts a dwell when anything happened.
        """
        alighted = [p for p in self.aboard if p.dest == self.floor]
        if alighted:
            self.aboard = [p for p in self.aboard if p.dest != self.floor]
            for p in alighted:
                p.alight_time = now

        departure = self.departure_direction()
        boarded: list[Passenger] = []
        for p in self.waiting:
            if p.source != self.floor or self.load >= self.capacity:
                continue
            if departure == Direction.IDLE:
                departure = p.direction
            if p.direction != departure:
                continue
            p.board_time = now
            self.aboard.append(p)
            boarded.append(p)
        if boarded:
            ids = {p.id for p in boarded}
            self.waiting = [p for p in self.waiting if p.id not in ids]
            self.direction = departure

        if (alighted or boarded) and not self.stopped_here:
            # One stop per floor visit: doors do not reopen for passengers who arrive
            # while the car is already dwelling here; they wait for the next pass (A2).
            self.stopped_here = True
            self.stops_made += 1
            self.dwell_remaining = self.dwell_ticks
        return alighted, boarded

    # -- projection support ----------------------------------------------------

    def clone(self) -> Elevator:
        """Deep enough copy for route projection: passengers are copied, not shared."""
        return replace(
            self,
            aboard=[replace(p) for p in self.aboard],
            waiting=[replace(p) for p in self.waiting],
        )
