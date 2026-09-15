// Conformance runner used by tests/test_js_conformance.py:
//   node conform.mjs <requests.csv> '<config json>' <scheduler> [fairness]
// Prints JSON {positions, events, passengers, cars} in the same shape as the Python trace and summary.
import { readFileSync } from 'node:fs';
import { Simulation, makeScheduler, parseCsv, carUsage } from './engine.js';

const [, , csvPath, configJson, schedulerName, fairnessArg] = process.argv;
const cfg = JSON.parse(configJson);
const servedFloors = {};
for (const [k, v] of Object.entries(cfg.served_floors ?? {})) servedFloors[Number(k)] = new Set(v);
const config = {
  elevators: cfg.elevators, floors: cfg.floors, capacity: cfg.capacity,
  dwellTicks: cfg.dwell_ticks ?? 1, startFloor: cfg.start_floor ?? 1, parkFloor: cfg.park_floor ?? null, servedFloors,
};
const requests = parseCsv(readFileSync(csvPath, 'utf8'), config.floors);
const sim = new Simulation(config, makeScheduler(schedulerName, Number(fairnessArg ?? 0)), requests).run();
process.stdout.write(JSON.stringify({
  positions: sim.positions,
  events: sim.events,
  passengers: sim.passengers.map(p => ({ id: p.id, t: p.requestTime, source: p.source, dest: p.dest, car: p.car, board: p.boardTime, alight: p.alightTime })),
  cars: carUsage(sim).map(c => ({ car: c.car, carried: c.carried, stops: c.stops, floors_travelled: c.floors_travelled, busy_ticks: c.busy_ticks })),
}));
