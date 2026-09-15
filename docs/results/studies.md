# Sensitivity studies

Seeds 101-105 where a study says "across seeds" (mean ± sd); the committed seed otherwise. Ticks throughout; the service level counts passengers waiting more than 30 ticks. Regenerate with `uv run python scenarios/studies.py`.

## Stop cost (dwell 0, 1, 2) — committed seeds

Average wait; in brackets, the rule's wait divided by ETD's at the same dwell.

| pattern | dwell | etd | nearest_car | round_robin |
|---|---:|---:|---:|---:|
| morning_up_peak | 0 | 6.8 | 11.5 (1.71x) | 15.4 (2.28x) |
| morning_up_peak | 1 | 7.1 | 12.0 (1.69x) | 16.5 (2.31x) |
| morning_up_peak | 2 | 7.6 | 14.5 (1.91x) | 18.1 (2.37x) |
| lunch_two_way | 0 | 3.9 | 7.3 (1.90x) | 12.2 (3.17x) |
| lunch_two_way | 1 | 4.0 | 6.9 (1.70x) | 13.2 (3.27x) |
| lunch_two_way | 2 | 7.0 | 9.0 (1.29x) | 14.0 (2.02x) |
| evening_down_peak | 0 | 6.9 | 9.6 (1.40x) | 14.1 (2.05x) |
| evening_down_peak | 1 | 7.6 | 10.8 (1.42x) | 17.9 (2.36x) |
| evening_down_peak | 2 | 9.8 | 10.9 (1.11x) | 20.5 (2.08x) |
| interfloor | 0 | 3.6 | 4.5 (1.23x) | 7.2 (1.96x) |
| interfloor | 1 | 3.9 | 4.5 (1.17x) | 8.1 (2.08x) |
| interfloor | 2 | 4.0 | 5.4 (1.36x) | 9.0 (2.28x) |
| capacity_stress | 0 | 42.8 | 65.8 (1.54x) | 42.5 (0.99x) |
| capacity_stress | 1 | 60.3 | 76.2 (1.26x) | 60.1 (1.00x) |
| capacity_stress | 2 | 75.2 | 92.4 (1.23x) | 77.8 (1.03x) |
| tall_building | 0 | 12.9 | 39.9 (3.10x) | 40.9 (3.18x) |
| tall_building | 1 | 18.3 | 67.1 (3.68x) | 51.4 (2.81x) |
| tall_building | 2 | 35.3 | 77.6 (2.20x) | 59.5 (1.69x) |
| tall_lobby_traffic | 0 | 16.7 | 51.2 (3.06x) | 43.2 (2.58x) |
| tall_lobby_traffic | 1 | 21.4 | 65.0 (3.03x) | 47.5 (2.22x) |
| tall_lobby_traffic | 2 | 25.6 | 75.7 (2.95x) | 55.9 (2.18x) |
| office_day | 0 | 5.0 | 7.6 (1.54x) | 12.5 (2.53x) |
| office_day | 1 | 5.1 | 8.4 (1.64x) | 13.8 (2.68x) |
| office_day | 2 | 6.8 | 8.5 (1.25x) | 14.1 (2.09x) |

## Load — arrival rate scaled, across seeds

Average wait (share waiting > 30 ticks).

| pattern | rate x | etd | nearest_car | round_robin |
|---|---:|---:|---:|---:|
| morning_up_peak | 0.5 | 6.2 ± 0.5 (0%) | 8.2 ± 1.6 (3%) | 11.3 ± 1.2 (3%) |
| morning_up_peak | 0.75 | 7.0 ± 0.5 (0%) | 8.9 ± 1.5 (6%) | 13.0 ± 1.3 (7%) |
| morning_up_peak | 1.0 | 6.7 ± 0.5 (0%) | 11.1 ± 1.1 (12%) | 15.0 ± 0.7 (11%) |
| morning_up_peak | 1.5 | 7.9 ± 1.5 (0%) | 15.6 ± 1.7 (25%) | 17.3 ± 0.8 (17%) |
| morning_up_peak | 2.0 | 10.9 ± 1.5 (1%) | 31.5 ± 9.1 (49%) | 21.3 ± 1.2 (28%) |
| lunch_two_way | 0.5 | 3.7 ± 1.2 (0%) | 5.5 ± 1.1 (2%) | 9.3 ± 1.3 (1%) |
| lunch_two_way | 0.75 | 3.9 ± 0.7 (0%) | 7.2 ± 1.3 (3%) | 12.6 ± 1.0 (5%) |
| lunch_two_way | 1.0 | 4.7 ± 0.5 (0%) | 8.5 ± 0.3 (7%) | 13.8 ± 1.1 (8%) |
| lunch_two_way | 1.5 | 5.3 ± 0.9 (0%) | 11.1 ± 1.3 (13%) | 17.3 ± 0.7 (16%) |
| lunch_two_way | 2.0 | 7.0 ± 0.2 (0%) | 13.6 ± 1.4 (18%) | 19.7 ± 0.5 (24%) |
| evening_down_peak | 0.5 | 6.2 ± 0.9 (0%) | 8.4 ± 0.9 (2%) | 10.6 ± 1.4 (2%) |
| evening_down_peak | 0.75 | 6.8 ± 1.1 (0%) | 9.6 ± 1.9 (6%) | 13.8 ± 2.0 (5%) |
| evening_down_peak | 1.0 | 7.0 ± 0.7 (0%) | 10.7 ± 1.2 (8%) | 15.4 ± 1.1 (9%) |
| evening_down_peak | 1.5 | 7.9 ± 0.4 (0%) | 14.3 ± 3.1 (18%) | 17.7 ± 1.8 (17%) |
| evening_down_peak | 2.0 | 9.5 ± 0.7 (1%) | 22.6 ± 4.8 (28%) | 22.4 ± 1.0 (28%) |
| interfloor | 0.5 | 4.1 ± 0.8 (0%) | 4.2 ± 0.7 (0%) | 6.3 ± 1.1 (0%) |
| interfloor | 0.75 | 3.9 ± 0.9 (0%) | 4.2 ± 0.8 (0%) | 7.2 ± 0.4 (0%) |
| interfloor | 1.0 | 4.1 ± 0.3 (0%) | 4.6 ± 0.4 (0%) | 8.2 ± 0.5 (0%) |
| interfloor | 1.5 | 4.2 ± 0.4 (0%) | 5.9 ± 1.4 (1%) | 9.6 ± 0.9 (2%) |
| interfloor | 2.0 | 4.9 ± 0.4 (0%) | 7.7 ± 1.0 (5%) | 12.6 ± 1.7 (5%) |
| capacity_stress | 0.5 | 10.4 ± 2.7 (1%) | 16.2 ± 4.3 (28%) | 17.5 ± 3.2 (19%) |
| capacity_stress | 0.75 | 26.0 ± 10.0 (35%) | 29.9 ± 7.2 (57%) | 29.3 ± 8.0 (45%) |
| capacity_stress | 1.0 | 57.8 ± 17.1 (69%) | 66.2 ± 15.6 (78%) | 64.3 ± 18.8 (75%) |
| capacity_stress | 1.5 | 118.7 ± 17.7 (86%) | 127.4 ± 15.3 (86%) | 126.8 ± 16.6 (87%) |
| capacity_stress | 2.0 | 183.2 ± 14.2 (89%) | 196.9 ± 19.8 (89%) | 183.1 ± 18.5 (90%) |
| tall_building | 0.5 | 13.0 ± 3.3 (9%) | 34.6 ± 6.0 (39%) | 43.8 ± 3.6 (63%) |
| tall_building | 0.75 | 16.6 ± 4.2 (16%) | 42.9 ± 7.9 (42%) | 46.2 ± 0.6 (64%) |
| tall_building | 1.0 | 22.8 ± 7.2 (30%) | 59.6 ± 10.2 (51%) | 52.0 ± 3.6 (70%) |
| tall_building | 1.5 | 48.0 ± 7.7 (62%) | 97.0 ± 24.8 (56%) | 79.1 ± 7.9 (81%) |
| tall_building | 2.0 | 105.7 ± 15.9 (76%) | 169.5 ± 51.4 (67%) | 130.6 ± 12.9 (87%) |
| tall_lobby_traffic | 0.5 | 16.4 ± 2.9 (18%) | 34.4 ± 4.7 (39%) | 40.5 ± 2.1 (57%) |
| tall_lobby_traffic | 0.75 | 17.4 ± 6.9 (18%) | 44.7 ± 12.9 (45%) | 45.3 ± 1.4 (64%) |
| tall_lobby_traffic | 1.0 | 31.1 ± 5.7 (53%) | 67.9 ± 7.8 (54%) | 54.5 ± 1.7 (73%) |
| tall_lobby_traffic | 1.5 | 84.7 ± 19.5 (76%) | 148.6 ± 30.5 (66%) | 103.2 ± 13.3 (86%) |
| tall_lobby_traffic | 2.0 | 143.4 ± 14.8 (80%) | 227.3 ± 41.6 (72%) | 159.2 ± 10.0 (89%) |

## Cars — how many to keep long waits under 10%, across seeds

**morning_up_peak** — cars needed so that at most 10% wait more than 30 ticks: etd 2, nearest_car 5, round_robin 5.

| cars | etd | nearest_car | round_robin |
|---:|---:|---:|---:|
| 2 | 12.0 ± 1.5 (3%) | 20.0 ± 2.4 (36%) | 18.8 ± 1.0 (21%) |
| 3 | 7.3 ± 0.5 (0%) | 14.2 ± 0.2 (22%) | 17.0 ± 1.1 (15%) |
| 4 | 6.7 ± 0.5 (0%) | 11.1 ± 1.1 (12%) | 15.0 ± 0.7 (11%) |
| 5 | 6.1 ± 0.7 (0%) | 8.0 ± 0.6 (4%) | 13.1 ± 0.6 (7%) |
| 6 | 6.0 ± 0.5 (0%) | 8.1 ± 0.5 (5%) | 11.9 ± 0.6 (4%) |
| 7 | 5.9 ± 0.7 (0%) | 7.2 ± 0.6 (1%) | 10.9 ± 0.7 (3%) |
| 8 | 5.8 ± 0.5 (0%) | 6.7 ± 0.5 (1%) | 10.0 ± 0.3 (2%) |

**tall_building** — cars needed so that at most 10% wait more than 30 ticks: etd 9, nearest_car > 10, round_robin > 10.

| cars | etd | nearest_car | round_robin |
|---:|---:|---:|---:|
| 3 | 108.1 ± 14.0 (79%) | 152.9 ± 36.5 (79%) | 133.9 ± 14.8 (88%) |
| 4 | 58.8 ± 11.3 (67%) | 109.9 ± 28.7 (69%) | 87.1 ± 14.7 (84%) |
| 5 | 38.6 ± 11.1 (58%) | 74.2 ± 18.0 (57%) | 64.7 ± 6.4 (79%) |
| 6 | 22.8 ± 7.2 (30%) | 59.6 ± 10.2 (51%) | 52.0 ± 3.6 (70%) |
| 7 | 16.7 ± 5.2 (14%) | 49.5 ± 9.9 (46%) | 48.8 ± 2.4 (68%) |
| 8 | 13.8 ± 3.8 (11%) | 38.0 ± 5.9 (39%) | 46.3 ± 1.1 (66%) |
| 9 | 10.3 ± 1.1 (3%) | 34.4 ± 4.7 (37%) | 45.9 ± 1.2 (63%) |
| 10 | 10.0 ± 1.5 (3%) | 31.9 ± 5.5 (35%) | 45.6 ± 1.9 (65%) |

## Resilience — 30 people at floor 14 at tick 200 on the morning up-peak, across seeds

| rule | peak backlog | ticks to recover | avg wait of the burst |
|---|---:|---:|---:|
| etd | 35.2 ± 3.6 | 25.6 ± 8.0 | 13.1 ± 2.8 |
| nearest_car | 35.4 ± 2.5 | 122.8 ± 22.5 | 56.9 ± 9.4 |
| round_robin | 36.8 ± 4.7 | 39.6 ± 16.0 | 16.9 ± 4.2 |

## Office day — average wait by time of day, across seeds

Schedule for "park by time of day": tick 0 → floor 1, tick 300 → floor 10, tick 600 → floor 1, tick 900 → floor 10, tick 1200 → floor 16.

| variant | whole day | morning | midmorning | lunch | afternoon | evening | floors/pax |
|---|---:|---:|---:|---:|---:|---:|---:|
| etd | 5.4 ± 0.4 | 6.1 ± 1.2 | 4.0 ± 0.6 | 4.5 ± 0.4 | 2.9 ± 0.7 | 6.8 ± 0.4 | 7.9 |
| nearest_car | 9.0 ± 0.7 | 10.8 ± 1.6 | 4.5 ± 1.4 | 8.6 ± 1.8 | 4.1 ± 0.9 | 10.6 ± 1.1 | 9.5 |
| round_robin | 13.9 ± 0.7 | 14.7 ± 1.6 | 8.6 ± 0.6 | 15.2 ± 1.5 | 8.3 ± 1.1 | 15.1 ± 1.2 | 10.8 |
| etd + park lobby all day | 5.5 ± 0.4 | 4.3 ± 0.9 | 6.0 ± 1.1 | 4.5 ± 0.5 | 6.1 ± 1.9 | 7.2 ± 0.6 | 10.2 |
| etd + park by time of day | 4.8 ± 0.4 | 4.3 ± 0.9 | 4.6 ± 0.5 | 4.7 ± 1.0 | 4.4 ± 0.4 | 5.6 ± 1.0 | 10.7 |
