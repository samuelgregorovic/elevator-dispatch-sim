"""The browser engine (docs/viewer/engine.js) must produce exactly what the Python engine does.

Runs the JavaScript port with Node on every committed scenario and every scheduler and
compares positions, events and passenger lifecycles field by field. Skipped when Node
is not installed; CI installs it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from elevator_sim.compare import Variant, load_manifest
from elevator_sim.io import read_requests
from elevator_sim.metrics import car_usage, efficiency, service
from elevator_sim.schedulers import make_scheduler
from elevator_sim.simulation import Simulation

ROOT = Path(__file__).parent.parent
ENGINE = ROOT / "docs" / "viewer" / "conform.mjs"
NODE = shutil.which("node")

VARIANTS = [
    Variant("etd"),
    Variant("nearest_car"),
    Variant("nearest_car_balanced"),
    Variant("round_robin"),
    Variant("etd", 0.5),
]


def run_js(csv: Path, config, variant: Variant) -> dict:
    cfg = {
        "elevators": config.elevators,
        "floors": config.floors,
        "capacity": config.capacity,
        "dwell_ticks": config.dwell_ticks,
        "start_floor": config.start_floor,
        "park_floor": config.park_floor,
        "park_schedule": [list(e) for e in config.park_schedule],
        "served_floors": {str(k): sorted(v) for k, v in config.served_floors.items()},
    }
    out = subprocess.run(
        [NODE, str(ENGINE), str(csv), json.dumps(cfg), variant.scheduler, str(variant.fairness)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(out.stdout)


@pytest.mark.skipif(NODE is None, reason="node not installed")
@pytest.mark.parametrize(
    "scenario", load_manifest(ROOT / "scenarios" / "manifest.json"), ids=lambda s: s.name
)
@pytest.mark.parametrize("variant", VARIANTS, ids=lambda v: v.label)
def test_js_engine_matches_python(scenario, variant):
    config = scenario.config(1)
    requests = read_requests(scenario.file, scenario.floors)
    py = Simulation(
        config, make_scheduler(variant.scheduler, fairness=variant.fairness), requests
    ).run()
    js = run_js(scenario.file, config, variant)

    assert js["positions"] == py.positions
    assert js["events"] == py.events
    py_passengers = [
        {
            "id": p.id,
            "t": p.request_time,
            "source": p.source,
            "dest": p.dest,
            "car": p.car,
            "board": p.board_time,
            "alight": p.alight_time,
        }
        for p in py.passengers
    ]
    assert js["passengers"] == py_passengers
    py_cars = [
        {
            "car": c.car,
            "carried": c.carried,
            "stops": c.stops,
            "floors_travelled": c.floors_travelled,
            "busy_ticks": c.busy_ticks,
        }
        for c in car_usage(py)
    ]
    assert js["cars"] == py_cars
    assert js["service_over"] == service(py).over
    served = [p for p in py.passengers if p.alight_time is not None]
    assert js["intermediate_stops"] == round(
        efficiency(py, car_usage(py)).stops_per_trip * len(served)
    )
