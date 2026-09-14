"""Input validation (docs/ASSUMPTIONS.md A15). Fails fast with the offending row named."""

from __future__ import annotations

from collections.abc import Iterable

from .config import SimulationConfig
from .model import Request


class InvalidInputError(ValueError):
    pass


REQUIRED = ("time", "id", "source", "dest")


def parse_row(row: dict[str, str], line: int) -> Request:
    missing = [k for k in REQUIRED if k not in row]
    if missing:
        raise InvalidInputError(f"line {line}: missing column {missing[0]!r}")
    if any(row[k] is None for k in REQUIRED):
        raise InvalidInputError(f"line {line}: expected 4 fields (time,id,source,dest)")
    try:
        time = int(row["time"])
        source = int(row["source"])
        dest = int(row["dest"])
        ident = row["id"].strip()
    except ValueError:
        raise InvalidInputError(f"line {line}: time, source and dest must be integers") from None
    if not ident:
        raise InvalidInputError(f"line {line}: empty id")
    return Request(time=time, id=ident, source=source, dest=dest)


def validate_requests(requests: Iterable[Request], floors: int) -> list[Request]:
    seen: set[str] = set()
    out: list[Request] = []
    for r in requests:
        if r.time < 0:
            raise InvalidInputError(f"request {r.id}: negative time {r.time}")
        if r.source == r.dest:
            raise InvalidInputError(f"request {r.id}: source and dest are both {r.source}")
        for label, floor in (("source", r.source), ("dest", r.dest)):
            if not 1 <= floor <= floors:
                raise InvalidInputError(
                    f"request {r.id}: {label} floor {floor} outside 1..{floors}"
                )
        if r.id in seen:
            raise InvalidInputError(f"duplicate passenger id {r.id}")
        seen.add(r.id)
        out.append(r)
    return out


def validate_feasibility(requests: Iterable[Request], config: SimulationConfig) -> None:
    """Reject, before the run starts, any request no car could ever serve (express zones)."""
    zones = [config.served_floors.get(i) for i in range(config.elevators)]
    for r in requests:
        if not any(z is None or (r.source in z and r.dest in z) for z in zones):
            raise InvalidInputError(
                f"request {r.id}: no elevator serves both floor {r.source} and floor {r.dest}"
            )


def tick_bound(requests: list[Request], config: SimulationConfig) -> int:
    """Generous upper bound on ticks; exceeding it means a livelock, not a slow run."""
    last = max((r.time for r in requests), default=0)
    return last + 10 * config.floors * (len(requests) + 1) * (config.dwell_ticks + 1) + 100
