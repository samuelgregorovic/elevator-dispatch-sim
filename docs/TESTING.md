# Testing approach

`uv run pytest` — 228 tests, about twenty seconds, no network, no fixtures beyond the committed scenario files. CI runs the suite with `ruff` on Python 3.11 and 3.12, with Node installed for the conformance matrix — on push, so commits pushed in a batch are checked only at the batch's head; the pre-commit hook in `.githooks/` runs the same three commands locally on every commit.

The suite is organised by what kind of mistake it would catch, not by module.

## 1. Unit tests: the rules of the model

`test_tick_semantics.py`, `test_capacity_and_direction.py`, `test_validation.py`, `test_car_usage.py`

Each assumption in `ASSUMPTIONS.md` that has an observable consequence has a test that pins it: the idle-car-on-the-floor case gives wait 0 and the one-floor-away case gives wait 1 (A3); dwell adds exactly one tick per stop and `dwell_ticks = 0` reproduces the literal brief (A2); tick 0 logs the initial positions and the simulation ticks through idle gaps instead of jumping (A5); capacity is never exceeded and a passenger left behind boards the same car on a later pass (A8, A11); a car going up does not pick up a down passenger it passes (A12); an idle car adopts the direction of the longest-waiting passenger at its floor; an express car is only ever assigned feasible passengers, an infeasible request is rejected before the run starts, and a park floor must lie inside every express zone (A10); a stop is one dwell per floor visit and passengers arriving mid-dwell do not extend it (A2); an idle car reports an idle direction; `percentile` is nearest-rank; a car is busy from assignment until its last passenger alights, an idle car counts as unused, round robin's carried counts are equal by construction, and the balance figures are in the summary (A20); the service level counts waits over the threshold and the efficiency figures count intermediate stops and floors per passenger on a two-passenger case (A21); a park schedule moves the park floor at its ticks and is validated (A22); every invalid-input case in A15 is rejected with a message that names the row and the reason, and a UTF-8 BOM is tolerated.

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

The sample from the brief is run with each scheduler and its tick count, wait and total statistics are pinned. Every row of the committed comparison table (`docs/results/comparison.json`, 65 scenario × variant rows) is regenerated and compared field by field — passengers, ticks, wait and total distributions, per-car usage, balance — so that a behaviour change cannot orphan a figure quoted in the README, the design notes, the whitepaper or the deck without failing the suite. Three empirical findings are pinned as inequalities (parking reduces up-peak wait; the fairness weight lowers the maximum wait under the capacity burst; the zoned scenario is fully served); only findings that also held across fresh seeds (`docs/results/robustness.md`) are pinned this way — an earlier test pinned the fairness effect on the tall lobby traffic, which the seed study showed was a coincidence of the committed seed.

## 5. Scenario and tooling tests

`test_scenarios_and_compare.py`

The scenario generator is re-run inside the test and its output compared byte for byte with the committed CSV files, so the data in the README cannot drift from the generator. The `compare` and `run` CLIs are exercised end to end, and `report` is smoke-tested when `matplotlib` is installed (skipped otherwise, so the stdlib-only install still passes).

## 6. Conformance: the browser engine equals the Python engine

`test_js_conformance.py`

The interactive simulator on GitHub Pages runs a JavaScript port of the engine (`docs/viewer/engine.js`). Two implementations of the same rules will drift unless something stops them, so the suite runs the port with Node (`docs/viewer/conform.mjs`) on every committed scenario with every scheduler variant — 65 combinations — and asserts that positions per tick, the full event list, every passenger's assignment, boarding and alighting ticks, every car's carried, stops, floors and busy ticks, the count of long waits and the count of intermediate stops are identical to Python's. Skipped when Node is absent; CI installs it.

## What is not tested, and why

- Rendering details of the charts and the simulator page beyond "produces a file" / "loads without console errors" (the page is exercised in a headless browser at 1280×800, 1440×900 and 1920×1080: one screen, no console errors, floor click, live traffic, CSV upload, the stop-cost setting). The engine underneath is covered by the conformance matrix. Pixel tests would cost more than they catch here.
- Performance. The full comparison runs in a few seconds; there is no requirement that would justify a benchmark.
- The projection horizon bound in `etd.py` is generous by construction rather than proven tight; the invariant tests cover the outcome (every passenger delivered, deterministic), not the bound itself.

## Adversarial testing

Beyond the suite, the engine was fuzzed with 400 random buildings (1–10 cars, 2–60 floors, capacity 1–12, random express zones, park and start floors), reconstructing load from events and checking delivery, movement, capacity, boarding at origin and alighting at destination; no invariant broke, and the Hypothesis strategy was widened to the same ranges afterwards. Malformed and edge-case inputs — missing fields, a BOM, CRLF, blank lines, float times, a header-only file, a last-tick request, a single pair, adversarial oscillation and streaming cases — produced two fixes, both now covered by tests. The browser page's comparison figures were cross-checked against `comparison.md`, which found and fixed a double-rounding of the published means.

## Checks against theory

`scenarios/theory.py` ([`results/theory.md`](results/theory.md), about ten minutes) asks whether the engine produces what elevator-traffic theory says it should, which is evidence about the model rather than about the rules. Four checks. Exact identities on every committed scenario × rule run: Little's law in its finite form (the sum of every passenger's wait equals the sum over ticks of the number waiting), every passenger carried by exactly one car, floors travelled equal to the moves in the positions log, the load in the per-tick log equal to boardings minus alightings in the event list, and every boarding at the floor the log puts the car on — all 52 runs hold exactly. The classical up-peak round-trip time: one car parked at the lobby, everyone waiting there at tick 0 with uniform destinations, capacity *P*; Barney & Al-Sharif give the expected stops `S = N·(1 − (1 − 1/N)^P)` and the expected highest reversal floor `H = N − Σ(i/N)^P`, so with one tick per floor and one per stop the round trip is `2H + S + 1`. The formula is nowhere in the engine; the measured round trip matches it within 0.4% on six building sizes from 10 to 50 floors and capacities 4 to 10, twenty seeds each. Handling capacity: the same formula's five-minute capacity against each pattern's lobby demand predicts which committed runs saturate (the lobby burst at 177% of capacity, the two 51-floor cases at 104% and 122%) and which stay stable (the office patterns at 38–47%); the engine agrees on all seven. And the measured margins against published claims: destination dispatch is reported to cut trip times by about 25% over conventional control with the gains concentrated at peaks; here smart dispatch's time-to-destination gain over nearest car is 13–23% on the office peaks, 6% on quiet traffic and about 40% on the tower. `tests/test_theory.py` runs a fast version of the first two checks in the suite.
