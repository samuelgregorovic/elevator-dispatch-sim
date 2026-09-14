# Domain research: destination dispatch and elevator traffic

Research notes, revised so that every sentence is either quoted from a linked source or marked as the author's reasoning. Scope is deliberately limited to what changes a design decision in a simplified model where one time unit equals one floor of travel.

## 1. Assignment logic in commercial destination-dispatch controllers

Destination dispatch (also "destination control") replaces hall buttons with a kiosk where the passenger enters the destination floor; the controller assigns a car immediately and groups passengers with coincident destinations so each car makes fewer stops. Schindler's Miconic 10 (1990s) was the first commercial system, followed by Schindler PORT, Otis Compass / CompassPlus / Compass 360, and KONE Polaris. Reported gains vary by source: Wikipedia cites trip-time reductions of about 25% and handling-capacity gains of about 30% over conventional control; Otis's own CompassPlus material claims journeys "up to 50% faster". Both attribute the gain mainly to stop reduction.

The best-documented assignment method is the **Estimated Time to Destination (ETD)** algorithm described by Peters Research. For a new passenger and each candidate car *e*, the controller computes

```
TC_e = ETD_e + Σ_k SDF_e,k
```

where `ETD_e` is the new passenger's estimated time to destination if served by car *e* (arrival of the car at the origin, plus all intermediate stops, plus travel to the destination), and `SDF_e,k` is the *system degradation factor*: the delay imposed on each passenger *k* already assigned to car *e* by inserting the new stops. The passenger is allocated to the car with the lowest total cost. Capacity enters through a learned "capacity factor" and load weighing; the controller avoids allocating to cars projected to be full at the pickup floor.

Two operational facts matter for this model. First, in full destination systems the allocation is final once shown to the passenger (the display says "car C"); reallocation is only possible in hybrid systems with conventional hall buttons, and only until the allocated car begins slowing for the call (Peters, ETD paper). Second, coincident-call bonuses (favouring a car that already stops at that floor) raise handling capacity but "do not always improve quality of service; some passengers will wait longer" (Peters, ELEVCON 2014 paper cited in §2).

Known weaknesses: passengers unfamiliar with the interface board the wrong car; groups entering one destination for several people overload cars unless load sensing or "group" buttons are used; and performance gains are concentrated in peak periods, so sizing a building on peak destination-dispatch figures is a documented mistake.

Sources: [Peters Research — ETD algorithm with destination dispatch and booster options](https://download.peters-research.com/library/ETD_Algorithm_with_Destination_Dispatch_and_Booster_Options.pdf) · [Wikipedia — Destination dispatch](https://en.wikipedia.org/wiki/Destination_dispatch) · [Elevator Wiki — Destination dispatch](https://elevation.fandom.com/wiki/Destination_dispatch) · [Elevator World — Otis launches CompassPlus](https://elevatorworld.com/article/otis-launches-compassplus/)

## 2. Classical dispatching baselines

**Collective control (SCAN/LOOK).** A car serves all calls in its current direction, then reverses. LOOK reverses at the last pending stop rather than the terminal floor. This is the near-universal car-level discipline because it never carries a passenger away from their destination; it is not itself a group-assignment rule.

**Nearest car.** Allocate "the closest car that can stop in time for the landing call" (Peters). The failure mode is the author's reasoning, not a sourced finding: the rule ignores queued stops, so a close car with many pending stops beats a slightly farther empty one, and this matters more as load rises. The comparison in `DESIGN.md` confirms it on the committed scenarios.

**Estimated time of arrival (ETA).** Nearest car refined with time: the Peters paper illustrates a distant elevator with few stops being preferred over a closer one with many. ETA is subsumed by ETD, which additionally counts the delay to passengers already assigned.

**Round robin.** Cars take calls in rotation. Not discussed in the sources; included here as the author's baseline because it uses no state at all and therefore bounds what "ignoring position" costs.

**Zoning / sectoring.** Each car (or bank) serves a fixed range of floors. Peters names sectoring as a remedy "where passenger demand exceeds the handling capacity", because it reduces stops per trip; the flexibility cost is the author's reasoning and is measured in `DESIGN.md`. CIBSE practice, as quoted by Peters, is that a single group should serve at most about 15–16 floors, which is why tall buildings are split into rises.

Direction handling is common to all of them: collective control serves "all landing calls, and the resulting car calls in one direction" before reversing, so a hall call is served only by a car that will be travelling in the call's direction when it arrives.

Sources: [Peters Research — Elevator dispatching (ELEVCON 2014)](https://peters-research.com/index.php/papers/elevator-dispatching/) · [Peters Research — Lift planning for high-rise buildings](https://download.peters-research.com/library/Lift_Planning_for_High-Rise_Buildings.pdf)

## 3. Standard traffic patterns for benchmarking

The elevator-traffic literature (Barney & Al-Sharif, *Elevator Traffic Handbook*; CIBSE Guide D; BCO guidance) benchmarks on a five-minute peak and characterises traffic by its arrival rate as a percentage of the building population per five minutes and by its directional mix.

| Pattern | Arrival rate (% of population / 5 min) | Directional mix | Notes |
|---|---|---|---|
| Morning up-peak | 11–15 % of population per 5 min (Elevator World); handling-capacity grades from 11–14 % "fair" to > 15 % "excellent" (Adsimulo, from CIBSE) | 85 % up from lobby, 10 % down, 5 % interfloor (BCO 2014, via Adsimulo) | Hardest on handling capacity; nearly all origins are the lobby |
| Lunchtime two-way | handling-capacity target ≥ 12 % (Adsimulo) | 45 % up, 45 % down, 10 % interfloor (Adsimulo) | "Gradually becomes the most difficult situation to be handled" (Elevator World) because both directions saturate at once |
| Evening down-peak | "shorter in duration, but the arrival rate much higher" (Elevator World) | dominant flow to lobby | Cars fill on the way down; lobby is the bottleneck |
| Interfloor | low, spread through the day | origin and destination both above lobby | "Not serious in office buildings; more relevant in institutional facilities" (Elevator World) |

Quality targets for offices as tabulated by Adsimulo from CIBSE Guide D and BCO: average waiting time in the morning up-peak ≤ 25 s "excellent" and ≤ 30 s "good" for mixed tenancy (≤ 20 s and ≤ 25 s for single tenancy); BCO 2014 recommends < 25 s; lunchtime two-way average waiting time ≤ 40 s. The percentages used by the scenario generator are the office mixes in this table; the stress cases (`capacity_stress`, `tall_building`, `tall_lobby_traffic`) use mixes chosen for the comparison and say so in `scenarios/generate.py`.

Sources: [Elevator World — Fundamentals of traffic analysis](https://elevatorworld.com/article/fundamentals-of-traffic-analysis/) · [Adsimulo — Lift performance criteria (CIBSE / BCO figures)](https://adsimulo.com/support/adsimulo-university/lift-performance-criteria/) · [Barney & Al-Sharif — Elevator Traffic Handbook, 2nd ed.](https://www.routledge.com/Elevator-Traffic-Handbook-Theory-and-Practice/Barney-Al-Sharif/p/book/9781032179650) · [Peters Research — Designing elevator installations using modern estimates of passenger demand](https://peters-research.com/index.php/papers/designing-elevator-installations-using-modern-estimates-of-passenger-demand/)

## 4. Performance metrics and the fairness question

Industry reporting uses **average waiting time** (call registration to car arrival), **transit time** (boarding to alighting), **time to destination** (their sum), and **handling capacity** (passengers moved per five minutes). Percentiles of waiting time are used alongside the average because the distribution has a long right tail: a few very long waits are what passengers remember, and a low average can hide them.

The tension between average performance and worst-case fairness is normally handled inside the cost function rather than by a separate rule. The classic reinforcement-learning formulation of elevator dispatching (Crites & Barto, reproduced in Sutton & Barto §11.4) uses the sum of *squared* waiting times as its cost precisely so that long waits are penalised disproportionately (this citation is from the author's prior knowledge of the text; the host could not be re-fetched when the sources were checked). Pure throughput optimisation (coincident-call bonuses, sectoring) is documented to lengthen some individual waits (Peters, ELEVCON 2014). The age-weighted delay term used in this project's ETD scheduler is the author's design choice in the same spirit, not a documented feature of a commercial controller.

Sources: [Sutton & Barto — Reinforcement Learning, §11.4 Elevator dispatching](http://incompleteideas.net/book/first/ebook/node111.html) · [Peters Research — Elevator dispatching (ELEVCON 2014)](https://peters-research.com/index.php/papers/elevator-dispatching/) · [arXiv — Novel RL approach for efficient elevator group control](https://arxiv.org/html/2507.00011v1) (cited for its description of the ETD baseline, not for fairness)

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
7. Fairness is a weight in the cost function: an age term (waiting time so far) added to the cost of delaying an already-waiting passenger — the author's design choice, in the spirit of the squared-wait cost. Sweeping the weight gives the fairness-versus-efficiency curve the brief asks about.
8. Scenario generator parameters: up-peak 85/10/5 (up/down/interfloor) with lobby origins; lunch 45/45/10; down-peak dominant to lobby; arrival rates scaled from 11–15 % of a nominal population per five-minute window mapped onto ticks. Stress and tall-building mixes are chosen for the comparison, not taken from the literature.
9. Express elevators are modelled as a `served_floors` set per car; the scheduler filters infeasible cars. Sky-lobby transfers are out of scope.
10. Scale: a single bank should not be expected to serve more than ~16 floors well; the 51-floor sample input from the brief is a stress case, and results on it should be read as such.
