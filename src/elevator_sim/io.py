"""Reading requests, writing the positions log and the JSON trace."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .model import Request
from .simulation import SimulationResult
from .validate import parse_row, validate_requests


def read_requests(path: Path, floors: int) -> list[Request]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = [parse_row(row, line) for line, row in enumerate(reader, start=2)]
    return validate_requests(rows, floors)


def write_positions(result: SimulationResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["time", *[f"elevator_{i + 1}" for i in range(result.config.elevators)]])
        for t, row in enumerate(result.positions):
            writer.writerow([t, *row])


def write_trace(result: SimulationResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg = result.config
    payload = {
        "scheduler": result.scheduler,
        "config": {
            "elevators": cfg.elevators,
            "floors": cfg.floors,
            "capacity": cfg.capacity,
            "dwell_ticks": cfg.dwell_ticks,
            "start_floor": cfg.start_floor,
            "park_floor": cfg.park_floor,
            "park_schedule": [list(e) for e in cfg.park_schedule],
            "served_floors": {str(k): sorted(v) for k, v in cfg.served_floors.items()},
        },
        "ticks": result.ticks,
        "cars": result.car_states,
        "events": result.events,
        "passengers": [
            {
                "id": p.id,
                "t": p.request_time,
                "source": p.source,
                "dest": p.dest,
                "car": p.car,
                "board": p.board_time,
                "alight": p.alight_time,
            }
            for p in result.passengers
        ],
    }
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
