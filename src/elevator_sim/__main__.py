"""Command-line interface: ``python -m elevator_sim run ...``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import SimulationConfig
from .io import read_requests, write_positions, write_trace
from .metrics import format_summary, summarize
from .schedulers import SCHEDULERS, make_scheduler
from .simulation import Simulation
from .validate import InvalidInputError


def _add_config_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--elevators", type=int, default=4)
    p.add_argument("--floors", type=int, default=51)
    p.add_argument("--capacity", type=int, default=8)
    p.add_argument("--dwell", type=int, default=1, help="ticks spent at each stop (default 1)")
    p.add_argument("--start-floor", type=int, default=1)
    p.add_argument(
        "--park-floor",
        type=int,
        default=None,
        help="send idle cars to this floor (default: stay put)",
    )
    p.add_argument(
        "--express",
        action="append",
        default=[],
        metavar="CAR:FLOORS",
        help="restrict a car to floors, e.g. 3:1,30-51 (1-based car index)",
    )


def _config_from_args(a: argparse.Namespace) -> SimulationConfig:
    served: dict[int, frozenset[int]] = {}
    for spec in a.express:
        car, _, floors = spec.partition(":")
        served[int(car) - 1] = frozenset(_parse_floors(floors))
    return SimulationConfig(
        elevators=a.elevators,
        floors=a.floors,
        capacity=a.capacity,
        dwell_ticks=a.dwell,
        start_floor=a.start_floor,
        park_floor=a.park_floor,
        served_floors=served,
    )


def _parse_floors(spec: str) -> set[int]:
    out: set[int] = set()
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        out.update(range(int(lo), int(hi or lo) + 1))
    return out


def cmd_run(a: argparse.Namespace) -> int:
    config = _config_from_args(a)
    requests = read_requests(a.requests, config.floors)
    scheduler = make_scheduler(a.scheduler, fairness=a.fairness)
    result = Simulation(config, scheduler, requests).run()
    out = a.out
    write_positions(result, out / "positions.csv")
    write_trace(result, out / "trace.json")
    summary = summarize(result)
    (out / "summary.json").write_text(json.dumps(summary.to_dict(), indent=2) + "\n")
    print(format_summary(summary))
    print(f"\nwrote {out / 'positions.csv'}, {out / 'trace.json'}, {out / 'summary.json'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="elevator-sim", description="Destination-dispatch elevator simulation"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="simulate one request file with one scheduler")
    run.add_argument("requests", type=Path, help="CSV with columns time,id,source,dest")
    run.add_argument("--scheduler", choices=sorted(SCHEDULERS), default="etd")
    run.add_argument(
        "--fairness", type=float, default=0.0, help="ETD fairness weight (0 = pure efficiency)"
    )
    run.add_argument("--out", type=Path, default=Path("outputs/run"))
    _add_config_args(run)
    run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (InvalidInputError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
