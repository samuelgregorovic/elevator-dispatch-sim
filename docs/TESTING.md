# Testing approach

`uv run pytest` — 192 tests, about twenty seconds, no network, no fixtures beyond the committed scenario files. CI runs the suite with `ruff` on Python 3.11 and 3.12, with Node installed for the conformance matrix — on push, so commits pushed in a batch are checked only at the batch's head; the pre-commit hook in `.githooks/` runs the same three commands locally on every commit.

The suite is organised by what kind of mistake it would catch, not by module.

## 1. Unit tests: the rules of the model

`test_tick_semantics.py`, `test_capacity_and_direction.py`, `test_validation.py`, `test_car_usage.py`

Each assumption in `ASSUMPTIONS.md` that has an observable consequence has a test that pins it: the idle-car-on-the-floor case gives wait 0 and the one-floor-away case gives wait 1 (A3); dwell adds exactly one tick per stop and `dwell_ticks = 0` reproduces the literal brief (A2); tick 0 logs the initial positions and the simulation ticks through idle gaps instead of jumping (A5); capacity is never exceeded and a passenger left behind boards the same car on a later pass (A8, A11); a car going up does not pick up a down passenger it passes (A12); an idle car adopts the direction of the longest-waiting passenger at its floor; an express car is only ever assigned feasible passengers, an infeasible request is rejected before the run starts, and a park floor must lie inside every express zone (A10); a stop is one dwell per floor visit and passengers arriving mid-dwell do not extend it (A2); an idle car reports an idle direction; `percentile` is nearest-rank; a car is busy from assignment until its last passenger alights, an idle car counts as unused, round robin's carried counts are equal by construction, and the balance figures are in the summary (A20); every invalid-input case in A15 is rejected with a message that names the row and the reason, and a UTF-8 BOM is tolerated.

These tests are deliberately tiny — one to four requests, one or two cars — so that when one fails the reason is obvious.

## 2. Structural test: no peek-ahead

`test_no_peek_ahead.py`

A spy *scheduler* records the clock value at which it sees each request. The test asserts that every request is seen exactly at its own `time`, never earlier, on an input that is deliberately out of order. The `RequestFeed` is also tested directly for its release rule, and the scheduler protocol's signature is asserted to carry only `(request, cars, now)` — there is no parameter through which a feed could reach a scheduler. This is the brief's hardest constraint to trust by inspection, so it is tested rather than promised.

## 3. Property-based invariants

`test_invariants.py` (Hypothesis)

For random buildings (2–24 floors, 1–6 cars, capacity 1–6, dwell 0–2, any start floor, optionally one express car and a park floor) and random request sets (0–40 requests over 30 ticks), for every scheduler:

- every passenger is delivered, `request ≤ board < alight`, and boarding happens only at the origin and alighting only at the destination;
- every car stays within the building and moves at most one floor per tick;
- load never exceeds capacity;
- two runs on the same input produce identical positions and events;
- the positions log has one row per tick from 0 and one column per car.

These are the properties the brief's three objectives translate into. The delivery invariant is the one that earned its keep: it found a LOOK livelock (two waiting passengers on adjacent floors wanting opposite directions) within the first few hundred examples, which no hand-written case had covered. The fix is documented in A12.

## 4. Regression tests: golden statistics

`test_scenarios_golden.py`, `test_results_golden.py`, `test_policies.py`

The sample from the brief is run with each scheduler and its tick count, wait and total statistics are pinned. Every row of the committed comparison table (`docs/results/comparison.json`, 50 scenario × variant rows) is regenerated and compared field by field — passengers, ticks, wait and total distributions, per-car usage, balance — so that a behaviour change cannot orphan a figure quoted in the README, the design notes, the whitepaper or the deck without failing the suite. Three empirical findings are pinned as inequalities (parking reduces up-peak wait; the fairness weight lowers the maximum wait under the capacity burst; the zoned scenario is fully served); only findings that also held across fresh seeds (`docs/results/robustness.md`) are pinned this way — an earlier test pinned the fairness effect on the tall lobby traffic, which the seed study showed was a coincidence of the committed seed.

## 5. Scenario and tooling tests

`test_scenarios_and_compare.py`

The scenario generator is re-run inside the test and its output compared byte for byte with the committed CSV files, so the data in the README cannot drift from the generator. The `compare` and `run` CLIs are exercised end to end, and `report` is smoke-tested when `matplotlib` is installed (skipped otherwise, so the stdlib-only install still passes).

## 6. Conformance: the browser engine equals the Python engine

`test_js_conformance.py`

The interactive simulator on GitHub Pages runs a JavaScript port of the engine (`docs/viewer/engine.js`). Two implementations of the same rules will drift unless something stops them, so the suite runs the port with Node (`docs/viewer/conform.mjs`) on every committed scenario with every scheduler variant — 50 combinations — and asserts that positions per tick, the full event list, every passenger's assignment, boarding and alighting ticks, and every car's carried, stops, floors and busy ticks are identical to Python's. Skipped when Node is absent; CI installs it.

## What is not tested, and why

- Rendering details of the charts and the simulator page beyond "produces a file" / "loads without console errors" (the page was exercised in a headless browser: floor click, live traffic, CSV upload, phone width). The engine underneath is covered by the conformance matrix. Pixel tests would cost more than they catch here.
- Performance. The full comparison runs in a few seconds; there is no requirement that would justify a benchmark.
- The projection horizon bound in `etd.py` is generous by construction rather than proven tight; the invariant tests cover the outcome (every passenger delivered, deterministic), not the bound itself.

## Adversarial testing

Beyond the suite, the engine was fuzzed with 400 random buildings (1–10 cars, 2–60 floors, capacity 1–12, random express zones, park and start floors), reconstructing load from events and checking delivery, movement, capacity, boarding at origin and alighting at destination; no invariant broke, and the Hypothesis strategy was widened to the same ranges afterwards. Malformed and edge-case inputs — missing fields, a BOM, CRLF, blank lines, float times, a header-only file, a last-tick request, a single pair, adversarial oscillation and streaming cases — produced two fixes, both now covered by tests. The browser page's comparison figures were cross-checked against `comparison.md`, which found and fixed a double-rounding of the published means.
