# Assumptions and simplifications

Every item here is a place where the brief (`brief.pdf`) leaves a choice open. Each records the decision, the reason, and whether it is configurable. These were fixed before the code that depends on them was written.

## Time

**A1. One tick = one floor of travel.** As specified. A car at floor 3 moving up is at floor 4 one tick later.

**A2. Stops cost time.** The brief does not say whether boarding takes time. Default: a car that stops at a floor to load or unload spends `dwell_ticks = 1` tick stationary there before moving on. Reason: without a stop cost, "fewer stops" — the main benefit of destination dispatch — has no effect on any metric, and every scheduler looks the same. `dwell_ticks = 0` reproduces the literal brief and is supported.

A stop is one dwell per floor visit. Passengers who arrive at the floor while the car is already dwelling there may still board if there is room, but they do not restart the dwell; the car leaves when the dwell ends and anyone who missed it waits for the next pass. `stops_made` counts floor visits with activity, not boarding events. (An earlier implementation restarted the dwell on every boarding, which let a busy lobby hold a car indefinitely.)

**A3. Order of operations within a tick `t`.** A tick is the state of the system *at* time `t`; movement happens between ticks.

1. Release all requests with `time == t` to the controller (never any with `time > t`).
2. The scheduler assigns each new request to exactly one car, in input order.
3. At each car's current floor: passengers whose destination is this floor alight; then assigned passengers waiting at this floor board, in request order, while capacity and direction allow. Boarding or alighting starts a dwell if `dwell_ticks > 0`.
4. Positions of all cars at time `t` are logged. Tick 0 therefore shows the initial positions.
5. Each car advances toward its state at `t + 1`: if dwelling, the dwell counter decrements and the car stays; otherwise it moves one floor toward its next stop, or stays if idle.

Consequence: a passenger who requests at `t` on the floor where an idle car already stands boards at `t` and has wait time 0. A car one floor away arrives at `t + 1`. With `dwell_ticks = 1`, a car that boards at `t` is still at that floor at `t + 1` and moves at `t + 2`.

*Revision note:* the first draft of this list placed movement before boarding, so tick 0 would have logged positions after a move. The tests written against the consequence above exposed the inconsistency and the order was corrected before the first commit of the engine.

**A4. Metrics.** `wait = board_time − request_time`; `travel = alight_time − board_time`; `total = wait + travel`. All integers in ticks.

**A5. Termination.** The simulation runs until every request has been released and every passenger has alighted. Positions are logged for every tick from 0 to the final tick inclusive. If the last request time is beyond the current tick, the simulation keeps ticking one unit at a time until it arrives there (it never jumps).

## Building and cars

**A6. Floors are numbered `1..n`.** The sample input uses floors 1, 20, 37 and 51, so the sample building has at least 51 floors. Floor 1 is the lobby.

**A7. Initial state.** All cars start idle at floor 1 at tick 0 (configurable `start_floor`).

**A8. Capacity.** Each car carries at most `capacity` passengers. A car never exceeds it: if a waiting passenger's assigned car arrives full, the passenger stays on the floor and the car keeps the stop until the passenger has boarded.

**A9. Idle behaviour.** An idle car stays where it last stopped. Optional `park_floor` policy sends idle cars to a floor (usually the lobby); off by default.

**A10. Express cars.** A car may have a `served_floors` set. It never stops elsewhere and is never assigned a passenger whose origin or destination it does not serve. A request that no car could serve is rejected before the run starts, and a park floor must be served by every express car. Transfers between cars (sky lobbies) are out of scope.

## Dispatch

**A11. Assignment is immediate and final.** The brief says the system immediately assigns each passenger to a specific car and that the destination cannot be changed. Assignment to a car is treated as immutable as well, which is how commercial destination-dispatch systems behave (the kiosk displays the car). Consequence: the scheduler must be capacity-aware when assigning, and a passenger is never moved to another car later.

**A12. Direction discipline (LOOK).** A car with pending stops keeps moving in its current direction while any stop lies ahead in that direction, then reverses. A car never reverses with passengers aboard whose destinations lie ahead. A waiting passenger boards only a car that will depart their floor in the passenger's direction, or a car that is idle at that floor (which then adopts the direction of the longest-waiting passenger there).

One refinement, found by a property-based test: a passenger waiting at the car's current floor who wants to travel in the car's current direction counts as a stop ahead. Without it, a single car with two waiting passengers on adjacent floors wanting opposite directions reverses at each floor before either can board and oscillates forever.

**A13. Tie-breaking is deterministic.** When two cars have equal cost, the lower car index wins. Combined with seeded scenario generation this makes every run reproducible byte for byte. For nearest-car, which has no load term, this means simultaneous requests at one floor all go to the lowest-index idle car there; the `nearest_car_balanced` variant breaks ties by occupancy instead, and the comparison reports both so that the share of the margin due to the tie-break is visible (small across seeds; see `results/robustness.md`).

## Input

**A14. Input format.** CSV with header `time,id,source,dest`, as in the brief. Rows need not be sorted; they are sorted by `time` (stable, preserving file order within a tick) on load. Sorting is not peeking: the controller still only sees a row once the clock reaches its `time`.

**A15. Validation.** The following are rejected with a message naming the row: rows with fewer than four fields; non-integer fields; `time < 0`; `source == dest`; `source` or `dest` outside `1..n`; duplicate `id`. An empty request list is valid and produces a single log row for tick 0. The parser is otherwise Python's: rows with extra fields are accepted and the extras ignored, `int()` accepts `1_000`, ` 3 `, `+1` and Unicode digits, and a file with only a header runs as no passengers. None of these produce a wrong result, so they are documented rather than rejected.

**A16. No peek-ahead is structural.** The simulation reads requests through a feed object that only releases rows with `time <= now`. The scheduler receives new requests one tick at a time and has no reference to the feed. A spy scheduler that records the clock at which it sees each request asserts this, and the feed's release rule is tested directly.

## Output

**A17. Positions log.** `positions.csv` with header `time,elevator_1,…,elevator_k` and one row per tick.

**A18. Trace.** `trace.json` with per-tick car state (floor, direction, load, dwell) and events (request, assign, board, alight) for inspection and debugging. Not required by the brief; it is what makes behaviour inspectable. (The first browser viewer replayed this file; the current simulator runs its own port of the engine instead, so the trace is now for the `run` command's users.)

**A19. Statistics.** For wait and total time: min, max, mean, p50, p90; plus a short list of generated observations (share of passengers waiting more than twice the median, busiest origin floor, per-car usage and balance).

**A20. Car usage and balance.** Per car: passengers carried, stops, floors travelled, and *busy ticks* — ticks in which the car has a passenger aboard or a passenger assigned and still waiting; *busy share* is busy ticks over ticks simulated. A car moving to park is not busy, and a parked run lasts until the cars have parked, so its busy shares are computed over a slightly longer run than the unparked one (484 against 474 ticks on the morning peak). Balance across cars: the mean busy share (how much car-time the rule spends), the *spread* (busiest minus least busy car's share, in points), and the busiest car's share of delivered passengers against the fair share 1/cars. Reason: waiting time says how the passengers fared; these say how the cars were used — the same result achieved with less car-time is cheaper to run, and work concentrated on one car is uneven wear. Both are reported by `run`, `compare`, the charts and the browser simulator, and the browser port is held to the Python definition by the conformance test.

## Out of scope

Real-time clock synchronisation; acceleration, door and travel physics beyond the one-floor-per-tick model; reassignment after dispatch; sky-lobby transfers; passenger no-shows or group entries; energy.
