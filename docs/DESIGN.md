# Design

How the simulation is built, how the schedulers decide, and what the comparison shows. Assumptions are in [`ASSUMPTIONS.md`](ASSUMPTIONS.md) and are referenced here by number; the domain background is in [`RESEARCH.md`](RESEARCH.md).

## Architecture

```mermaid
flowchart LR
    CSV[requests.csv] --> V[validate] --> F[RequestFeed<br/>releases time ≤ now]
    F --> S[Simulation<br/>tick loop]
    S -->|assign| SCH[Scheduler<br/>etd · nearest_car · round_robin]
    SCH -->|car index| S
    S --> E[Elevator ×k<br/>LOOK movement, capacity, dwell]
    S --> P[positions.csv]
    S --> T[trace.json]
    S --> M[metrics → summary.json]
```

Seven small modules, one responsibility each:

| module | responsibility |
|---|---|
| `model.py` | `Request`, `Passenger`, `Elevator`. The car's movement and boarding rules live here so the simulation and the ETD projection share one implementation. |
| `feed.py` | `RequestFeed`: the only source of requests; releases rows with `time <= now` (A16). |
| `simulation.py` | The tick loop in the fixed order of A3; produces positions, per-tick car states and events. |
| `schedulers/` | `Scheduler` protocol plus three implementations behind one interface. |
| `metrics.py` | Distributions (min, max, mean, p50, p90) and generated observations. |
| `validate.py`, `io.py` | Fail-fast input checks; CSV/JSON readers and writers. |
| `compare.py` | Runs a scheduler × scenario matrix from `scenarios/manifest.json`. |

The runtime is standard library only; `matplotlib` is an optional extra used only to render charts.

## The tick

A tick is the state at time `t`. Within a tick: release requests due at `t` → scheduler assigns each one → each car alights and boards at its current floor → positions logged → each car advances one step toward `t + 1` (dwell, move one floor, or stay). The consequences that matter: an idle car on the request floor gives wait 0; a car one floor away gives wait 1; a stop costs one extra tick by default (A2).

The loop ends when the feed is exhausted and every car is at rest. The simulation never jumps: if the next request is far in the future it ticks through the idle time, as the brief requires.

## Car behaviour

Each car runs LOOK (A12): keep the current direction while a stop lies ahead, otherwise reverse, otherwise idle. Stops are the destinations of passengers aboard plus the origins of passengers assigned but not yet picked up. A passenger boards only if the car will leave the floor in their direction, so no one is carried the wrong way; a full car keeps the pickup as a pending stop and returns (A8, A11).

One rule was added after a property-based test found a livelock: a passenger waiting at the car's *current* floor who wants to go in the car's current direction counts as a stop ahead. Without it, a single car facing two waiting passengers on adjacent floors with opposite directions reversed at each floor before either could board.

## Schedulers

All three implement `assign(request, cars, now) -> car index`, see only the current state of the cars, and must return a car that serves both floors (express cars, A10). Ties go to the lower car index (A13).

**Round robin.** Cars take requests in rotation. No use of position at all; a floor for the comparison.

**Nearest car.** Distance from the car to the origin, plus a large penalty if the car is moving away from the origin or in the wrong direction for the passenger. Ignores queued stops, which is the documented weakness of nearest-car control: a close car with many stops beats a slightly farther empty one.

**ETD (estimated time to destination).** The industry approach for destination dispatch (RESEARCH §1). For each feasible car the scheduler projects the car's route twice — as it is, and with the new passenger inserted — using the same LOOK and boarding code the simulation runs, so the projection is exact for that car if no further requests arrive. The cost is

```
cost(car) = (alight_new − now)                             # new passenger's time to destination
          + Σ_k  w_k · (alight_k' − alight_k)              # delay inflicted on each passenger k already
                                                           # assigned to the car (Peters' "system
                                                           # degradation factor")
w_k = 1 + fairness · (now − request_k)  if k is still waiting, else 1
```

and the lowest-cost car wins. Capacity enters through the projection: if the car would be full when it reaches the new passenger, the projection shows them boarding on a later pass and the cost rises accordingly. With `fairness = 0` the cost is pure system time; a positive weight makes delaying a passenger who has already waited a long time progressively more expensive, which is how commercial controllers keep the tail of the waiting-time distribution in check (RESEARCH §4).

The projection is O(route length) per candidate car and runs once per request, so a request costs O(cars × route). For the sizes in the brief (≤ 10 cars, hundreds of requests) a full comparison over all scenarios runs in about a second.

## What the comparison shows

`uv run python -m elevator_sim compare --fairness 0.5` on the committed scenarios (dwell 1, all cars start at the lobby; `etd_f0.5` is ETD with fairness weight 0.5). The sample from the brief is discussed separately below.

| scenario | scheduler | n | ticks | wait avg | wait p90 | wait max | total avg | total p90 | total max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| morning_up_peak | etd | 166 | 474 | 6.8 | 15 | 19 | 20.2 | 32 | 44 |
| morning_up_peak | nearest_car | 166 | 503 | 11.9 | 35 | 44 | 24.8 | 45 | 62 |
| morning_up_peak | round_robin | 166 | 494 | 16.6 | 34 | 42 | 29.4 | 47 | 64 |
| morning_up_peak | etd_f0.5 | 166 | 476 | 7.7 | 17 | 25 | 20.8 | 31 | 42 |
| lunch_two_way | etd | 131 | 476 | 4.2 | 11 | 21 | 15.2 | 26 | 40 |
| lunch_two_way | nearest_car | 131 | 489 | 7.3 | 18 | 36 | 18.5 | 35 | 52 |
| lunch_two_way | round_robin | 131 | 487 | 13.2 | 28 | 38 | 24.2 | 40 | 55 |
| lunch_two_way | etd_f0.5 | 131 | 474 | 4.7 | 13 | 21 | 15.6 | 26 | 40 |
| evening_down_peak | etd | 113 | 341 | 7.8 | 17 | 25 | 19.6 | 36 | 44 |
| evening_down_peak | nearest_car | 113 | 331 | 12.3 | 37 | 49 | 24.8 | 49 | 69 |
| evening_down_peak | round_robin | 113 | 337 | 17.9 | 33 | 42 | 30.0 | 46 | 61 |
| evening_down_peak | etd_f0.5 | 113 | 337 | 8.7 | 17 | 27 | 20.4 | 35 | 45 |
| interfloor | etd | 85 | 457 | 3.9 | 10 | 17 | 11.4 | 19 | 29 |
| interfloor | nearest_car | 85 | 453 | 5.4 | 16 | 36 | 13.0 | 26 | 39 |
| interfloor | round_robin | 85 | 462 | 8.1 | 15 | 27 | 15.5 | 25 | 47 |
| interfloor | etd_f0.5 | 85 | 457 | 3.6 | 8 | 17 | 11.1 | 19 | 29 |
| capacity_stress | etd | 76 | 290 | 60.3 | 91 | 120 | 73.0 | 108 | 140 |
| capacity_stress | nearest_car | 76 | 340 | 82.1 | 153 | 178 | 94.8 | 171 | 196 |
| capacity_stress | round_robin | 76 | 281 | 60.1 | 98 | 128 | 72.8 | 110 | 135 |
| capacity_stress | etd_f0.5 | 76 | 269 | 55.2 | 83 | 99 | 67.7 | 96 | 119 |
| tall_building | etd | 231 | 362 | 17.9 | 38 | 108 | 47.0 | 73 | 124 |
| tall_building | nearest_car | 231 | 487 | 54.8 | 115 | 227 | 84.1 | 156 | 242 |
| tall_building | round_robin | 231 | 431 | 51.4 | 95 | 115 | 80.2 | 131 | 164 |
| tall_building | etd_f0.5 | 231 | 362 | 16.5 | 31 | 44 | 45.4 | 67 | 86 |
| tall_lobby_traffic | etd | 198 | 380 | 20.5 | 38 | 52 | 50.6 | 79 | 97 |
| tall_lobby_traffic | nearest_car | 198 | 444 | 43.8 | 106 | 209 | 74.1 | 153 | 260 |
| tall_lobby_traffic | round_robin | 198 | 423 | 47.6 | 90 | 121 | 77.4 | 127 | 158 |
| tall_lobby_traffic | etd_f0.5 | 198 | 365 | 16.8 | 29 | 47 | 46.7 | 66 | 79 |
| morning_up_peak_parked | etd | 166 | 488 | 4.7 | 12 | 18 | 17.4 | 28 | 39 |
| morning_up_peak_parked | nearest_car | 166 | 515 | 13.3 | 37 | 45 | 26.3 | 52 | 66 |
| morning_up_peak_parked | round_robin | 166 | 507 | 16.5 | 33 | 40 | 29.1 | 47 | 63 |
| morning_up_peak_parked | etd_f0.5 | 166 | 487 | 5.8 | 14 | 25 | 18.4 | 29 | 40 |
| tall_lobby_zoned | etd | 198 | 394 | 26.0 | 59 | 79 | 55.5 | 98 | 133 |
| tall_lobby_zoned | nearest_car | 198 | 471 | 55.6 | 127 | 205 | 84.7 | 178 | 259 |
| tall_lobby_zoned | round_robin | 198 | 549 | 56.5 | 144 | 248 | 85.9 | 180 | 299 |
| tall_lobby_zoned | etd_f0.5 | 198 | 416 | 28.1 | 65 | 93 | 57.0 | 103 | 128 |

Observations:

- ETD has the lowest average and p90 wait on every realistic pattern, by a factor of roughly 1.5–3 over nearest-car. The gap is widest on the tall building, where nearest-car's blindness to queued stops hurts most.
- On `capacity_stress` (two small cars, everyone at the lobby at once) ETD and round robin are equal. When every request has the same origin and the system is saturated, the only lever is spreading load evenly, and round robin does that by construction. Nearest-car is worst here because it keeps piling passengers onto whichever car is nearest the lobby.
- On the three-request sample from the brief nearest-car happens to beat ETD (6.3 vs 15.0 average wait). ETD spreads the two lobby passengers over both cars to avoid the extra stop, which leaves no idle car for the third request; nearest-car puts both on car 1 and the idle car 2 collects the third. Greedy assignment with no knowledge of future demand can lose on tiny inputs; the scenarios are what the algorithm should be judged on.
- Round robin's maximum wait is often *lower* than nearest-car's (tall building: 115 vs 227). Ignoring position is bad on average but it never starves anyone, which is the fairness-versus-efficiency tension the brief asks about; the ETD fairness weight is the deliberate version of that trade.

## Policies: fairness weight, parking, zoning

Three configuration-level policies were added after the baseline comparison. Each is one flag; the table above already includes them.

**Fairness weight.** With `fairness = 0.5` the delay inflicted on a passenger who has waited `a` ticks is weighted `1 + 0.5·a`. On the tall building this cuts the maximum wait from 108 to 44 ticks *and* lowers the average total time (47.0 → 45.4): protecting the tail also removes the pathological assignments that produced it. On the 20-floor office patterns the same weight costs a little on average (up-peak 6.8 → 7.7) and raises the maximum (19 → 25). The effect is not monotonic in the weight — see `docs/charts/fairness_sweep_*.png` — because the cost function is greedy and per-request; the weight changes which local optimum is picked, not the global structure. Read it as a tuning knob to be set per building and traffic profile, not a free lunch.

**Park idle cars at the lobby.** `morning_up_peak_parked` is the same traffic with `park_floor = 1`. ETD's average wait falls from 6.8 to 4.7 ticks (−30%) and the maximum from 19 to 18: in up-peak nearly every request starts at the lobby, so an idle car waiting there answers it with wait 0. The cost is extra travel (empty runs down) and it would hurt in down-peak, where idle cars should wait high; the right policy is time-of-day dependent, which is why it is a flag rather than a default.

**Zoning / express cars.** `tall_lobby_zoned` splits six cars into three local (floors 1–26) and three express (lobby + 27–51), on lobby-only traffic. It is *worse* than the same six cars unzoned: ETD average wait 26.0 vs 20.5, maximum 79 vs 52. At this load the loss of flexibility (a request for floor 30 can only use three cars) outweighs the stop reduction. Zoning is a handling-capacity tool for saturated tall buildings and a way to save shaft space, not a wait-time optimisation at moderate load — consistent with the guidance in `RESEARCH.md` §5. Interfloor trips across the zone boundary are rejected with a clear error; serving them needs a sky-lobby transfer, which is out of scope.

## Trade-offs made

- **Tick-based over event-driven.** The brief asks for a discrete-time model and the outputs are per-tick; an event queue would be faster for large idle gaps but adds complexity for no benefit at this scale.
- **Immutable assignment.** Matches real destination dispatch and the brief's wording; it also makes the scheduler's capacity awareness matter. Reassignment (as hybrid ETA systems allow until the car slows) would improve results under bursty load and is listed as future work.
- **Exact projection over a heuristic ETA.** Reusing the car's own movement code for projection is slower than an arithmetic estimate but cannot disagree with the simulation, which removes a whole class of subtle bugs.
- **Greedy, per-request assignment.** No look-ahead and no batch re-optimisation. This is what commercial controllers do at request time; it is also why ETD can lose on a tiny sample.
- **Generated observations over prose.** The brief asks for "notable observations"; producing them from the data for every run is more useful than writing a paragraph about one run.
