"""Static charts for the README. Requires the optional ``viz`` extra (matplotlib)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .compare import Variant, load_manifest, run_matrix

# Fixed colour per scheduler (categorical slots 1-3 of the reference palette).
COLORS = {"etd": "#2a78d6", "nearest_car": "#eb6834", "round_robin": "#1baf7a"}
ORDER = ["etd", "nearest_car", "round_robin"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"


def _plt():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "charts need matplotlib: install with `uv sync --group dev --extra viz`"
        ) from exc
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 10,
            "axes.edgecolor": GRID,
            "axes.labelcolor": MUTED,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
            "figure.facecolor": "white",
            "savefig.dpi": 160,
        }
    )
    return plt


def chart_wait_by_scenario(rows: list[dict[str, Any]], out: Path) -> Path:
    """Two panels (mean, p90) of waiting time per scenario, one bar per scheduler."""
    plt = _plt()
    scenarios = [s for s in dict.fromkeys(r["scenario"] for r in rows) if s != "sample"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.6), sharey=False)
    for ax, stat, title in zip(axes, ("mean", "p90"), ("Average wait", "p90 wait"), strict=True):
        width = 0.26
        for i, sched in enumerate(ORDER):
            vals = [
                next(
                    r["wait"][stat] for r in rows if r["scenario"] == s and r["scheduler"] == sched
                )
                for s in scenarios
            ]
            xs = [x + (i - 1) * (width + 0.02) for x in range(len(scenarios))]
            ax.bar(xs, vals, width=width, color=COLORS[sched], label=sched, linewidth=0)
        ax.set_xticks(range(len(scenarios)))
        ax.set_xticklabels([s.replace("_", "\n") for s in scenarios], fontsize=7.5)
        ax.set_title(f"{title} (ticks)", loc="left", color=INK, fontsize=11)
        ax.grid(axis="x", visible=False)
    axes[0].legend(frameon=False, fontsize=9)
    fig.tight_layout()
    path = out / "wait_by_scenario.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_wait_distribution(traces: dict[str, dict[str, Any]], scenario: str, out: Path) -> Path:
    """Histogram of waiting times for one scenario, one small multiple per scheduler."""
    plt = _plt()
    fig, axes = plt.subplots(len(ORDER), 1, figsize=(8, 5.4), sharex=True, sharey=True)
    waits = {
        s: [p["board"] - p["t"] for p in traces[f"{scenario}__{s}"]["passengers"]] for s in ORDER
    }
    hi = max(max(w) for w in waits.values())
    bins = range(0, hi + 5, max(1, hi // 30))
    for ax, sched in zip(axes, ORDER, strict=True):
        ax.hist(waits[sched], bins=bins, color=COLORS[sched], linewidth=0)
        mean = sum(waits[sched]) / len(waits[sched])
        ax.axvline(mean, color=INK, linewidth=1, linestyle="--")
        ax.text(
            mean + 0.5, ax.get_ylim()[1] * 0.85, f"{sched}  mean {mean:.1f}", color=INK, fontsize=9
        )
        ax.grid(axis="x", visible=False)
    axes[-1].set_xlabel("waiting time (ticks)")
    fig.suptitle(f"Waiting-time distribution — {scenario}", x=0.02, ha="left", color=INK)
    fig.tight_layout()
    path = out / f"wait_distribution_{scenario}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_positions(trace: dict[str, Any], scenario: str, out: Path, ticks: int = 160) -> Path:
    """Elevator floor over time for the first ``ticks`` ticks of one run."""
    plt = _plt()
    cars = trace["config"]["elevators"]
    palette = [
        "#2a78d6",
        "#eb6834",
        "#1baf7a",
        "#eda100",
        "#e87ba4",
        "#008300",
        "#4a3aa7",
        "#e34948",
    ]
    fig, ax = plt.subplots(figsize=(11, 3.8))
    for i in range(min(cars, len(palette))):
        ys = [t[i]["floor"] for t in trace["cars"][:ticks]]
        ax.plot(range(len(ys)), ys, color=palette[i], linewidth=1.6, label=f"elevator {i + 1}")
    ax.set_xlabel("tick")
    ax.set_ylabel("floor")
    ax.set_title(f"Elevator positions — {scenario}, {trace['scheduler']}", loc="left", color=INK)
    ax.legend(
        frameon=False,
        fontsize=8,
        ncol=min(cars, 6),
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
    )
    fig.tight_layout()
    path = out / f"positions_{scenario}_{trace['scheduler']}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_car_usage(rows: list[dict[str, Any]], scenario: str, out: Path) -> Path:
    """Busy share per car, one bar group per car, one bar per scheduler."""
    plt = _plt()
    sel = {r["scheduler"]: r for r in rows if r["scenario"] == scenario}
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    cars = sel[ORDER[0]]["cars"]
    width = 0.26
    for i, sched in enumerate(ORDER):
        vals = [100 * c["busy_share"] for c in sel[sched]["cars"]]
        xs = [x + (i - 1) * (width + 0.02) for x in range(len(cars))]
        ax.bar(xs, vals, width=width, color=COLORS[sched], label=sched, linewidth=0)
    ax.set_xticks(range(len(cars)))
    ax.set_xticklabels([f"car {c['car']}" for c in cars])
    ax.set_ylim(0, 100)
    ax.set_ylabel("busy (% of ticks with a passenger aboard or assigned)")
    ax.set_title(f"Car usage — {scenario}", loc="left", color=INK)
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    path = out / f"car_usage_{scenario}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_balance_by_scenario(rows: list[dict[str, Any]], out: Path) -> Path:
    """Two panels: mean busy share (car-time spent) and busy spread (unevenness) per scenario."""
    plt = _plt()
    scenarios = [s for s in dict.fromkeys(r["scenario"] for r in rows) if s != "sample"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.6))
    panels = (
        ("busy_mean", "Car-time used (mean busy share, %)"),
        ("busy_spread", "Unevenness (busiest minus least busy car, points)"),
    )
    for ax, (key, title) in zip(axes, panels, strict=True):
        width = 0.26
        for i, sched in enumerate(ORDER):
            vals = [
                100
                * next(
                    r["balance"][key]
                    for r in rows
                    if r["scenario"] == s and r["scheduler"] == sched
                )
                for s in scenarios
            ]
            xs = [x + (i - 1) * (width + 0.02) for x in range(len(scenarios))]
            ax.bar(xs, vals, width=width, color=COLORS[sched], label=sched, linewidth=0)
        ax.set_xticks(range(len(scenarios)))
        ax.set_xticklabels([s.replace("_", "\n") for s in scenarios], fontsize=7.5)
        ax.set_title(title, loc="left", color=INK, fontsize=11)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylim(0, 100)
    axes[0].legend(frameon=False, fontsize=9)
    fig.tight_layout()
    path = out / "car_balance_by_scenario.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_backlog(traces: dict[str, dict[str, Any]], scenario: str, out: Path) -> Path:
    """People waiting per tick, one line per scheduler, from the committed traces."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(10, 3.8))
    for sched in ORDER:
        tr = traces[f"{scenario}__{sched}"]
        delta = [0] * (tr["ticks"] + 1)
        for p in tr["passengers"]:
            delta[p["t"]] += 1
            if p["board"] is not None:
                delta[min(p["board"], tr["ticks"])] -= 1
        series, cur = [], 0
        for t in range(tr["ticks"]):
            cur += delta[t]
            series.append(cur)
        ax.plot(series, color=COLORS[sched], label=sched, linewidth=1.2)
    ax.set_xlabel("tick")
    ax.set_ylabel("people waiting")
    ax.set_title(f"Backlog over time — {scenario}", loc="left", color=INK)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    path = out / f"backlog_{scenario}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_wait_by_floor(traces: dict[str, dict[str, Any]], scenario: str, out: Path) -> Path:
    """Average wait by origin band (lobby, then ten-floor bands), one bar per scheduler."""
    plt = _plt()
    floors = traces[f"{scenario}__{ORDER[0]}"]["config"]["floors"]
    bands = [(1, 1), *[(lo, min(lo + 9, floors)) for lo in range(2, floors + 1, 10)]]
    labels = ["lobby"] + [f"{lo}-{hi}" for lo, hi in bands[1:]]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    width = 0.26
    for i, sched in enumerate(ORDER):
        tr = traces[f"{scenario}__{sched}"]
        vals = []
        for lo, hi in bands:
            w = [
                p["board"] - p["t"]
                for p in tr["passengers"]
                if p["board"] is not None and lo <= p["source"] <= hi
            ]
            vals.append(sum(w) / len(w) if w else 0.0)
        xs = [x + (i - 1) * (width + 0.02) for x in range(len(bands))]
        ax.bar(xs, vals, width=width, color=COLORS[sched], label=sched, linewidth=0)
    ax.set_xticks(range(len(bands)))
    ax.set_xticklabels(labels)
    ax.set_xlabel("origin floor")
    ax.set_ylabel("average wait (ticks)")
    ax.set_title(f"Who waits: average wait by origin floor — {scenario}", loc="left", color=INK)
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    path = out / f"wait_by_floor_{scenario}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_fairness_sweep(rows: list[dict[str, Any]], scenario: str, out: Path) -> Path | None:
    """Max wait vs average total time as the ETD fairness weight increases."""
    pts = [r for r in rows if r["scenario"] == scenario and r["scheduler"].startswith("etd")]
    if len(pts) < 2:
        return None
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    xs = [r["total"]["mean"] for r in pts]
    ys = [r["wait"]["max"] for r in pts]
    ax.scatter(xs, ys, color=COLORS["etd"], s=48, zorder=3)
    for r, x, y in zip(pts, xs, ys, strict=True):
        label = "0" if r["scheduler"] == "etd" else r["scheduler"].split("_f")[1]
        ax.annotate(
            f"w={label}", (x, y), textcoords="offset points", xytext=(6, 4), fontsize=9, color=INK
        )
    ax.set_xlabel("average total time (ticks) — efficiency")
    ax.set_ylabel("maximum wait (ticks) — fairness")
    ax.set_title(f"Fairness weight sweep — {scenario}", loc="left", color=INK)
    fig.tight_layout()
    path = out / f"fairness_sweep_{scenario}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def build_report(manifest: Path, out: Path, fairness: list[float], dwell: int = 1) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    scenarios = load_manifest(manifest)
    variants = [Variant(s) for s in ORDER] + [Variant("etd", fairness=w) for w in fairness]
    trace_dir = out / "_traces"
    rows = run_matrix(scenarios, variants, dwell_ticks=dwell, trace_dir=trace_dir)
    traces = {p.stem: json.loads(p.read_text()) for p in trace_dir.glob("*.json")}
    written = [chart_wait_by_scenario(rows, out)]
    for name in ("morning_up_peak", "tall_building"):
        if any(r["scenario"] == name for r in rows):
            written.append(chart_wait_distribution(traces, name, out))
    if "morning_up_peak__etd" in traces:
        written.append(chart_positions(traces["morning_up_peak__etd"], "morning_up_peak", out))
    written.append(chart_balance_by_scenario(rows, out))
    for name in ("morning_up_peak", "tall_lobby_traffic"):
        if any(r["scenario"] == name for r in rows):
            written.append(chart_car_usage(rows, name, out))
    for name in ("morning_up_peak", "tall_building"):
        if f"{name}__etd" in traces:
            written.append(chart_backlog(traces, name, out))
            written.append(chart_wait_by_floor(traces, name, out))
    for name in ("morning_up_peak", "tall_building"):
        p = chart_fairness_sweep(rows, name, out)
        if p:
            written.append(p)
    for p in trace_dir.glob("*.json"):
        p.unlink()
    trace_dir.rmdir()
    return written
