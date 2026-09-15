"""Command-line interface: ``python -m elevator_sim run ...``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compare import parse_floors
from .config import SimulationConfig
from .io import read_requests, write_positions, write_trace
from .metrics import format_summary, summarize
from .schedulers import SCHEDULERS, make_scheduler
from .simulation import Simulation
from .validate import InvalidInputError, tick_bound, validate_feasibility


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
        "--park-schedule",
        default=None,
        metavar="TICK:FLOOR,...",
        help="time-of-day parking, e.g. 0:1,900:16 (floor 1 from tick 0, floor 16 from tick 900)",
    )
    p.add_argument(
        "--express",
        action="append",
        default=[],
        metavar="CAR:FLOORS",
        help="restrict a car to floors, e.g. 3:1,30-51 (1-based car index)",
    )


def _parse_schedule(spec: str | None) -> tuple[tuple[int, int], ...]:
    """``"0:1,900:16"`` -> ((0, 1), (900, 16))."""
    if not spec:
        return ()
    out = []
    for part in spec.split(","):
        tick, sep, floor = part.partition(":")
        if not sep or not tick.strip().isdigit() or not floor.strip().isdigit():
            raise ValueError(
                f"--park-schedule expects TICK:FLOOR pairs such as 0:1,900:16, got {part!r}"
            )
        out.append((int(tick), int(floor)))
    return tuple(out)


def _config_from_args(a: argparse.Namespace) -> SimulationConfig:
    served: dict[int, frozenset[int]] = {}
    for spec in a.express:
        car, sep, floors = spec.partition(":")
        try:
            if not sep or not car.isdigit():
                raise ValueError
            served[int(car) - 1] = frozenset(parse_floors(floors))
        except ValueError:
            raise ValueError(
                f"--express expects CAR:FLOORS such as 3:1,30-51, got {spec!r}"
            ) from None
    return SimulationConfig(
        elevators=a.elevators,
        floors=a.floors,
        capacity=a.capacity,
        dwell_ticks=a.dwell,
        start_floor=a.start_floor,
        park_floor=a.park_floor,
        park_schedule=_parse_schedule(a.park_schedule),
        served_floors=served,
    )


def cmd_run(a: argparse.Namespace) -> int:
    config = _config_from_args(a)
    requests = read_requests(a.requests, config.floors)
    validate_feasibility(requests, config)
    scheduler = make_scheduler(a.scheduler, fairness=a.fairness)
    result = Simulation(config, scheduler, requests).run(max_ticks=tick_bound(requests, config))
    out = a.out
    write_positions(result, out / "positions.csv")
    write_trace(result, out / "trace.json")
    summary = summarize(result)
    (out / "summary.json").write_text(json.dumps(summary.to_dict(), indent=2) + "\n")
    print(format_summary(summary))
    print(f"\nwrote {out / 'positions.csv'}, {out / 'trace.json'}, {out / 'summary.json'}")
    return 0


def cmd_compare(a: argparse.Namespace) -> int:
    from .compare import Variant, format_markdown, format_table, load_manifest, run_matrix

    scenarios = load_manifest(a.manifest)
    if a.scenario:
        scenarios = [s for s in scenarios if s.name in a.scenario]
    variants = [Variant(name) for name in a.schedulers.split(",")]
    variants += [Variant("etd", fairness=w) for w in a.fairness]
    rows = run_matrix(
        scenarios, variants, dwell_ticks=a.dwell, trace_dir=a.out / "traces" if a.traces else None
    )
    print(format_table(rows))
    a.out.mkdir(parents=True, exist_ok=True)
    if a.traces:
        index = [
            {
                "scenario": s.name,
                "description": s.description,
                "floors": s.floors,
                "elevators": s.elevators,
                "capacity": s.capacity,
                "park_floor": s.park_floor,
                "express": {str(k + 1): sorted(v) for k, v in s.served_floors.items()},
                "schedulers": [v.label for v in variants],
            }
            for s in scenarios
        ]
        (a.out / "traces" / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    (a.out / "comparison.json").write_text(json.dumps(rows, indent=2) + "\n")
    (a.out / "comparison.md").write_text(format_markdown(rows) + "\n")
    print(
        f"\nwrote {a.out / 'comparison.json'}, {a.out / 'comparison.md'}"
        + (f", traces in {a.out / 'traces'}" if a.traces else "")
    )
    return 0


def cmd_report(a: argparse.Namespace) -> int:
    from .report import build_report

    for path in build_report(a.manifest, a.out, a.fairness, dwell=a.dwell):
        print(f"wrote {path}")
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

    cmp_ = sub.add_parser("compare", help="run every scheduler on every scenario in a manifest")
    cmp_.add_argument("--manifest", type=Path, default=Path("scenarios/manifest.json"))
    cmp_.add_argument("--scenario", action="append", default=[], help="limit to these names")
    cmp_.add_argument("--schedulers", default=",".join(sorted(SCHEDULERS)))
    cmp_.add_argument(
        "--fairness",
        type=float,
        action="append",
        default=[],
        help="also run ETD with this fairness weight (repeatable)",
    )
    cmp_.add_argument("--dwell", type=int, default=1)
    cmp_.add_argument("--traces", action="store_true", help="write a JSON trace per run")
    cmp_.add_argument("--out", type=Path, default=Path("outputs/compare"))
    cmp_.set_defaults(func=cmd_compare)

    rep = sub.add_parser("report", help="render PNG charts (needs the viz extra)")
    rep.add_argument("--manifest", type=Path, default=Path("scenarios/manifest.json"))
    rep.add_argument("--fairness", type=float, action="append", default=[])
    rep.add_argument("--dwell", type=int, default=1)
    rep.add_argument("--out", type=Path, default=Path("docs/charts"))
    rep.set_defaults(func=cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (InvalidInputError, ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
