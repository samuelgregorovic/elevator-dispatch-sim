"""Passenger statistics and generated observations (docs/ASSUMPTIONS.md A19)."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from .simulation import SimulationResult


@dataclass(frozen=True, slots=True)
class Distribution:
    count: int
    min: int
    max: int
    mean: float
    p50: float
    p90: float

    @classmethod
    def of(cls, values: list[int]) -> Distribution:
        if not values:
            return cls(0, 0, 0, 0.0, 0.0, 0.0)
        s = sorted(values)
        return cls(
            count=len(s),
            min=s[0],
            max=s[-1],
            mean=round(sum(s) / len(s), 2),
            p50=percentile(s, 50),
            p90=percentile(s, 90),
        )


def percentile(sorted_values: list[int], pct: float) -> float:
    """Nearest-rank percentile on an already sorted list."""
    if not sorted_values:
        return 0.0
    rank = max(1, round(pct / 100 * len(sorted_values) + 0.5))
    return float(sorted_values[min(rank, len(sorted_values)) - 1])


@dataclass(frozen=True, slots=True)
class Summary:
    scheduler: str
    passengers: int
    ticks: int
    wait: Distribution
    travel: Distribution
    total: Distribution
    observations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize(result: SimulationResult) -> Summary:
    served = [p for p in result.passengers if p.alight_time is not None]
    waits = [p.wait for p in served if p.wait is not None]
    travels = [p.travel for p in served if p.travel is not None]
    totals = [p.total for p in served if p.total is not None]
    return Summary(
        scheduler=result.scheduler,
        passengers=len(result.passengers),
        ticks=result.ticks,
        wait=Distribution.of(waits),
        travel=Distribution.of(travels),
        total=Distribution.of(totals),
        observations=observations(result),
    )


def observations(result: SimulationResult) -> list[str]:
    notes: list[str] = []
    served = [p for p in result.passengers if p.alight_time is not None]
    if not served:
        return ["no passengers served"]
    unserved = len(result.passengers) - len(served)
    if unserved:
        notes.append(f"{unserved} passenger(s) not delivered")

    waits = sorted(p.wait for p in served if p.wait is not None)
    median = percentile(waits, 50)
    long_waits = sum(1 for w in waits if median > 0 and w > 2 * median)
    if waits:
        notes.append(
            f"{long_waits} of {len(waits)} passengers ({100 * long_waits / len(waits):.0f}%) "
            f"waited more than twice the median wait of {median:g} ticks"
        )
    zero = sum(1 for w in waits if w == 0)
    if zero:
        notes.append(f"{zero} passengers boarded in the tick they requested (wait 0)")

    origins = Counter(p.source for p in served)
    floor, n = origins.most_common(1)[0]
    notes.append(f"busiest origin floor: {floor} ({n} of {len(served)} requests)")

    up = sum(1 for p in served if p.dest > p.source)
    notes.append(f"direction mix: {up} up, {len(served) - up} down")

    for car in result.cars:
        carried = sum(1 for p in served if p.car == car.index)
        idle = sum(
            1
            for t in result.car_states
            if t[car.index]["load"] == 0 and t[car.index]["waiting"] == 0
        )
        notes.append(
            f"elevator {car.index + 1}: carried {carried}, stops {car.stops_made}, "
            f"floors travelled {car.floors_travelled}, "
            f"idle {100 * idle / result.ticks:.0f}% of ticks"
        )
    return notes


def format_summary(summary: Summary) -> str:
    lines = [
        f"scheduler: {summary.scheduler}",
        f"passengers: {summary.passengers}   ticks simulated: {summary.ticks}",
        "",
        f"{'':8}{'min':>6}{'max':>6}{'mean':>8}{'p50':>7}{'p90':>7}",
    ]
    for label, d in (("wait", summary.wait), ("travel", summary.travel), ("total", summary.total)):
        lines.append(f"{label:8}{d.min:>6}{d.max:>6}{d.mean:>8.2f}{d.p50:>7g}{d.p90:>7g}")
    lines.append("")
    lines.append("observations:")
    lines.extend(f"  - {note}" for note in summary.observations)
    return "\n".join(lines)
