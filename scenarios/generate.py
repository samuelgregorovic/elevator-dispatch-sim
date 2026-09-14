"""Seeded generator for the benchmark scenarios in this directory.

Traffic mixes follow the office-building figures collected in docs/RESEARCH.md:
morning up-peak 85/10/5 (up from lobby / down to lobby / interfloor),
lunchtime two-way 45/45/10, evening down-peak dominated by trips to the lobby.
Arrival rates are expressed as a share of the building population per
five-minute window, and a window is mapped to ``WINDOW_TICKS`` ticks.

Re-running this script with the same seed reproduces the committed CSV files
byte for byte::

    uv run python scenarios/generate.py
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent
WINDOW_TICKS = 150  # one five-minute window; ~2 s per floor of travel
LOBBY = 1


@dataclass(frozen=True)
class Traffic:
    name: str
    floors: int
    elevators: int
    capacity: int
    population: int
    rate: float  # share of population arriving per window
    windows: int
    mix: tuple[float, float, float]  # up from lobby, down to lobby, interfloor
    seed: int
    description: str


SCENARIOS: list[Traffic] = [
    Traffic(
        "morning_up_peak",
        20,
        4,
        8,
        400,
        0.13,
        3,
        (0.85, 0.10, 0.05),
        1,
        "Office morning: 13% of population per window, almost all from the lobby.",
    ),
    Traffic(
        "lunch_two_way",
        20,
        4,
        8,
        400,
        0.12,
        3,
        (0.45, 0.45, 0.10),
        2,
        "Lunchtime: balanced up and down traffic, the hardest pattern for control.",
    ),
    Traffic(
        "evening_down_peak",
        20,
        4,
        8,
        400,
        0.14,
        2,
        (0.10, 0.85, 0.05),
        3,
        "End of day: high rate for a short time, nearly everyone heading to the lobby.",
    ),
    Traffic(
        "interfloor",
        20,
        4,
        8,
        400,
        0.06,
        3,
        (0.0, 0.0, 1.0),
        4,
        "Quiet interfloor traffic between upper floors, no lobby involvement.",
    ),
    Traffic(
        "capacity_stress",
        20,
        2,
        6,
        400,
        0.20,
        1,
        (1.0, 0.0, 0.0),
        5,
        "Two small cars, a burst of lobby arrivals: cars fill and passengers get left behind.",
    ),
    Traffic(
        "tall_building",
        51,
        6,
        10,
        900,
        0.12,
        2,
        (0.70, 0.15, 0.15),
        6,
        "The 51-floor building implied by the brief's sample, beyond a single bank's comfort.",
    ),
    Traffic(
        "tall_lobby_traffic",
        51,
        6,
        10,
        900,
        0.12,
        2,
        (0.80, 0.20, 0.0),
        7,
        "51 floors, lobby-only trips (no interfloor), so a zoned bank can serve every request.",
    ),
]


def generate(t: Traffic) -> list[tuple[int, str, int, int]]:
    rng = random.Random(t.seed)
    per_tick = t.population * t.rate / WINDOW_TICKS
    rows: list[tuple[int, str, int, int]] = []
    n = 0
    for tick in range(t.windows * WINDOW_TICKS):
        for _ in range(poisson(rng, per_tick)):
            n += 1
            source, dest = trip(rng, t)
            rows.append((tick, f"p{n:04d}", source, dest))
    return rows


def trip(rng: random.Random, t: Traffic) -> tuple[int, int]:
    up, down, _ = t.mix
    r = rng.random()
    upper = range(2, t.floors + 1)
    if r < up:
        return LOBBY, rng.choice(upper)
    if r < up + down:
        return rng.choice(upper), LOBBY
    source = rng.choice(upper)
    dest = rng.choice([f for f in upper if f != source])
    return source, dest


def poisson(rng: random.Random, lam: float) -> int:
    """Knuth's method; adequate for the small rates used here."""
    if lam <= 0:
        return 0
    limit, k, p = pow(2.718281828459045, -lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def write_all() -> None:
    manifest = []
    for t in SCENARIOS:
        path = HERE / f"{t.name}.csv"
        with path.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["time", "id", "source", "dest"])
            writer.writerows(generate(t))
        manifest.append(
            {
                "name": t.name,
                "file": path.name,
                "floors": t.floors,
                "elevators": t.elevators,
                "capacity": t.capacity,
                "description": t.description,
                "seed": t.seed,
            }
        )
    manifest += [
        {
            "name": "morning_up_peak_parked",
            "file": "morning_up_peak.csv",
            "floors": 20,
            "elevators": 4,
            "capacity": 8,
            "park_floor": 1,
            "description": "Same morning traffic; idle cars return to the lobby (park_floor=1).",
            "seed": 1,
        },
        {
            "name": "tall_lobby_zoned",
            "file": "tall_lobby_traffic.csv",
            "floors": 51,
            "elevators": 6,
            "capacity": 10,
            "express": {
                "1": "1-26",
                "2": "1-26",
                "3": "1-26",
                "4": "1,27-51",
                "5": "1,27-51",
                "6": "1,27-51",
            },
            "description": (
                "Same lobby-only traffic; three local cars (1-26) "
                "and three express cars (lobby + 27-51)."
            ),
            "seed": 7,
        },
    ]
    manifest.insert(
        0,
        {
            "name": "sample",
            "file": "sample.csv",
            "floors": 51,
            "elevators": 2,
            "capacity": 8,
            "description": "The three requests from the brief.",
            "seed": None,
        },
    )
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for m in manifest:
        with (HERE / m["file"]).open() as fh:
            rows = sum(1 for _ in fh) - 1
        print(f"{m['name']:18} {rows:5d} requests  floors={m['floors']} cars={m['elevators']}")


if __name__ == "__main__":
    write_all()
