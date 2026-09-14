# elevator-dispatch-sim

Discrete-time simulation of a destination-dispatch elevator system: configurable cars, floors and capacity; pluggable scheduling algorithms; a positions log and passenger statistics as required by the [brief](docs/brief.pdf); and a comparison of schedulers on realistic traffic patterns.


## How to run

Requires Python 3.11+. The simulation itself has no third-party dependencies.

```bash
git clone https://github.com/samuelgregorovic/elevator-dispatch-sim.git
cd elevator-dispatch-sim

# with uv (recommended: also installs the dev tools)
uv sync --group dev
uv run python -m elevator_sim run scenarios/sample.csv --elevators 2 --floors 51 --capacity 8

# or with plain Python, no install
PYTHONPATH=src python3 -m elevator_sim run scenarios/sample.csv --elevators 2
```

`run` writes `positions.csv` (one row per tick, one column per elevator), `trace.json` (per-tick car state and every request/assign/board/alight event) and `summary.json` into `outputs/run/` (change with `--out`), and prints the passenger statistics.

Options: `--scheduler {etd,nearest_car,round_robin}` (default `etd`), `--fairness W` (ETD age weight, default 0), `--dwell N` (ticks per stop, default 1; `0` is the literal brief), `--start-floor`, `--park-floor`, `--express CAR:FLOORS` (e.g. `--express 3:1,30-51` makes car 3 serve only the lobby and floors 30–51).

Tests and lint:

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Time spent

_(filled in at submission)_

## Assumptions, simplifications and trade-offs

See [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md) for every decision the brief left open, with reasons. Design and algorithm trade-offs are in [`docs/DESIGN.md`](docs/DESIGN.md).

## What I would improve with more time

_(filled in at submission)_

## Repository

- `src/elevator_sim/` — the package (stdlib only)
- `tests/` — unit, property-based and scenario tests
- `scenarios/` — input files and the seeded generator
- `docs/` — brief, assumptions, design, research, testing, charts, viewer
