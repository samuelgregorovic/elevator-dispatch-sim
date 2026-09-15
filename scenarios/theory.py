"""Checks of the simulation against elevator-traffic theory and exact identities.

Four checks, each answering "does the engine produce what the textbook says it should?"::

    identities   Little's law and conservation, exactly, on every committed run
    rtt          single-car up-peak round-trip time against the classical formula
                 (Barney & Al-Sharif: expected stops S and highest reversal floor H)
    capacity     five-minute handling capacity from that formula against each
                 scenario's demand, predicting which runs saturate
    literature   the measured ETD margins against published destination-dispatch claims

    uv run python scenarios/theory.py            # writes docs/results/theory.{md,json}

Deterministic: fixed seeds, deterministic engine, byte-identical output.
"""

from __future__ import annotations

import json
import random
import statistics
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from elevator_sim.compare import Variant, load_manifest  # noqa: E402
from elevator_sim.config import SimulationConfig  # noqa: E402
from elevator_sim.io import read_requests  # noqa: E402
from elevator_sim.metrics import car_usage, summarize  # noqa: E402
from elevator_sim.model import Request  # noqa: E402
from elevator_sim.schedulers import make_scheduler  # noqa: E402
from elevator_sim.simulation import Simulation, SimulationResult  # noqa: E402
from elevator_sim.validate import tick_bound  # noqa: E402
from generate import SCENARIOS, WINDOW_TICKS, Traffic, generate  # noqa: E402

OUT = HERE.parent / "docs" / "results"
SEEDS = list(range(201, 221))
RTT_CASES = [(10, 4), (10, 8), (20, 8), (20, 10), (50, 8), (50, 10)]  # (floors, capacity)
RTT_PASSENGERS = 240


# ------------------------------------------------------------------ theory (Barney & Al-Sharif)


def expected_stops(n_above: int, p: int) -> float:
    """Expected number of stops above the lobby for P passengers with uniform destinations."""
    return n_above * (1 - (1 - 1 / n_above) ** p)


def expected_highest(n_above: int, p: int) -> float:
    """Expected highest reversal floor (floors above the lobby) for P uniform passengers."""
    return n_above - sum((i / n_above) ** p for i in range(1, n_above))


def rtt_formula(floors: int, p: int, dwell: int) -> float:
    """Round-trip time in ticks: 2H floors of travel, S stops above plus one at the lobby."""
    n_above = floors - 1
    return 2 * expected_highest(n_above, p) + (expected_stops(n_above, p) + 1) * dwell


# ------------------------------------------------------------------ helpers


def backlog(result: SimulationResult) -> list[int]:
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


def run_traffic(t: Traffic, rule: str, seed: int | None = None) -> SimulationResult:
    tt = replace(t, seed=seed) if seed is not None else t
    requests = [Request(*row) for row in generate(tt)]
    config = SimulationConfig(elevators=t.elevators, floors=t.floors, capacity=t.capacity)
    return Simulation(config, make_scheduler(rule), requests).run(
        max_ticks=tick_bound(requests, config)
    )


# ------------------------------------------------------------------ check 1: identities


def check_identities() -> dict[str, Any]:
    """Exact identities that must hold on every committed scenario x scheduler run.

    Little's law in its exact finite form: the sum of individual waits equals the integral
    of the queue length over time, i.e. sum(wait_i) == sum_t backlog(t). Conservation:
    every passenger is carried by exactly one car; floors travelled per car equals the sum
    of its per-tick moves in the positions log; the load in the per-tick log equals boardings
    minus alightings from the event list, and every boarding or alighting happens at the
    floor the positions log says the car is on.
    """
    scenarios = load_manifest(HERE / "manifest.json")
    variants = [Variant(s) for s in ("etd", "nearest_car", "nearest_car_balanced", "round_robin")]
    rows = []
    for s in scenarios:
        config = s.config()
        requests = read_requests(s.file, config.floors)
        for v in variants:
            res = Simulation(
                config, make_scheduler(v.scheduler, fairness=v.fairness), requests
            ).run(max_ticks=tick_bound(requests, config))
            waits = sum(p.wait for p in res.passengers)
            queue_integral = sum(backlog(res))
            cars = car_usage(res)
            moves = [
                sum(
                    abs(a[i] - b[i]) for a, b in zip(res.positions, res.positions[1:], strict=False)
                )
                for i in range(len(res.cars))
            ]
            # Load in the per-tick log must equal boardings minus alightings up to that tick.
            load_ok = True
            aboard = [0] * len(res.cars)
            by_tick: dict[int, list[dict[str, Any]]] = {}
            for e in res.events:
                if e["type"] in ("board", "alight"):
                    by_tick.setdefault(e["t"], []).append(e)
            for t, states in enumerate(res.car_states):
                for e in by_tick.get(t, ()):
                    aboard[e["car"]] += 1 if e["type"] == "board" else -1
                    if res.positions[t][e["car"]] != e["floor"]:
                        load_ok = False
                if [st["load"] for st in states] != aboard:
                    load_ok = False
            rows.append(
                {
                    "scenario": s.name,
                    "scheduler": v.label,
                    "passengers": len(res.passengers),
                    "little_ok": waits == queue_integral,
                    "carried_ok": sum(c.carried for c in cars) == len(res.passengers),
                    "moves_ok": [c.floors_travelled for c in cars] == moves,
                    "load_ok": load_ok,
                }
            )
    return {
        "runs": len(rows),
        "all_ok": all(all(r[k] for k in r if k.endswith("_ok")) for r in rows),
        "rows": rows,
    }


# ------------------------------------------------------------------ check 2: round-trip time


def check_rtt() -> dict[str, Any]:
    """One car parked at the lobby, everyone waiting at the lobby at tick 0 with uniform
    destinations, capacity P: the car makes ceil(n/P) full trips. The measured mean
    round-trip time should match Barney's 2H + (S + 1) * dwell.
    """
    out = []
    for floors, cap in RTT_CASES:
        measured = []
        for seed in SEEDS:
            rng = random.Random(seed)
            reqs = [
                Request(0, f"p{i:04d}", 1, rng.randint(2, floors)) for i in range(RTT_PASSENGERS)
            ]
            config = SimulationConfig(elevators=1, floors=floors, capacity=cap, park_floor=1)
            res = Simulation(config, make_scheduler("etd"), reqs).run(
                max_ticks=tick_bound(reqs, config)
            )
            trips = -(-RTT_PASSENGERS // cap)
            # The run ends the tick the car is back at the lobby after the last trip and
            # has finished dwelling; ticks / trips is the mean round trip.
            measured.append((res.ticks - 1) / trips)
        formula = rtt_formula(floors, cap, dwell=1)
        m, sd = statistics.fmean(measured), statistics.stdev(measured)
        out.append(
            {
                "floors": floors,
                "capacity": cap,
                "formula_rtt": formula,
                "measured_rtt": m,
                "measured_sd": sd,
                "error_pct": 100 * (m - formula) / formula,
                "S": expected_stops(floors - 1, cap),
                "H": expected_highest(floors - 1, cap),
            }
        )
    return {"seeds": len(SEEDS), "passengers": RTT_PASSENGERS, "cases": out}


# ------------------------------------------------------------------ check 3: handling capacity


def check_capacity() -> dict[str, Any]:
    """Five-minute handling capacity of each scenario's bank from the RTT formula, against
    the scenario's demand: demand above capacity predicts a saturated run (backlog that
    grows through the window and a large share of long waits); below it, a stable one.
    Measured on the committed seed with ETD.
    """
    out = []
    for t in SCENARIOS:
        if t.segments:
            continue
        rtt = rtt_formula(t.floors, t.capacity, dwell=1)
        interval = rtt / t.elevators
        hc = WINDOW_TICKS / interval * t.capacity  # passengers per window, full cars
        demand = t.population * t.rate  # arrivals per window
        # lobby-origin share of the traffic is what the up-peak formula sizes for
        lobby_share = t.mix[0] + t.mix[1]
        res = run_traffic(t, "etd")
        s = summarize(res)
        bl = backlog(res)
        window_end = min(len(bl) - 1, t.windows * WINDOW_TICKS - 1)
        out.append(
            {
                "pattern": t.name,
                "cars": t.elevators,
                "capacity": t.capacity,
                "rtt": rtt,
                "interval": interval,
                "handling_capacity": hc,
                "demand": demand,
                "lobby_demand": demand * lobby_share,
                "utilisation": demand * lobby_share / hc,
                "predicted_saturated": demand * lobby_share > hc,
                "backlog_end_of_window": bl[window_end],
                "backlog_peak": max(bl),
                "over_30_share": s.service.over_share,
                "busy_mean": s.balance.busy_mean,
            }
        )
    return {"rows": out}


# ------------------------------------------------------------------ check 4: literature


def check_literature() -> dict[str, Any]:
    """Measured improvements of ETD over nearest car in time to destination, per pattern,
    across seeds, next to the published claims for destination dispatch over conventional
    control (about 25% shorter trip times; gains concentrated in peak periods).
    """
    out = []
    for t in SCENARIOS:
        if t.segments:
            continue
        gains = []
        for seed in SEEDS[:10]:
            a = summarize(run_traffic(t, "etd", seed)).total.mean
            b = summarize(run_traffic(t, "nearest_car", seed)).total.mean
            gains.append(100 * (1 - a / b))
        out.append(
            {
                "pattern": t.name,
                "rate": t.rate,
                "ttd_gain_pct_mean": statistics.fmean(gains),
                "ttd_gain_pct_sd": statistics.stdev(gains),
            }
        )
    return {"seeds": 10, "rows": out}


# ------------------------------------------------------------------ render


def render(r: dict[str, Any]) -> str:
    lines = [
        "# Checks against theory",
        "",
        "Does the engine produce what elevator-traffic theory says it should? Four checks; "
        "regenerate with `uv run python scenarios/theory.py`.",
        "",
        "## 1. Exact identities on every committed run",
        "",
        "Little's law in its finite form — the sum of every passenger's wait equals the sum over "
        "ticks of the number of people waiting — plus conservation: every passenger carried by "
        "exactly one car, floors travelled equal to the moves in the positions log, the load in "
        "the per-tick log equal to boardings minus alightings in the event list, and every "
        "boarding "
        "or alighting at the floor the positions log puts the car on.",
        "",
        f"{r['identities']['runs']} runs (every manifest scenario x four rules): "
        + (
            "**all identities hold exactly.**"
            if r["identities"]["all_ok"]
            else "**FAILURES — see json.**"
        ),
        "",
        "## 2. Up-peak round-trip time against the classical formula",
        "",
        "One car parked at the lobby, everyone at the lobby at tick 0 with uniformly random "
        "destinations, capacity P. Barney & Al-Sharif give the expected number of stops "
        "S = N·(1 - (1 - 1/N)^P) and the expected highest reversal floor "
        "H = N - Σ(i/N)^P over N floors above the lobby; with one tick per floor and one tick "
        "per stop the round trip is 2H + S + 1. Measured: ticks per trip over "
        f"{r['rtt']['passengers']} passengers, {r['rtt']['seeds']} seeds.",
        "",
        "| floors | P | S (formula) | H (formula) | RTT formula | RTT measured | error |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for c in r["rtt"]["cases"]:
        lines.append(
            f"| {c['floors']} | {c['capacity']} | {c['S']:.2f} | {c['H']:.2f} | "
            f"{c['formula_rtt']:.1f} | {c['measured_rtt']:.1f} ± {c['measured_sd']:.1f} | "
            f"{c['error_pct']:+.1f}% |"
        )
    lines += [
        "",
        "## 3. Handling capacity against demand",
        "",
        "The same formula gives each bank's five-minute handling capacity "
        "(window / interval x car capacity, interval = RTT / cars). Where lobby-bound demand "
        "exceeds it the run must saturate — a backlog still standing at the end of the arrival "
        "window and a large share of long waits — and where it does not, the run must be stable. "
        "Committed seed, ETD.",
        "",
        "| pattern | cars x P | RTT | interval | capacity / window | lobby demand / window | "
        "utilisation | predicted | backlog at window end | peak backlog | waits > 30 |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for c in r["capacity"]["rows"]:
        lines.append(
            f"| {c['pattern']} | {c['cars']} x {c['capacity']} | {c['rtt']:.0f} | "
            f"{c['interval']:.1f} | {c['handling_capacity']:.0f} | {c['lobby_demand']:.0f} | "
            f"{100 * c['utilisation']:.0f}% | "
            f"{'saturated' if c['predicted_saturated'] else 'stable'} | "
            f"{c['backlog_end_of_window']} | {c['backlog_peak']} | "
            f"{100 * c['over_30_share']:.0f}% |"
        )
    lines += [
        "",
        "## 4. Measured margins against published claims",
        "",
        "Published figures for destination dispatch over conventional control: trip times about "
        "25% shorter, handling capacity about 30% higher, with the gains concentrated in peak "
        "periods (RESEARCH.md §1). Measured here: ETD's reduction in mean time to destination "
        "against nearest car, ten fresh seeds per pattern.",
        "",
        "| pattern | arrival rate | time-to-destination gain |",
        "|---|---:|---:|",
    ]
    for c in r["literature"]["rows"]:
        lines.append(
            f"| {c['pattern']} | {100 * c['rate']:.0f}% / window | "
            f"{c['ttd_gain_pct_mean']:.0f}% ± {c['ttd_gain_pct_sd']:.0f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    r = {
        "identities": check_identities(),
        "rtt": check_rtt(),
        "capacity": check_capacity(),
        "literature": check_literature(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "theory.json").write_text(json.dumps(r, indent=2) + "\n")
    (OUT / "theory.md").write_text(render(r))
    print(render(r))


if __name__ == "__main__":
    main()
