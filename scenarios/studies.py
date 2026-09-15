"""Sensitivity studies: dwell, load, car count, resilience, and the office day.

Each study answers one question the single-seed comparison cannot::

    dwell        does the ranking hold when a stop costs 0, 1 or 2 ticks?
    load         where does each rule break down as arrivals scale up?
    cars         how many cars does each rule need to hit a service level?
    resilience   how fast does each rule recover from a sudden burst?
    day          across a whole office day, does time-of-day parking pay?

    uv run python scenarios/studies.py           # writes docs/results/studies.{md,json}
                                                 # and, with matplotlib, docs/charts/*.png

Deterministic: fixed seeds, deterministic engine, byte-identical output.
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

from elevator_sim.config import SimulationConfig  # noqa: E402
from elevator_sim.metrics import LONG_WAIT_TICKS, summarize  # noqa: E402
from elevator_sim.model import Request  # noqa: E402
from elevator_sim.schedulers import make_scheduler  # noqa: E402
from elevator_sim.simulation import Simulation, SimulationResult  # noqa: E402
from elevator_sim.validate import tick_bound  # noqa: E402
from generate import SCENARIOS, Traffic, generate, segment_bounds  # noqa: E402

RULES = ["etd", "nearest_car", "round_robin"]
SEEDS = [101, 102, 103, 104, 105]
RATES = [0.5, 0.75, 1.0, 1.5, 2.0]
CAR_RANGE = {"morning_up_peak": range(2, 9), "tall_building": range(3, 11)}
SERVICE_TARGET = 0.10  # at most 10% of passengers waiting longer than LONG_WAIT_TICKS
SPIKE = {"tick": 200, "floor": 14, "people": 30}
DAY_SCHEDULE = ((0, 1), (300, 10), (600, 1), (900, 10), (1200, 16))
OUT = HERE.parent / "docs" / "results"
CHARTS = HERE.parent / "docs" / "charts"
PATTERNS = [t for t in SCENARIOS if not t.segments]
DAY = next(t for t in SCENARIOS if t.name == "office_day")


def run(
    t: Traffic,
    rule: str,
    *,
    seed: int | None = None,
    dwell: int = 1,
    rate_scale: float = 1.0,
    elevators: int | None = None,
    extra: list[tuple[int, str, int, int]] | None = None,
    park_floor: int | None = None,
    park_schedule: tuple[tuple[int, int], ...] = (),
) -> SimulationResult:
    traffic = replace(t, seed=seed if seed is not None else t.seed)
    if rate_scale != 1.0:
        traffic = replace(
            traffic,
            rate=traffic.rate * rate_scale,
            segments=tuple(replace(s, rate=s.rate * rate_scale) for s in traffic.segments),
        )
    rows = generate(traffic) + (extra or [])
    rows.sort(key=lambda r: r[0])
    requests = [Request(*r) for r in rows]
    config = SimulationConfig(
        elevators=elevators or t.elevators,
        floors=t.floors,
        capacity=t.capacity,
        dwell_ticks=dwell,
        park_floor=park_floor,
        park_schedule=park_schedule,
    )
    return Simulation(config, make_scheduler(rule), requests).run(
        max_ticks=tick_bound(requests, config)
    )


def stats(result: SimulationResult) -> dict[str, float]:
    s = summarize(result)
    return {
        "wait_avg": s.wait.mean,
        "wait_p90": s.wait.p90,
        "wait_max": float(s.wait.max),
        "over_share": s.service.over_share,
        "stops_per_trip": s.efficiency.stops_per_trip,
        "floors_per_passenger": s.efficiency.floors_per_passenger,
    }


def mean_sd(xs: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(xs),
        "sd": statistics.stdev(xs) if len(xs) > 1 else 0.0,
    }


def agg(runs: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    return {k: mean_sd([r[k] for r in runs]) for k in runs[0]}


def backlog(result: SimulationResult) -> list[int]:
    """People waiting (requested, not yet boarded) at each tick."""
    delta = [0] * (result.ticks + 1)
    for p in result.passengers:
        delta[p.request_time] += 1
        if p.board_time is not None:
            delta[min(p.board_time, result.ticks)] -= 1
    out, cur = [], 0
    for t in range(result.ticks):
        cur += delta[t]
        out.append(cur)
    return out


# ---------------------------------------------------------------------------- studies


def study_dwell() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for t in [*PATTERNS, DAY]:
        out[t.name] = {
            str(d): {rule: stats(run(t, rule, dwell=d)) for rule in RULES} for d in (0, 1, 2)
        }
    return out


def study_load() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for t in PATTERNS:
        out[t.name] = {}
        for scale in RATES:
            out[t.name][str(scale)] = {
                rule: agg([stats(run(t, rule, seed=s, rate_scale=scale)) for s in SEEDS])
                for rule in RULES
            }
    return out


def study_cars() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, cars in CAR_RANGE.items():
        t = next(x for x in PATTERNS if x.name == name)
        out[name] = {"by_cars": {}, "cars_needed": {}}
        for n in cars:
            out[name]["by_cars"][str(n)] = {
                rule: agg([stats(run(t, rule, seed=s, elevators=n)) for s in SEEDS])
                for rule in RULES
            }
        for rule in RULES:
            needed = next(
                (
                    n
                    for n in cars
                    if out[name]["by_cars"][str(n)][rule]["over_share"]["mean"] <= SERVICE_TARGET
                ),
                None,
            )
            out[name]["cars_needed"][rule] = needed
    return out


def study_resilience() -> dict[str, Any]:
    t = next(x for x in PATTERNS if x.name == "morning_up_peak")
    spike = [(SPIKE["tick"], f"s{i:03d}", SPIKE["floor"], 1) for i in range(SPIKE["people"])]
    out: dict[str, Any] = {"spike": SPIKE, "seeds": {}, "series": {}}
    per_rule: dict[str, list[dict[str, float]]] = {r: [] for r in RULES}
    for seed in [*SEEDS, t.seed]:
        for rule in RULES:
            base = backlog(run(t, rule, seed=seed))
            hit = run(t, rule, seed=seed, extra=spike)
            series = backlog(hit)
            n = min(len(base), len(series))
            recovered = next(
                (k for k in range(SPIKE["tick"] + 1, n) if series[k] <= base[k]),
                n,
            )
            rec = {
                "peak_backlog": float(max(series[SPIKE["tick"] :])),
                "recovery_ticks": float(recovered - SPIKE["tick"]),
                "spike_wait_avg": statistics.fmean(
                    p.wait for p in hit.passengers if p.id.startswith("s") and p.wait is not None
                ),
            }
            if seed == t.seed:
                out["series"][rule] = {"base": base, "spike": series}
            else:
                per_rule[rule].append(rec)
    out["seeds"] = {rule: agg(runs) for rule, runs in per_rule.items()}
    return out


def study_day() -> dict[str, Any]:
    bounds = segment_bounds(DAY)
    variants = {
        "etd": dict(rule="etd"),
        "nearest_car": dict(rule="nearest_car"),
        "round_robin": dict(rule="round_robin"),
        "etd + park lobby all day": dict(rule="etd", park_floor=1),
        "etd + park by time of day": dict(rule="etd", park_schedule=DAY_SCHEDULE),
    }
    out: dict[str, Any] = {
        "segments": [b[0] for b in bounds],
        "schedule": DAY_SCHEDULE,
        "variants": {},
    }
    for label, kw in variants.items():
        rule = kw.pop("rule")
        per_seg: dict[str, list[float]] = {b[0]: [] for b in bounds}
        whole: list[dict[str, float]] = []
        for seed in [*SEEDS, DAY.seed]:
            res = run(DAY, rule, seed=seed, **kw)
            whole.append(stats(res))
            for name, lo, hi in bounds:
                waits = [
                    p.wait
                    for p in res.passengers
                    if lo <= p.request_time < hi and p.wait is not None
                ]
                per_seg[name].append(statistics.fmean(waits) if waits else 0.0)
        out["variants"][label] = {
            "whole": agg(whole),
            "by_segment": {k: mean_sd(v) for k, v in per_seg.items()},
        }
    return out


# ---------------------------------------------------------------------------- charts


def charts(res: dict[str, Any]) -> list[str]:
    try:
        from elevator_sim.report import COLORS, INK, _plt
    except Exception:  # pragma: no cover
        return []
    try:
        plt = _plt()
    except RuntimeError:
        return []
    written = []
    CHARTS.mkdir(parents=True, exist_ok=True)

    # dwell sensitivity: ratio to ETD per pattern at dwell 0/1/2
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    names = list(res["dwell"])
    for ax, rule in zip(axes, ("nearest_car", "round_robin"), strict=True):
        width = 0.26
        for i, d in enumerate(("0", "1", "2")):
            vals = [
                res["dwell"][n][d][rule]["wait_avg"] / res["dwell"][n][d]["etd"]["wait_avg"]
                for n in names
            ]
            xs = [x + (i - 1) * (width + 0.02) for x in range(len(names))]
            ax.bar(
                xs, vals, width=width, color=COLORS[rule], alpha=0.45 + 0.27 * i, label=f"dwell {d}"
            )
        ax.axhline(1, color=INK, linewidth=0.8)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels([n.replace("_", "\n") for n in names], fontsize=7.5)
        ax.set_title(
            f"{rule} average wait / ETD's, by stop cost", loc="left", color=INK, fontsize=11
        )
        ax.legend(frameon=False, fontsize=9)
        ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "dwell_sensitivity.png")
    plt.close(fig)
    written.append("dwell_sensitivity.png")

    # load curve
    names = list(res["load"])
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.4))
    for ax, name in zip(axes.flat, names, strict=False):
        for rule in RULES:
            ys = [res["load"][name][str(s)][rule]["wait_avg"]["mean"] for s in RATES]
            es = [res["load"][name][str(s)][rule]["wait_avg"]["sd"] for s in RATES]
            ax.errorbar(
                RATES,
                ys,
                yerr=es,
                color=COLORS[rule],
                marker="o",
                markersize=3,
                capsize=2,
                label=rule,
            )
        ax.set_title(name.replace("_", " "), loc="left", color=INK, fontsize=10)
        ax.set_xlabel("arrival rate x committed rate", fontsize=8)
        ax.set_ylabel("average wait (ticks)", fontsize=8)
    for ax in list(axes.flat)[len(names) :]:
        ax.axis("off")
    axes.flat[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS / "load_curve.png")
    plt.close(fig)
    written.append("load_curve.png")

    # car sweep
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    for ax, (name, cars) in zip(axes, CAR_RANGE.items(), strict=True):
        for rule in RULES:
            ys = [
                100 * res["cars"][name]["by_cars"][str(n)][rule]["over_share"]["mean"] for n in cars
            ]
            ax.plot(list(cars), ys, color=COLORS[rule], marker="o", markersize=3, label=rule)
        ax.axhline(100 * SERVICE_TARGET, color=INK, linewidth=0.8, linestyle="--")
        ax.set_title(
            f"{name.replace('_', ' ')}: share waiting > {LONG_WAIT_TICKS} ticks",
            loc="left",
            color=INK,
            fontsize=11,
        )
        ax.set_xlabel("cars")
        ax.set_ylabel("% of passengers")
        ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(CHARTS / "cars_sweep.png")
    plt.close(fig)
    written.append("cars_sweep.png")

    # resilience backlog
    fig, ax = plt.subplots(figsize=(10, 4))
    for rule in RULES:
        s = res["resilience"]["series"][rule]
        ax.plot(s["spike"], color=COLORS[rule], label=f"{rule} (with spike)")
        ax.plot(s["base"], color=COLORS[rule], alpha=0.35, linewidth=0.8)
    ax.axvline(SPIKE["tick"], color=INK, linewidth=0.8, linestyle="--")
    ax.set_xlabel("tick")
    ax.set_ylabel("people waiting")
    title = (
        f"Morning up-peak with {SPIKE['people']} people arriving at floor {SPIKE['floor']} "
        f"at tick {SPIKE['tick']} (faint: without the spike)"
    )
    ax.set_title(title, loc="left", color=INK, fontsize=10)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(CHARTS / "resilience_backlog.png")
    plt.close(fig)
    written.append("resilience_backlog.png")

    # day by segment
    fig, ax = plt.subplots(figsize=(10, 4.2))
    segs = res["day"]["segments"]
    labels = list(res["day"]["variants"])
    width = 0.8 / len(labels)
    palette = {
        "etd": COLORS["etd"],
        "nearest_car": COLORS["nearest_car"],
        "round_robin": COLORS["round_robin"],
        "etd + park lobby all day": "#8fb3e8",
        "etd + park by time of day": "#1f3f80",
    }
    for i, lab in enumerate(labels):
        ys = [res["day"]["variants"][lab]["by_segment"][s]["mean"] for s in segs]
        xs = [x + (i - (len(labels) - 1) / 2) * width for x in range(len(segs))]
        ax.bar(xs, ys, width=width * 0.95, color=palette[lab], label=lab, linewidth=0)
    ax.set_xticks(range(len(segs)))
    ax.set_xticklabels(segs)
    ax.set_ylabel("average wait (ticks)")
    ax.set_title("Office day: average wait by time of day", loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "wait_by_time_of_day.png")
    plt.close(fig)
    written.append("wait_by_time_of_day.png")
    return written


# ---------------------------------------------------------------------------- report


def f1(ms: dict[str, float]) -> str:
    return f"{ms['mean']:.1f} ± {ms['sd']:.1f}"


def render(res: dict[str, Any]) -> str:
    lines = [
        "# Sensitivity studies",
        "",
        f'Seeds {SEEDS[0]}-{SEEDS[-1]} where a study says "across seeds" (mean ± sd); '
        "the committed seed otherwise. Ticks throughout; the service level counts passengers "
        f"waiting more than {LONG_WAIT_TICKS} ticks. "
        "Regenerate with `uv run python scenarios/studies.py`.",
        "",
        "## Stop cost (dwell 0, 1, 2) — committed seeds",
        "",
        "Average wait; in brackets, the rule's wait divided by ETD's at the same dwell.",
        "",
        "| pattern | dwell | etd | nearest_car | round_robin |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, by_d in res["dwell"].items():
        for d, rules in by_d.items():
            e = rules["etd"]["wait_avg"]
            nc, rr = rules["nearest_car"]["wait_avg"], rules["round_robin"]["wait_avg"]
            lines.append(
                f"| {name} | {d} | {e:.1f} | {nc:.1f} ({nc / e:.2f}x) | {rr:.1f} ({rr / e:.2f}x) |"
            )
    lines += [
        "",
        "## Load — arrival rate scaled, across seeds",
        "",
        "Average wait (share waiting > 30 ticks).",
        "",
    ]
    lines += ["| pattern | rate x | etd | nearest_car | round_robin |", "|---|---:|---:|---:|---:|"]
    for name, by_r in res["load"].items():
        for scale, rules in by_r.items():
            cells = [
                f"{f1(rules[r]['wait_avg'])} ({100 * rules[r]['over_share']['mean']:.0f}%)"
                for r in RULES
            ]
            lines.append(f"| {name} | {scale} | " + " | ".join(cells) + " |")
    lines += ["", "## Cars — how many to keep long waits under 10%, across seeds", ""]
    for name, d in res["cars"].items():
        lines += [
            f"**{name}** — cars needed so that at most 10% wait more than {LONG_WAIT_TICKS} ticks: "
            + ", ".join(
                f"{r} {d['cars_needed'][r] or '> ' + str(max(CAR_RANGE[name]))}" for r in RULES
            )
            + ".",
            "",
        ]
        lines += ["| cars | etd | nearest_car | round_robin |", "|---:|---:|---:|---:|"]
        for n, rules in d["by_cars"].items():
            cells = [
                f"{f1(rules[r]['wait_avg'])} ({100 * rules[r]['over_share']['mean']:.0f}%)"
                for r in RULES
            ]
            lines.append(f"| {n} | " + " | ".join(cells) + " |")
        lines.append("")
    sp = res["resilience"]["spike"]
    lines += [
        f"## Resilience — {sp['people']} people at floor {sp['floor']} at tick {sp['tick']} "
        "on the morning up-peak, across seeds",
        "",
        "| rule | peak backlog | ticks to recover | avg wait of the burst |",
        "|---|---:|---:|---:|",
    ]
    for r in RULES:
        s = res["resilience"]["seeds"][r]
        cells = [f1(s["peak_backlog"]), f1(s["recovery_ticks"]), f1(s["spike_wait_avg"])]
        lines.append(f"| {r} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Office day — average wait by time of day, across seeds",
        "",
        'Schedule for "park by time of day": '
        + ", ".join(f"tick {t} → floor {f}" for t, f in DAY_SCHEDULE)
        + ".",
        "",
    ]
    segs = res["day"]["segments"]
    lines += [
        "| variant | whole day | " + " | ".join(segs) + " | floors/pax |",
        "|---|---:|" + "---:|" * len(segs) + "---:|",
    ]
    for lab, d in res["day"]["variants"].items():
        lines.append(
            f"| {lab} | {f1(d['whole']['wait_avg'])} | "
            + " | ".join(f1(d["by_segment"][s]) for s in segs)
            + f" | {d['whole']['floors_per_passenger']['mean']:.1f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    res = {
        "dwell": study_dwell(),
        "load": study_load(),
        "cars": study_cars(),
        "resilience": study_resilience(),
        "day": study_day(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    slim = json.loads(json.dumps(res))
    for r in slim["resilience"]["series"].values():  # keep the json readable
        r["base"] = r["base"][:400]
        r["spike"] = r["spike"][:400]
    (OUT / "studies.json").write_text(json.dumps(slim, indent=1) + "\n")
    (OUT / "studies.md").write_text(render(res))
    print(render(res))
    for name in charts(res):
        print("wrote", CHARTS / name)


if __name__ == "__main__":
    main()
