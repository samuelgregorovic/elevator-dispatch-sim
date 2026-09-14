# Domain research: destination dispatch and elevator traffic

Research notes. Scope is deliberately limited to what changes a design decision in a simplified model where one time unit equals one floor of travel.

## 1. Assignment logic in commercial destination-dispatch controllers

Destination dispatch (also "destination control") replaces hall buttons with a kiosk where the passenger enters the destination floor; the controller assigns a car immediately and groups passengers with coincident destinations so each car makes fewer stops. Schindler's Miconic 10 (1990s) was the first commercial system, followed by Schindler PORT, Otis Compass / CompassPlus / Compass 360, and KONE Polaris. Vendors claim trip-time reductions of roughly a quarter and handling-capacity gains of roughly a third over conventional control, mostly from stop reduction.

The best-documented assignment method is the **Estimated Time to Destination (ETD)** algorithm described by Peters Research. For a new passenger and each candidate car *e*, the controller computes

```
TC_e = ETD_e + Σ_k SDF_e,k
```

where `ETD_e` is the new passenger's estimated time to destination if served by car *e* (arrival of the car at the origin, plus all intermediate stops, plus travel to the destination), and `SDF_e,k` is the *system degradation factor*: the delay imposed on each passenger *k* already assigned to car *e* by inserting the new stops. The passenger is allocated to the car with the lowest total cost. Capacity enters through a learned "capacity factor" and load weighing; the controller avoids allocating to cars projected to be full at the pickup floor.

Two operational facts matter for this model. First, in full destination systems the allocation is final once shown to the passenger (the display says "car C"); reallocation is only possible in hybrid systems with conventional hall buttons, and only until the allocated car begins slowing for the call. Second, coincident-call bonuses (favouring a car that already stops at that floor) raise handling capacity but make individual waits less even — some passengers wait longer so that the system moves more people.

Known weaknesses: passengers unfamiliar with the interface board the wrong car; groups entering one destination for several people overload cars unless load sensing or "group" buttons are used; and performance gains are concentrated in peak periods, so sizing a building on peak destination-dispatch figures is a documented mistake.

Sources: [Peters Research — ETD algorithm with destination dispatch and booster options](https://download.peters-research.com/library/ETD_Algorithm_with_Destination_Dispatch_and_Booster_Options.pdf) · [Wikipedia — Destination dispatch](https://en.wikipedia.org/wiki/Destination_dispatch) · [Elevator Wiki — Destination dispatch](https://elevation.fandom.com/wiki/Destination_dispatch) · [Elevator World — Otis launches CompassPlus](https://elevatorworld.com/article/otis-launches-compassplus/)

## 2. Classical dispatching baselines

**Collective control (SCAN/LOOK).** A car serves all calls in its current direction, then reverses. LOOK reverses at the last pending stop rather than the terminal floor. This is the near-universal car-level discipline because it never carries a passenger away from their destination; it is not itself a group-assignment rule.

**Nearest car.** Allocate the closest car that can still stop for the call. Simple and often adequate at low load; it ignores queued stops, so a close car with many pending stops beats a slightly farther empty one, and under peak load it degrades quickly.

**Estimated time of arrival (ETA).** Nearest car refined with time: travel distance plus an allowance per intermediate stop. Fixes the main failure of nearest car; still ignores the effect on passengers already aboard.

**Round robin.** Cars take calls in rotation. Trivially fair in the count of assignments and trivially bad in waiting time, since it ignores position entirely. Useful only as a floor for comparison.

**Zoning / sectoring.** Each car (or bank) serves a fixed range of floors. Reduces stops per trip and is the standard remedy when demand exceeds handling capacity; costs flexibility and can strand a zone when its car is far away. CIBSE practice is that a single group should serve at most about 15–16 floors, which is why tall buildings are split into rises.

Direction handling is common to all of them: every practical algorithm serves a hall call only with a car that will be travelling in the call's direction when it arrives.

Sources: [Peters Research — Elevator dispatching (ELEVCON 2014)](https://peters-research.com/index.php/papers/elevator-dispatching/) · [Elevator World — Elevator group control optimal](https://elevatorworld.com/article/elevator-group-control-optimal/) · [Peters Research — Lift planning for high-rise buildings](https://download.peters-research.com/library/Lift_Planning_for_High-Rise_Buildings.pdf)

## 3. Standard traffic patterns for benchmarking

The elevator-traffic literature (Barney & Al-Sharif, *Elevator Traffic Handbook*; CIBSE Guide D; BCO guidance) benchmarks on a five-minute peak and characterises traffic by its arrival rate as a percentage of the building population per five minutes and by its directional mix.

| Pattern | Arrival rate (% of population / 5 min) | Directional mix | Notes |
|---|---|---|---|
| Morning up-peak | 11–15 % (design), "excellent" ≥ 15 % | ~85 % up from lobby, 10 % down, 5 % interfloor (BCO) | Hardest on handling capacity; nearly all origins are the lobby |
| Lunchtime two-way | ~12 % | ~45 % up, 45 % down, 10 % interfloor | Described as the most difficult pattern for control because both directions saturate at once |
| Evening down-peak | higher instantaneous rate, shorter duration | dominant flow to lobby | Cars fill on the way down; lobby is the bottleneck |
| Interfloor | low, spread through the day | origin and destination both above lobby | Minor in offices; significant in hospitals and institutions |

Quality targets for offices (CIBSE / BCO): average waiting time in the morning up-peak ≤ 25–30 s for "good", ≤ 20–25 s for "excellent"; lunchtime average waiting time ≤ 40 s.

Sources: [Elevator World — Fundamentals of traffic analysis](https://elevatorworld.com/article/fundamentals-of-traffic-analysis/) · [Adsimulo — Lift performance criteria (CIBSE / BCO figures)](https://adsimulo.com/support/adsimulo-university/lift-performance-criteria/) · [Barney & Al-Sharif — Elevator Traffic Handbook, 2nd ed.](https://www.routledge.com/Elevator-Traffic-Handbook-Theory-and-Practice/Barney-Al-Sharif/p/book/9781032179650) · [Peters Research — Designing elevator installations using modern estimates of passenger demand](https://peters-research.com/index.php/papers/designing-elevator-installations-using-modern-estimates-of-passenger-demand/)

## 4. Performance metrics and the fairness question

Industry reporting uses **average waiting time** (call registration to car arrival), **transit time** (boarding to alighting), **time to destination** (their sum), and **handling capacity** (passengers moved per five minutes). Percentiles of waiting time are used alongside the average because the distribution has a long right tail: a few very long waits are what passengers remember, and a low average can hide them.

The tension between average performance and worst-case fairness is normally handled inside the cost function rather than by a separate rule. The classic reinforcement-learning formulation of elevator dispatching (Crites & Barto, reproduced in Sutton & Barto) minimises the sum of *squared* waiting times precisely so that long waits are penalised disproportionately; commercial cost functions achieve the same effect with an age-weighted term or a hard cap after which a waiting call takes priority. Pure throughput optimisation (coincident-call bonuses, sectoring) is known to lengthen some individual waits.

Sources: [Sutton & Barto — Reinforcement Learning, §11.4 Elevator dispatching](http://incompleteideas.net/book/first/ebook/node111.html) · [Peters Research — Elevator dispatching (ELEVCON 2014)](https://peters-research.com/index.php/papers/elevator-dispatching/) · [arXiv — Novel RL approach for efficient elevator group control](https://arxiv.org/html/2507.00011v1)

## 5. Express elevators and sky lobbies

Tall buildings are split into rises of roughly 15–16 floors; a high-rise group runs express through the lower floors and serves only its own zone. Sky lobbies go further: shuttle cars serve only the ground and the sky lobby, and passengers change to local cars. For a single-bank model that merely skips floors, the only assignment consequence is feasibility — a car can be allocated a passenger only if it serves both the origin and the destination floor. Transfers (two-leg journeys through a sky lobby) are a routing problem across banks and are out of scope here.

Sources: [Peters Research — Lift planning for high-rise buildings](https://download.peters-research.com/library/Lift_Planning_for_High-Rise_Buildings.pdf) · [Wikipedia — Sky lobby](https://en.wikipedia.org/wiki/Sky_lobby)

## Design implications for this project

1. The headline scheduler is an ETD-style cost function: `cost = new passenger's projected time to destination + Σ delay added to passengers already assigned to that car`; lowest cost wins. This is the documented industry approach, not an invention.
2. Assignment is final. The scheduler must therefore check projected capacity along the car's plan before assigning; a passenger who still meets a full car keeps their assignment and boards on the next pass.
3. Car-level movement is LOOK: continue in the committed direction while stops remain ahead, then reverse. A passenger boards only a car that will leave their floor in their direction, or an idle car.
4. Stops must cost time (configurable dwell, default 1 tick), otherwise stop reduction — the main benefit of destination dispatch — has no effect on the metrics.
5. Baselines: nearest car (with a LOOK-direction check) and round robin. ETA is subsumed by ETD; zoning is a configuration of per-car served floors rather than a separate algorithm.
6. Metrics: report min / max / average and p50 / p90 for wait and total time, plus the share of passengers whose wait exceeds twice the median, so the tail is visible.
7. Fairness is a weight in the cost function: an age term (waiting time so far, optionally squared) added to the cost of delaying an already-waiting passenger. Sweeping the weight gives the fairness-versus-efficiency curve the brief asks about.
8. Scenario generator parameters: up-peak 85/10/5 (up/down/interfloor) with lobby origins; lunch 45/45/10; down-peak dominant to lobby; arrival rates scaled from 11–15 % of a nominal population per five-minute window mapped onto ticks.
9. Express elevators are modelled as a `served_floors` set per car; the scheduler filters infeasible cars. Sky-lobby transfers are out of scope.
10. Scale: a single bank should not be expected to serve more than ~16 floors well; the 51-floor sample input from the brief is a stress case, and results on it should be read as such.
