# Testing approach

`uv run pytest` — 77 tests, about ten seconds, no network, no fixtures beyond the committed scenario files. CI runs the suite with `ruff` on Python 3.11 and 3.12.

The suite is organised by what kind of mistake it would catch, not by module.

## 1. Unit tests: the rules of the model

`test_tick_semantics.py`, `test_capacity_and_direction.py`, `test_validation.py`

Each assumption in `ASSUMPTIONS.md` that has an observable consequence has a test that pins it: the idle-car-on-the-floor case gives wait 0 and the one-floor-away case gives wait 1 (A3); dwell adds exactly one tick per stop and `dwell_ticks = 0` reproduces the literal brief (A2); tick 0 logs the initial positions and the simulation ticks through idle gaps instead of jumping (A5); capacity is never exceeded and a passenger left behind boards the same car on a later pass (A8, A11); a car going up does not pick up a down passenger it passes (A12); an idle car adopts the direction of the longest-waiting passenger at its floor; an express car is only ever assigned feasible passengers (A10); every invalid-input case in A15 is rejected with a message that names the row and the reason.

These tests are deliberately tiny — one to four requests, one or two cars — so that when one fails the reason is obvious.

## 2. Structural test: no peek-ahead

`test_no_peek_ahead.py`

A spy scheduler records the clock value at which it sees each request. The test asserts that every request is seen exactly at its own `time`, never earlier, on an input that is deliberately out of order. The `RequestFeed` is also tested directly. This is the brief's hardest constraint to trust by inspection, so it is tested rather than promised.

## 3. Property-based invariants

`test_invariants.py` (Hypothesis)

For random buildings (2–12 floors, 1–4 cars, capacity 1–6, dwell 0–2) and random request sets (0–25 requests over 30 ticks), for every scheduler:

- every passenger is delivered, and `request ≤ board < alight`;
- every car stays within the building and moves at most one floor per tick;
- load never exceeds capacity;
- two runs on the same input produce identical positions and events;
- the positions log has one row per tick from 0 and one column per car.

These are the properties the brief's three objectives translate into. The delivery invariant is the one that earned its keep: it found a LOOK livelock (two waiting passengers on adjacent floors wanting opposite directions) within the first few hundred examples, which no hand-written case had covered. The fix is documented in A12.

## 4. Regression tests: golden statistics

`test_scenarios_golden.py`, `test_policies.py`

The sample from the brief is run with each scheduler and its tick count, wait and total statistics are pinned. Three empirical findings from the committed scenarios are pinned as inequalities (parking reduces up-peak wait; the fairness weight lowers the tall-building maximum wait; the zoned scenario is fully served). Any change in behaviour — intended or not — changes these numbers and has to be acknowledged by updating the test.

## 5. Scenario and tooling tests

`test_scenarios_and_compare.py`

The scenario generator is re-run inside the test and its output compared byte for byte with the committed CSV files, so the data in the README cannot drift from the generator. The `compare` and `run` CLIs are exercised end to end, and `report` is smoke-tested when `matplotlib` is installed (skipped otherwise, so the stdlib-only install still passes).

## What is not tested, and why

- Rendering details of the charts and the viewer beyond "produces a file" / "loads without console errors" (the viewer was checked manually in a headless browser). Pixel tests would cost more than they catch here.
- Performance. The full comparison runs in about a second; there is no requirement that would justify a benchmark.
- The projection horizon bound in `etd.py` is generous by construction rather than proven tight; the invariant tests cover the outcome (every passenger delivered, deterministic), not the bound itself.
