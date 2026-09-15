"""Passenger statistics and generated observations (docs/ASSUMPTIONS.md A19)."""

from __future__ import annotations

import math
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
            mean=sum(s) / len(s),
            p50=percentile(s, 50),
            p90=percentile(s, 90),
        )


def percentile(sorted_values: list[int], pct: float) -> float:
    """Nearest-rank percentile on an already sorted list: value at rank ceil(p/100 * n)."""
    if not sorted_values:
        return 0.0
    rank = max(1, math.ceil(pct / 100 * len(sorted_values)))
    return float(sorted_values[min(rank, len(sorted_values)) - 1])


@dataclass(frozen=True, slots=True)
class CarUsage:
    """How much work one car did (docs/ASSUMPTIONS.md A20)."""

    car: int  # 1-based, as printed everywhere else
    carried: int  # passengers delivered by this car
    stops: int
    floors_travelled: int
    busy_ticks: int  # ticks with a passenger aboard or assigned and waiting
    busy_share: float  # busy_ticks / ticks simulated


@dataclass(frozen=True, slots=True)
class Balance:
    """How evenly the work was spread across cars (A20).

    ``busy_spread`` is the gap between the busiest and the least busy car's share of
    ticks; ``carried_max_share`` is the busiest car's share of delivered passengers,
    to be read against ``fair_share`` = 1 / cars. Both are 0 for a single car.
    """

    busy_mean: float
    busy_spread: float
    carried_max_share: float
    fair_share: float


@dataclass(frozen=True, slots=True)
class Summary:
    scheduler: str
    passengers: int
    ticks: int
    wait: Distribution
    travel: Distribution
    total: Distribution
    cars: list[CarUsage]
    balance: Balance
    observations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize(result: SimulationResult) -> Summary:
    served = [p for p in result.passengers if p.alight_time is not None]
    waits = [p.wait for p in served if p.wait is not None]
    travels = [p.travel for p in served if p.travel is not None]
    totals = [p.total for p in served if p.total is not None]
    cars = car_usage(result)
    return Summary(
        scheduler=result.scheduler,
        passengers=len(result.passengers),
        ticks=result.ticks,
        wait=Distribution.of(waits),
        travel=Distribution.of(travels),
        total=Distribution.of(totals),
        cars=cars,
        balance=balance(cars, result.ticks),
        observations=observations(result),
    )


def car_usage(result: SimulationResult) -> list[CarUsage]:
    served = [p for p in result.passengers if p.alight_time is not None]
    out: list[CarUsage] = []
    for car in result.cars:
        busy = sum(1 for t in result.car_states if t[car.index]["load"] or t[car.index]["waiting"])
        out.append(
            CarUsage(
                car=car.index + 1,
                carried=sum(1 for p in served if p.car == car.index),
                stops=car.stops_made,
                floors_travelled=car.floors_travelled,
                busy_ticks=busy,
                busy_share=busy / result.ticks if result.ticks else 0.0,
            )
        )
    return out


def balance(cars: list[CarUsage], ticks: int) -> Balance:
    if not cars:
        return Balance(0.0, 0.0, 0.0, 0.0)
    shares = [c.busy_share for c in cars]
    carried = sum(c.carried for c in cars)
    # Integer sum, one division: identical on every Python version and in the JS port.
    # (Python 3.12 changed float sum() to compensated summation, which moved the last
    # digit of a mean of floats and broke the golden results on one CI leg.)
    busy_total = sum(c.busy_ticks for c in cars)
    return Balance(
        busy_mean=busy_total / (len(cars) * ticks) if ticks else 0.0,
        busy_spread=max(shares) - min(shares),
        carried_max_share=max(c.carried for c in cars) / carried if carried else 0.0,
        fair_share=1 / len(cars),
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
    if waits and median > 0:
        long_waits = sum(1 for w in waits if w > 2 * median)
        notes.append(
            f"{long_waits} of {len(waits)} passengers ({100 * long_waits / len(waits):.0f}%) "
            f"waited more than twice the median wait of {median:g} ticks"
        )
    elif waits:
        notes.append("median wait is 0 ticks: most passengers boarded immediately")
    zero = sum(1 for w in waits if w == 0)
    if zero:
        notes.append(f"{zero} passengers boarded in the tick they requested (wait 0)")

    origins = Counter(p.source for p in served)
    floor, n = origins.most_common(1)[0]
    notes.append(f"busiest origin floor: {floor} ({n} of {len(served)} requests)")

    up = sum(1 for p in served if p.dest > p.source)
    notes.append(f"direction mix: {up} up, {len(served) - up} down")

    cars = car_usage(result)
    for c in cars:
        notes.append(
            f"elevator {c.car}: carried {c.carried}, stops {c.stops}, "
            f"floors travelled {c.floors_travelled}, busy {100 * c.busy_share:.0f}% of ticks"
        )
    if len(cars) > 1:
        b = balance(cars, result.ticks)
        busiest = max(cars, key=lambda c: c.carried)
        notes.append(
            f"work balance: elevator {busiest.car} carried {100 * b.carried_max_share:.0f}% "
            f"of passengers (fair share {100 * b.fair_share:.0f}%); "
            f"busy share ranges over {100 * b.busy_spread:.0f} points"
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
    lines.append(f"{'car':8}{'carried':>8}{'stops':>7}{'floors':>8}{'busy':>7}")
    for c in summary.cars:
        busy = f"{100 * c.busy_share:.0f}%"
        lines.append(f"{c.car:<8}{c.carried:>8}{c.stops:>7}{c.floors_travelled:>8}{busy:>7}")
    lines.append("")
    lines.append("observations:")
    lines.extend(f"  - {note}" for note in summary.observations)
    return "\n".join(lines)
