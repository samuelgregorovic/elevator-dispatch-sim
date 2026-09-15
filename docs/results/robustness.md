# Seed robustness — 20 fresh seeds per pattern

Seeds 101 to 120, none of them the committed one. Mean ± standard deviation over seeds; ticks throughout. Regenerate with `uv run python scenarios/robustness.py`.

## Average wait per variant

| pattern | etd | nearest_car | nearest_car_balanced | round_robin | etd_f0.5 | etd lowest |
|---|---:|---:|---:|---:|---:|---:|
| morning_up_peak | 7.0 ± 0.5 | 10.7 ± 1.3 | 11.0 ± 1.5 | 15.1 ± 1.1 | 7.2 ± 0.7 | 20/20 |
| lunch_two_way | 4.7 ± 0.5 | 9.3 ± 1.4 | 9.0 ± 1.3 | 14.0 ± 1.1 | 5.0 ± 0.7 | 20/20 |
| evening_down_peak | 7.2 ± 0.9 | 10.9 ± 1.5 | 10.6 ± 1.4 | 15.5 ± 1.3 | 8.3 ± 1.2 | 20/20 |
| interfloor | 3.9 ± 0.4 | 4.8 ± 0.8 | 4.8 ± 0.6 | 8.2 ± 0.9 | 4.0 ± 0.4 | 19/20 |
| capacity_stress | 55.4 ± 20.5 | 61.4 ± 20.0 | 62.0 ± 19.3 | 59.4 ± 19.1 | 53.9 ± 19.7 | 12/20 |
| tall_building | 22.6 ± 4.6 | 57.3 ± 10.5 | 52.6 ± 9.0 | 51.8 ± 3.0 | 29.2 ± 7.0 | 20/20 |
| tall_lobby_traffic | 24.8 ± 6.0 | 60.4 ± 12.1 | 58.8 ± 9.3 | 51.5 ± 3.1 | 25.0 ± 4.7 | 20/20 |
| office_day | 5.7 ± 0.4 | 9.0 ± 0.9 | 9.3 ± 1.0 | 13.8 ± 0.8 | 6.4 ± 0.4 | 20/20 |

## Ratios of average wait to ETD

| pattern | nearest_car / etd | nearest_car_balanced / etd | round_robin / etd |
|---|---:|---:|---:|
| morning_up_peak | 1.54 ± 0.22 | 1.58 ± 0.21 | 2.16 ± 0.18 |
| lunch_two_way | 2.00 ± 0.33 | 1.94 ± 0.33 | 3.02 ± 0.39 |
| evening_down_peak | 1.54 ± 0.22 | 1.49 ± 0.20 | 2.18 ± 0.21 |
| interfloor | 1.23 ± 0.18 | 1.22 ± 0.15 | 2.11 ± 0.25 |
| capacity_stress | 1.15 ± 0.16 | 1.17 ± 0.22 | 1.11 ± 0.15 |
| tall_building | 2.62 ± 0.75 | 2.42 ± 0.70 | 2.37 ± 0.45 |
| tall_lobby_traffic | 2.51 ± 0.54 | 2.46 ± 0.56 | 2.18 ± 0.49 |
| office_day | 1.57 ± 0.19 | 1.63 ± 0.19 | 2.41 ± 0.20 |

## Fairness weight 0.5 against plain ETD (seeds out of 20 in which the weight …)

| pattern | lowers max wait | lowers p90 wait | raises avg wait | narrows busy spread |
|---|---:|---:|---:|---:|
| morning_up_peak | 5 | 3 | 12 | 11 |
| lunch_two_way | 8 | 5 | 12 | 11 |
| evening_down_peak | 4 | 1 | 18 | 12 |
| interfloor | 5 | 4 | 9 | 9 |
| capacity_stress | 14 | 14 | 3 | 14 |
| tall_building | 4 | 2 | 18 | 14 |
| tall_lobby_traffic | 3 | 8 | 10 | 15 |
| office_day | 5 | 1 | 20 | 15 |

## Policies

- Parking idle cars at the lobby (morning up-peak, ETD): average wait lower in 20/20 seeds; reduction 38.6 ± 11.6%.
- Zoning three local + three express cars (tall lobby traffic, ETD): average wait worse than six free cars in 11/20 seeds; zoned 24.4 ± 7.1 against free 24.8 ± 6.0.

## Maximum wait per variant

| pattern | etd | etd_f0.5 | nearest_car | round_robin |
|---|---:|---:|---:|---:|
| morning_up_peak | 19.9 ± 2.5 | 20.1 ± 3.0 | 42.0 ± 3.6 | 39.4 ± 1.9 |
| lunch_two_way | 21.4 ± 4.2 | 21.9 ± 4.4 | 41.0 ± 2.3 | 39.0 ± 2.1 |
| evening_down_peak | 25.6 ± 5.3 | 29.2 ± 5.5 | 48.8 ± 15.5 | 39.6 ± 2.2 |
| interfloor | 16.2 ± 2.2 | 15.7 ± 1.9 | 27.8 ± 5.7 | 25.9 ± 4.3 |
| capacity_stress | 117.1 ± 36.7 | 112.5 ± 34.3 | 144.6 ± 38.6 | 128.8 ± 37.4 |
| tall_building | 65.0 ± 13.2 | 74.5 ± 15.8 | 252.1 ± 84.5 | 141.8 ± 46.2 |
| tall_lobby_traffic | 58.5 ± 12.7 | 64.2 ± 8.8 | 248.7 ± 71.6 | 126.0 ± 13.7 |
| office_day | 26.4 ± 3.5 | 30.6 ± 5.3 | 44.4 ± 3.5 | 41.1 ± 1.3 |
