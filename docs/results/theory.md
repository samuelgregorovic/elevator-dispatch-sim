# Checks against theory

Does the engine produce what elevator-traffic theory says it should? Four checks; regenerate with `uv run python scenarios/theory.py`.

## 1. Exact identities on every committed run

Little's law in its finite form — the sum of every passenger's wait equals the sum over ticks of the number of people waiting — plus conservation: every passenger carried by exactly one car, floors travelled equal to the moves in the positions log, the load in the per-tick log equal to boardings minus alightings in the event list, and every boarding or alighting at the floor the positions log puts the car on.

52 runs (every manifest scenario x four rules): **all identities hold exactly.**

## 2. Up-peak round-trip time against the classical formula

One car parked at the lobby, everyone at the lobby at tick 0 with uniformly random destinations, capacity P. Barney & Al-Sharif give the expected number of stops S = N·(1 - (1 - 1/N)^P) and the expected highest reversal floor H = N - Σ(i/N)^P over N floors above the lobby; with one tick per floor and one tick per stop the round trip is 2H + S + 1. Measured: ticks per trip over 240 passengers, 20 seeds.

| floors | P | S (formula) | H (formula) | RTT formula | RTT measured | error |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 4 | 3.38 | 7.66 | 19.7 | 19.6 ± 0.3 | -0.4% |
| 10 | 8 | 5.49 | 8.43 | 23.3 | 23.3 ± 0.3 | -0.1% |
| 20 | 8 | 6.67 | 17.35 | 42.4 | 42.5 ± 0.8 | +0.3% |
| 20 | 10 | 7.94 | 17.73 | 44.4 | 44.4 ± 0.8 | +0.1% |
| 50 | 8 | 7.45 | 44.04 | 96.5 | 96.2 ± 1.5 | -0.3% |
| 50 | 10 | 9.13 | 45.03 | 100.2 | 100.0 ± 1.4 | -0.2% |

## 3. Handling capacity against demand

The same formula gives each bank's five-minute handling capacity (window / interval x car capacity, interval = RTT / cars). Where lobby-bound demand exceeds it the run must saturate — a backlog still standing at the end of the arrival window and a large share of long waits — and where it does not, the run must be stable. Committed seed, ETD.

| pattern | cars x P | RTT | interval | capacity / window | lobby demand / window | utilisation | predicted | backlog at window end | peak backlog | waits > 30 |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| morning_up_peak | 4 x 8 | 42 | 10.6 | 113 | 49 | 44% | stable | 1 | 10 | 0% |
| lunch_two_way | 4 x 8 | 42 | 10.6 | 113 | 43 | 38% | stable | 2 | 4 | 0% |
| evening_down_peak | 4 x 8 | 42 | 10.6 | 113 | 53 | 47% | stable | 3 | 9 | 0% |
| interfloor | 4 x 8 | 42 | 10.6 | 113 | 0 | 0% | stable | 0 | 6 | 0% |
| capacity_stress | 2 x 6 | 40 | 19.9 | 45 | 80 | 177% | saturated | 37 | 37 | 80% |
| tall_building | 6 x 10 | 102 | 17.0 | 88 | 92 | 104% | saturated | 11 | 30 | 16% |
| tall_lobby_traffic | 6 x 10 | 102 | 17.0 | 88 | 108 | 122% | saturated | 15 | 26 | 24% |

## 4. Measured margins against published claims

Published figures for destination dispatch over conventional control: trip times about 25% shorter, handling capacity about 30% higher, with the gains concentrated in peak periods (RESEARCH.md §1). Measured here: ETD's reduction in mean time to destination against nearest car, ten fresh seeds per pattern.

| pattern | arrival rate | time-to-destination gain |
|---|---:|---:|
| morning_up_peak | 13% / window | 16% ± 6 |
| lunch_two_way | 12% / window | 23% ± 5 |
| evening_down_peak | 14% / window | 13% ± 7 |
| interfloor | 6% / window | 6% ± 5 |
| capacity_stress | 20% / window | 8% ± 8 |
| tall_building | 12% / window | 39% ± 12 |
| tall_lobby_traffic | 12% / window | 41% ± 5 |
