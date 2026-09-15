"""Seed-robustness study: re-run every generated pattern with fresh seeds.

The committed scenarios are one seed each, which fixes the *direction* of a
finding but not its size. This script regenerates each pattern with ``SEEDS``
fresh seeds, runs every scheduler variant on each, and reports means with
standard deviations, win counts, and the sign of each policy effect, so that
every recommendation in the documents can say how often it held::

    uv run python scenarios/robustness.py            # writes docs/results/robustness.{md,json}

Deterministic: the seed list is fixed and the engine is deterministic, so the
output regenerates byte for byte.
"""

from __future__ import annotations

import json
import statistics
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from elevator_sim.compare import parse_floors  # noqa: E402
from elevator_sim.config import SimulationConfig  # noqa: E402
from elevator_sim.metrics import summarize  # noqa: E402
from elevator_sim.model import Request  # noqa: E402
from elevator_sim.schedulers import make_scheduler  # noqa: E402
from elevator_sim.simulation import Simulation  # noqa: E402
from elevator_sim.validate import tick_bound  # noqa: E402
from generate import SCENARIOS, Traffic, generate  # noqa: E402

SEEDS = list(range(101, 121))
VARIANTS: list[tuple[str, float]] = [
    ("etd", 0.0),
    ("nearest_car", 0.0),
    ("nearest_car_balanced", 0.0),
    ("round_robin", 0.0),
    ("etd", 0.5),
]
ZONES = {0: "1-26", 1: "1-26", 2: "1-26", 3: "1,27-51", 4: "1,27-51", 5: "1,27-51"}
OUT = HERE.parent / "docs" / "results"


def label(name: str, fairness: float) -> str:
    return make_scheduler(name, fairness=fairness).name


def run_one(
    t: Traffic,
    seed: int,
    name: str,
    fairness: float,
    park_floor: int | None = None,
    zoned: bool = False,
) -> dict[str, float]:
    requests = [Request(*row) for row in generate(replace(t, seed=seed))]
    config = SimulationConfig(
        elevators=t.elevators,
        floors=t.floors,
        capacity=t.capacity,
        dwell_ticks=1,
        park_floor=park_floor,
        served_floors=(
            {car: frozenset(parse_floors(spec)) for car, spec in ZONES.items()} if zoned else {}
        ),
    )
    result = Simulation(config, make_scheduler(name, fairness=fairness), requests).run(
        max_ticks=tick_bound(requests, config)
    )
    s = summarize(result)
    return {
        "wait_avg": s.wait.mean,
        "wait_p90": s.wait.p90,
        "wait_max": float(s.wait.max),
        "total_avg": s.total.mean,
        "busy_spread": s.balance.busy_spread,
    }


def mean_sd(xs: list[float]) -> tuple[float, float]:
    return statistics.fmean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0)


def study() -> dict[str, Any]:
    out: dict[str, Any] = {"seeds": SEEDS, "patterns": {}}
    for t in SCENARIOS:
        per: dict[str, list[dict[str, float]]] = {}
        for name, w in VARIANTS:
            per[label(name, w)] = [run_one(t, seed, name, w) for seed in SEEDS]
        pattern: dict[str, Any] = {"floors": t.floors, "elevators": t.elevators, "variants": {}}
        for lab, runs in per.items():
            pattern["variants"][lab] = {
                k: dict(zip(("mean", "sd"), mean_sd([r[k] for r in runs]), strict=True))
                for k in runs[0]
            }
        etd, nc, ncb, rr, f = (
            per["etd"],
            per["nearest_car"],
            per["nearest_car_balanced"],
            per["round_robin"],
            per["etd_f0.5"],
        )
        n = len(SEEDS)
        pattern["etd_lowest_avg_wait"] = sum(
            1
            for i in range(n)
            if etd[i]["wait_avg"] <= min(nc[i]["wait_avg"], ncb[i]["wait_avg"], rr[i]["wait_avg"])
        )
        pattern["ratio_nearest_over_etd"] = dict(
            zip(
                ("mean", "sd"),
                mean_sd([nc[i]["wait_avg"] / etd[i]["wait_avg"] for i in range(n)]),
                strict=True,
            )
        )
        pattern["ratio_nearest_balanced_over_etd"] = dict(
            zip(
                ("mean", "sd"),
                mean_sd([ncb[i]["wait_avg"] / etd[i]["wait_avg"] for i in range(n)]),
                strict=True,
            )
        )
        pattern["ratio_round_robin_over_etd"] = dict(
            zip(
                ("mean", "sd"),
                mean_sd([rr[i]["wait_avg"] / etd[i]["wait_avg"] for i in range(n)]),
                strict=True,
            )
        )
        pattern["fairness_0.5"] = {
            "max_lower": sum(1 for i in range(n) if f[i]["wait_max"] < etd[i]["wait_max"]),
            "p90_lower": sum(1 for i in range(n) if f[i]["wait_p90"] < etd[i]["wait_p90"]),
            "avg_higher": sum(1 for i in range(n) if f[i]["wait_avg"] > etd[i]["wait_avg"]),
            "spread_lower": sum(1 for i in range(n) if f[i]["busy_spread"] < etd[i]["busy_spread"]),
        }
        if t.name == "morning_up_peak":
            parked = [run_one(t, seed, "etd", 0.0, park_floor=1) for seed in SEEDS]
            pattern["parking"] = {
                "avg_lower": sum(1 for i in range(n) if parked[i]["wait_avg"] < etd[i]["wait_avg"]),
                "avg_reduction_pct": dict(
                    zip(
                        ("mean", "sd"),
                        mean_sd(
                            [
                                100 * (1 - parked[i]["wait_avg"] / etd[i]["wait_avg"])
                                for i in range(n)
                            ]
                        ),
                        strict=True,
                    )
                ),
            }
        if t.name == "tall_lobby_traffic":
            zoned = [run_one(t, seed, "etd", 0.0, zoned=True) for seed in SEEDS]
            pattern["zoning"] = {
                "avg_worse": sum(1 for i in range(n) if zoned[i]["wait_avg"] > etd[i]["wait_avg"]),
                "zoned_avg": dict(
                    zip(("mean", "sd"), mean_sd([z["wait_avg"] for z in zoned]), strict=True)
                ),
                "free_avg": dict(
                    zip(("mean", "sd"), mean_sd([e["wait_avg"] for e in etd]), strict=True)
                ),
            }
        out["patterns"][t.name] = pattern
    return out


def fmt(ms: dict[str, float], digits: int = 1) -> str:
    return f"{ms['mean']:.{digits}f} ± {ms['sd']:.{digits}f}"


def render(study_out: dict[str, Any]) -> str:
    n = len(study_out["seeds"])
    lines = [
        f"# Seed robustness — {n} fresh seeds per pattern",
        "",
        f"Seeds {study_out['seeds'][0]} to {study_out['seeds'][-1]}, none of them the committed "
        "one. Mean ± standard deviation over seeds; ticks throughout. "
        "Regenerate with `uv run python scenarios/robustness.py`.",
        "",
        "## Average wait per variant",
        "",
        "| pattern | etd | nearest_car | nearest_car_balanced | round_robin | etd_f0.5 "
        "| etd lowest |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, p in study_out["patterns"].items():
        v = p["variants"]
        lines.append(
            f"| {name} | {fmt(v['etd']['wait_avg'])} | {fmt(v['nearest_car']['wait_avg'])} | "
            f"{fmt(v['nearest_car_balanced']['wait_avg'])} | {fmt(v['round_robin']['wait_avg'])} "
            f"| {fmt(v['etd_f0.5']['wait_avg'])} | {p['etd_lowest_avg_wait']}/{n} |"
        )
    lines += [
        "",
        "## Ratios of average wait to ETD",
        "",
        "| pattern | nearest_car / etd | nearest_car_balanced / etd | round_robin / etd |",
        "|---|---:|---:|---:|",
    ]
    for name, p in study_out["patterns"].items():
        lines.append(
            f"| {name} | {fmt(p['ratio_nearest_over_etd'], 2)} | "
            f"{fmt(p['ratio_nearest_balanced_over_etd'], 2)} | "
            f"{fmt(p['ratio_round_robin_over_etd'], 2)} |"
        )
    lines += [
        "",
        f"## Fairness weight 0.5 against plain ETD (seeds out of {n} in which the weight …)",
        "",
        "| pattern | lowers max wait | lowers p90 wait | raises avg wait | narrows busy spread |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, p in study_out["patterns"].items():
        f = p["fairness_0.5"]
        lines.append(
            f"| {name} | {f['max_lower']} | {f['p90_lower']} | {f['avg_higher']} | "
            f"{f['spread_lower']} |"
        )
    park = study_out["patterns"]["morning_up_peak"]["parking"]
    zone = study_out["patterns"]["tall_lobby_traffic"]["zoning"]
    lines += [
        "",
        "## Policies",
        "",
        f"- Parking idle cars at the lobby (morning up-peak, ETD): average wait lower in "
        f"{park['avg_lower']}/{n} seeds; reduction {fmt(park['avg_reduction_pct'])}%.",
        f"- Zoning three local + three express cars (tall lobby traffic, ETD): average wait "
        f"worse than six free cars in {zone['avg_worse']}/{n} seeds; zoned "
        f"{fmt(zone['zoned_avg'])} against free {fmt(zone['free_avg'])}.",
        "",
        "## Maximum wait per variant",
        "",
        "| pattern | etd | etd_f0.5 | nearest_car | round_robin |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, p in study_out["patterns"].items():
        v = p["variants"]
        lines.append(
            f"| {name} | {fmt(v['etd']['wait_max'])} | {fmt(v['etd_f0.5']['wait_max'])} | "
            f"{fmt(v['nearest_car']['wait_max'])} | {fmt(v['round_robin']['wait_max'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    result = study()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "robustness.json").write_text(json.dumps(result, indent=2) + "\n")
    (OUT / "robustness.md").write_text(render(result))
    print(render(result))


if __name__ == "__main__":
    main()
