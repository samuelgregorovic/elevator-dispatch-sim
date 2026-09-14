"""Simulation configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    elevators: int = 4
    floors: int = 51
    capacity: int = 8
    dwell_ticks: int = 1
    start_floor: int = 1
    park_floor: int | None = None
    # Per-car served floors for express cars; missing index means "serves all floors".
    served_floors: dict[int, frozenset[int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.elevators < 1:
            raise ValueError("elevators must be >= 1")
        if self.floors < 2:
            raise ValueError("floors must be >= 2")
        if self.capacity < 1:
            raise ValueError("capacity must be >= 1")
        if self.dwell_ticks < 0:
            raise ValueError("dwell_ticks must be >= 0")
        if not 1 <= self.start_floor <= self.floors:
            raise ValueError("start_floor must be within 1..floors")
        if self.park_floor is not None and not 1 <= self.park_floor <= self.floors:
            raise ValueError("park_floor must be within 1..floors")
        for idx, floors in self.served_floors.items():
            if not 0 <= idx < self.elevators:
                raise ValueError(f"served_floors refers to unknown elevator index {idx}")
            bad = [f for f in floors if not 1 <= f <= self.floors]
            if bad:
                raise ValueError(f"served_floors for elevator {idx} outside 1..floors: {bad}")
            if len(floors) < 2:
                raise ValueError(f"served_floors for elevator {idx} must contain >= 2 floors")
            if self.park_floor is not None and self.park_floor not in floors:
                raise ValueError(f"park_floor {self.park_floor} is not served by elevator {idx}")
