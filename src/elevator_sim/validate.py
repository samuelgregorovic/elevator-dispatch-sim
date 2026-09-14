"""Input validation (docs/ASSUMPTIONS.md A15). Fails fast with the offending row named."""

from __future__ import annotations

from collections.abc import Iterable

from .model import Request


class InvalidInputError(ValueError):
    pass


def parse_row(row: dict[str, str], line: int) -> Request:
    try:
        time = int(row["time"])
        source = int(row["source"])
        dest = int(row["dest"])
        ident = row["id"].strip()
    except KeyError as exc:
        raise InvalidInputError(f"line {line}: missing column {exc}") from None
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
