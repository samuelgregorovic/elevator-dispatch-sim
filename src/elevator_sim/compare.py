"""Run every scheduler on every scenario in a manifest and tabulate the results."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import SimulationConfig
from .io import read_requests, write_trace
from .metrics import summarize
from .schedulers import make_scheduler
from .simulation import Simulation
from .validate import tick_bound, validate_feasibility


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    file: Path
    floors: int
    elevators: int
    capacity: int
    description: str = ""
    park_floor: int | None = None
    served_floors: dict[int, frozenset[int]] = field(default_factory=dict)

    def config(self, dwell_ticks: int = 1) -> SimulationConfig:
        return SimulationConfig(
            elevators=self.elevators,
            floors=self.floors,
            capacity=self.capacity,
            dwell_ticks=dwell_ticks,
            park_floor=self.park_floor,
            served_floors=self.served_floors,
        )


def load_manifest(path: Path) -> list[Scenario]:
    entries = json.loads(path.read_text())
    return [
        Scenario(
            name=e["name"],
            file=path.parent / e["file"],
            floors=e["floors"],
            elevators=e["elevators"],
            capacity=e["capacity"],
            description=e.get("description", ""),
            park_floor=e.get("park_floor"),
            served_floors={
                int(car) - 1: frozenset(parse_floors(spec))
                for car, spec in e.get("express", {}).items()
            },
        )
        for e in entries
    ]


def parse_floors(spec: str) -> set[int]:
    """``"1,27-51"`` -> {1, 27, 28, ..., 51}."""
    out: set[int] = set()
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        out.update(range(int(lo), int(hi or lo) + 1))
    return out


@dataclass(frozen=True, slots=True)
class Variant:
    """A scheduler name plus its parameters, e.g. ETD with a fairness weight."""

    scheduler: str
    fairness: float = 0.0

    @property
    def label(self) -> str:
        return make_scheduler(self.scheduler, fairness=self.fairness).name


def run_matrix(
    scenarios: list[Scenario],
    variants: list[Variant],
    dwell_ticks: int = 1,
    trace_dir: Path | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        requests = read_requests(scenario.file, scenario.floors)
        config = scenario.config(dwell_ticks)
        validate_feasibility(requests, config)
        for variant in variants:
            scheduler = make_scheduler(variant.scheduler, fairness=variant.fairness)
            result = Simulation(config, scheduler, requests).run(
                max_ticks=tick_bound(requests, config)
            )
            summary = summarize(result)
            if trace_dir is not None:
                write_trace(result, trace_dir / f"{scenario.name}__{scheduler.name}.json")
            rows.append(
                {
                    "scenario": scenario.name,
                    "scheduler": scheduler.name,
                    "passengers": summary.passengers,
                    "ticks": summary.ticks,
                    "wait": _d(summary.wait),
                    "total": _d(summary.total),
                    "observations": summary.observations,
                }
            )
    return rows


def _d(dist: Any) -> dict[str, float]:
    return {k: getattr(dist, k) for k in ("count", "min", "max", "mean", "p50", "p90")}


def format_table(rows: list[dict[str, Any]]) -> str:
    header = (
        f"{'scenario':18} {'scheduler':12} {'n':>4} {'ticks':>6} "
        f"{'wait avg':>9} {'wait p90':>9} {'wait max':>9} "
        f"{'total avg':>10} {'total p90':>10} {'total max':>10}"
    )
    lines = [header, "-" * len(header)]
    last = None
    for r in rows:
        if last is not None and r["scenario"] != last:
            lines.append("")
        last = r["scenario"]
        w, t = r["wait"], r["total"]
        lines.append(
            f"{r['scenario']:18} {r['scheduler']:12} {r['passengers']:>4} {r['ticks']:>6} "
            f"{w['mean']:>9.1f} {w['p90']:>9.0f} {w['max']:>9.0f} "
            f"{t['mean']:>10.1f} {t['p90']:>10.0f} {t['max']:>10.0f}"
        )
    return "\n".join(lines)


def format_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| scenario | scheduler | n | ticks | wait avg | wait p90 | wait max "
        "| total avg | total p90 | total max |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        w, t = r["wait"], r["total"]
        lines.append(
            f"| {r['scenario']} | {r['scheduler']} | {r['passengers']} | {r['ticks']} | "
            f"{w['mean']:.1f} | {w['p90']:.0f} | {w['max']:.0f} | "
            f"{t['mean']:.1f} | {t['p90']:.0f} | {t['max']:.0f} |"
        )
    return "\n".join(lines)
