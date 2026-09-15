// Browser port of src/elevator_sim: the same tick order, LOOK movement, capacity,
// dwell and scheduler rules. tests/test_js_conformance.py runs this file with Node on
// every committed scenario and asserts the positions and events match the Python
// engine exactly, so the two implementations cannot drift apart silently.

export const UP = 1, IDLE = 0, DOWN = -1;

export class Passenger {
  constructor(id, requestTime, source, dest) {
    this.id = id; this.requestTime = requestTime; this.source = source; this.dest = dest;
    this.car = null; this.boardTime = null; this.alightTime = null;
  }
  get direction() { return this.dest > this.source ? UP : DOWN; }
  get wait() { return this.boardTime === null ? null : this.boardTime - this.requestTime; }
  get travel() { return this.alightTime === null ? null : this.alightTime - this.boardTime; }
  get total() { return this.alightTime === null ? null : this.alightTime - this.requestTime; }
  clone() { const p = new Passenger(this.id, this.requestTime, this.source, this.dest); p.car = this.car; p.boardTime = this.boardTime; p.alightTime = this.alightTime; return p; }
}

export class Elevator {
  constructor(index, floor, capacity, dwellTicks, servedFloors = null, parkFloor = null) {
    this.index = index; this.floor = floor; this.capacity = capacity; this.dwellTicks = dwellTicks;
    this.servedFloors = servedFloors; this.parkFloor = parkFloor;
    this.direction = IDLE; this.dwellRemaining = 0; this.aboard = []; this.waiting = [];
    this.stopsMade = 0; this.floorsTravelled = 0; this.stoppedHere = false;
  }
  serves(floor) { return this.servedFloors === null || this.servedFloors.has(floor); }
  get load() { return this.aboard.length; }
  get isIdle() { return this.aboard.length === 0 && this.waiting.length === 0; }
  get atRest() { return this.isIdle && this.dwellRemaining === 0 && (this.parkFloor === null || this.floor === this.parkFloor); }
  pendingStops() { const s = new Set(); for (const p of this.aboard) s.add(p.dest); for (const p of this.waiting) s.add(p.source); return s; }
  _nextDirection(stops) {
    let above = false, below = false;
    for (const f of stops) { if (f > this.floor) above = true; if (f < this.floor) below = true; }
    if (this.direction === UP && above) return UP;
    if (this.direction === DOWN && below) return DOWN;
    if (above) return UP;
    if (below) return DOWN;
    return IDLE;
  }
  departureDirection() {
    const ahead = new Set(); for (const f of this.pendingStops()) if (f !== this.floor) ahead.add(f);
    const here = this.waiting.filter(p => p.source === this.floor);
    let above = false, below = false;
    for (const f of ahead) { if (f > this.floor) above = true; if (f < this.floor) below = true; }
    const wants = new Set(here.map(p => p.direction));
    if (this.direction === UP && (above || wants.has(UP))) return UP;
    if (this.direction === DOWN && (below || wants.has(DOWN))) return DOWN;
    if (here.length) return here[0].direction;
    if (above) return UP;
    if (below) return DOWN;
    return IDLE;
  }
  move() {
    if (this.dwellRemaining > 0) {
      this.dwellRemaining -= 1;
      if (this.pendingStops().size === 0) this.direction = IDLE;
      return;
    }
    let direction = this._nextDirection(this.pendingStops());
    if (direction === IDLE && this.parkFloor !== null && this.parkFloor !== this.floor) direction = this.parkFloor > this.floor ? UP : DOWN;
    this.direction = direction;
    if (direction !== IDLE) { this.floor += direction; this.floorsTravelled += 1; }
    this.stoppedHere = false;
  }
  serveFloor(now) {
    const alighted = this.aboard.filter(p => p.dest === this.floor);
    if (alighted.length) { this.aboard = this.aboard.filter(p => p.dest !== this.floor); for (const p of alighted) p.alightTime = now; }
    let departure = this.departureDirection();
    const boarded = [];
    for (const p of this.waiting) {
      if (p.source !== this.floor || this.load >= this.capacity) continue;
      if (departure === IDLE) departure = p.direction;
      if (p.direction !== departure) continue;
      p.boardTime = now; this.aboard.push(p); boarded.push(p);
    }
    if (boarded.length) { const ids = new Set(boarded.map(p => p.id)); this.waiting = this.waiting.filter(p => !ids.has(p.id)); this.direction = departure; }
    if ((alighted.length || boarded.length) && !this.stoppedHere) { this.stoppedHere = true; this.stopsMade += 1; this.dwellRemaining = this.dwellTicks; }
    return [alighted, boarded];
  }
  clone() {
    const c = new Elevator(this.index, this.floor, this.capacity, this.dwellTicks, this.servedFloors, this.parkFloor);
    c.direction = this.direction; c.dwellRemaining = this.dwellRemaining; c.stopsMade = this.stopsMade; c.floorsTravelled = this.floorsTravelled; c.stoppedHere = this.stoppedHere;
    c.aboard = this.aboard.map(p => p.clone()); c.waiting = this.waiting.map(p => p.clone());
    return c;
  }
}

// ---- schedulers -------------------------------------------------------------

function feasible(request, cars) { return cars.filter(c => c.serves(request.source) && c.serves(request.dest)); }
function requireFeasible(request, cars) {
  const cs = feasible(request, cars);
  if (!cs.length) throw new Error(`request ${request.id}: no elevator serves both floor ${request.source} and floor ${request.dest}`);
  return cs;
}
const dirOf = (r) => (r.dest > r.source ? UP : DOWN);

export class NearestCar {
  constructor() { this.name = 'nearest_car'; }
  assign(request, cars) {
    let best = -1, bestCost = Infinity;
    for (const car of requireFeasible(request, cars)) {
      const distance = Math.abs(car.floor - request.source);
      const cost = approaching(car, request) ? distance : distance + 2 * span(cars);
      if (cost < bestCost) { best = car.index; bestCost = cost; }
    }
    return best;
  }
}
function approaching(car, request) {
  if (car.direction === IDLE) return true;
  const toward = (car.direction === UP && request.source >= car.floor) || (car.direction === DOWN && request.source <= car.floor);
  return toward && car.direction === dirOf(request);
}
function span(cars) {
  const stops = new Set(); for (const c of cars) { for (const f of c.pendingStops()) stops.add(f); stops.add(c.floor); }
  if (!stops.size) return 1;
  return Math.max(...stops) - Math.min(...stops) + 1;
}

export class RoundRobin {
  constructor() { this.name = 'round_robin'; this._next = 0; }
  assign(request, cars) {
    const cs = requireFeasible(request, cars);
    for (let i = 0; i < cars.length; i++) { const car = cars[this._next % cars.length]; this._next += 1; if (cs.includes(car)) return car.index; }
    return cs[0].index;
  }
}

export class ETD {
  constructor(fairness = 0) { this.fairness = fairness; this.name = fairness ? `etd_f${fairness}` : 'etd'; }
  assign(request, cars, now) {
    let best = -1, bestCost = Infinity;
    for (const car of requireFeasible(request, cars)) { const cost = this._cost(car, request, now); if (cost < bestCost) { best = car.index; bestCost = cost; } }
    return best;
  }
  _cost(car, request, now) {
    const candidate = car.clone();
    candidate.waiting.push(new Passenger(request.id, request.time, request.source, request.dest));
    const horizon = projectionHorizon(candidate, now);
    const before = project(car, now, horizon), after = project(candidate, now, horizon);
    let cost = after.get(request.id) - now;
    for (const p of [...car.aboard, ...car.waiting]) {
      const delay = after.get(p.id) - before.get(p.id);
      if (delay <= 0) continue;
      let weight = 1;
      if (this.fairness && p.boardTime === null) weight += this.fairness * (now - p.requestTime);
      cost += weight * delay;
    }
    return cost;
  }
}
export function projectionHorizon(car, now) {
  const stops = [car.floor, ...car.pendingStops(), ...car.waiting.map(p => p.dest)];
  const sp = Math.max(...stops) - Math.min(...stops) + 1;
  const n = car.aboard.length + car.waiting.length;
  return now + 2 * (n + 1) * (sp + (car.dwellTicks + 1) * (2 * n + 1)) + 4;
}
export function project(car, now, horizon = null) {
  const sim = car.clone();
  const ids = [...sim.aboard, ...sim.waiting].map(p => p.id);
  if (horizon === null) horizon = projectionHorizon(sim, now);
  const done = new Map();
  let t = now;
  while (done.size < ids.length && t <= horizon) {
    const [alighted] = sim.serveFloor(t);
    for (const p of alighted) done.set(p.id, t);
    sim.move();
    t += 1;
  }
  for (const id of ids) if (!done.has(id)) done.set(id, horizon);
  return done;
}
export function makeScheduler(name, fairness = 0) {
  if (name === 'etd') return new ETD(fairness);
  if (name === 'nearest_car') return new NearestCar();
  if (name === 'round_robin') return new RoundRobin();
  throw new Error(`unknown scheduler ${name}`);
}

// ---- simulation ---------------------------------------------------------------

export class Simulation {
  /** config: {elevators, floors, capacity, dwellTicks, startFloor, parkFloor, servedFloors: {index: Set}} */
  constructor(config, scheduler, requests = []) {
    this.config = { dwellTicks: 1, startFloor: 1, parkFloor: null, servedFloors: {}, ...config };
    this.scheduler = scheduler;
    this.pending = [...requests].sort((a, b) => a.time - b.time); // stable
    this.cursor = 0;
    this.cars = Array.from({ length: this.config.elevators }, (_, i) => new Elevator(i, this.config.startFloor, this.config.capacity, this.config.dwellTicks, this.config.servedFloors[i] ?? null, this.config.parkFloor));
    this.passengers = []; this.events = []; this.positions = []; this.carStates = [];
    this.now = 0; this.finished = false;
  }
  get ticks() { return this.positions.length; }
  get feedExhausted() { return this.cursor >= this.pending.length; }
  /** Inject a request at or after the current tick (interactive use). */
  addRequest(request) {
    if (request.time < this.now) request = { ...request, time: this.now };
    let i = this.pending.length;
    while (i > this.cursor && this.pending[i - 1].time > request.time) i--;
    this.pending.splice(i, 0, request);
    this.finished = false;
  }
  release(now) { const out = []; while (this.cursor < this.pending.length && this.pending[this.cursor].time <= now) out.push(this.pending[this.cursor++]); return out; }
  /** Run one tick (state at this.now), then advance. Returns true when complete at this tick. */
  step() {
    const now = this.now;
    for (const request of this.release(now)) {
      this.events.push({ t: now, type: 'request', id: request.id, floor: request.source, dest: request.dest });
      const p = new Passenger(request.id, request.time, request.source, request.dest);
      const idx = this.scheduler.assign(request, this.cars, now);
      const car = this.cars[idx];
      if (!car || !(car.serves(request.source) && car.serves(request.dest))) throw new Error(`scheduler ${this.scheduler.name} assigned ${request.id} to an infeasible car`);
      p.car = car.index; car.waiting.push(p); this.passengers.push(p);
      this.events.push({ t: now, type: 'assign', id: request.id, car: car.index });
    }
    for (const car of this.cars) {
      const [alighted, boarded] = car.serveFloor(now);
      for (const p of alighted) this.events.push({ t: now, type: 'alight', id: p.id, car: car.index, floor: car.floor });
      for (const p of boarded) this.events.push({ t: now, type: 'board', id: p.id, car: car.index, floor: car.floor });
    }
    this.positions.push(this.cars.map(c => c.floor));
    this.carStates.push(this.cars.map(c => ({ floor: c.floor, dir: c.direction, load: c.load, dwell: c.dwellRemaining, waiting: c.waiting.length })));
    if (this.feedExhausted && this.cars.every(c => c.atRest)) { this.finished = true; return true; }
    for (const car of this.cars) car.move();
    this.now += 1;
    return false;
  }
  run(maxTicks = 1_000_000) { while (!this.step()) if (this.now > maxTicks) throw new Error(`did not finish within ${maxTicks} ticks`); return this; }
}

// ---- input and metrics -----------------------------------------------------------

export function parseCsv(text, floors) {
  const lines = text.replace(/^﻿/, '').split(/\r?\n/).filter(l => l.trim().length);
  if (!lines.length) return [];
  const header = lines[0].split(',').map(s => s.trim());
  const col = {}; header.forEach((h, i) => { col[h] = i; });
  for (const k of ['time', 'id', 'source', 'dest']) if (!(k in col)) throw new Error(`missing column '${k}'`);
  const out = [], seen = new Set();
  lines.slice(1).forEach((line, i) => {
    const cells = line.split(',').map(s => s.trim());
    const n = i + 2;
    if (cells.length < 4) throw new Error(`line ${n}: expected 4 fields (time,id,source,dest)`);
    const time = Number(cells[col.time]), source = Number(cells[col.source]), dest = Number(cells[col.dest]), id = cells[col.id];
    if (![time, source, dest].every(Number.isInteger)) throw new Error(`line ${n}: time, source and dest must be integers`);
    if (!id) throw new Error(`line ${n}: empty id`);
    if (time < 0) throw new Error(`request ${id}: negative time ${time}`);
    if (source === dest) throw new Error(`request ${id}: source and dest are both ${source}`);
    if (source < 1 || source > floors) throw new Error(`request ${id}: source floor ${source} outside 1..${floors}`);
    if (dest < 1 || dest > floors) throw new Error(`request ${id}: dest floor ${dest} outside 1..${floors}`);
    if (seen.has(id)) throw new Error(`duplicate passenger id ${id}`);
    seen.add(id);
    out.push({ time, id, source, dest });
  });
  return out;
}

export function percentile(sorted, pct) {
  if (!sorted.length) return 0;
  const rank = Math.max(1, Math.ceil(pct / 100 * sorted.length));
  return sorted[Math.min(rank, sorted.length) - 1];
}
export function distribution(values) {
  if (!values.length) return { count: 0, min: 0, max: 0, mean: 0, p50: 0, p90: 0 };
  const s = [...values].sort((a, b) => a - b);
  return { count: s.length, min: s[0], max: s[s.length - 1], mean: s.reduce((a, b) => a + b, 0) / s.length, p50: percentile(s, 50), p90: percentile(s, 90) };
}
export function summarize(sim) {
  const served = sim.passengers.filter(p => p.alightTime !== null);
  return {
    scheduler: sim.scheduler.name, passengers: sim.passengers.length, ticks: sim.ticks,
    wait: distribution(served.map(p => p.wait)), travel: distribution(served.map(p => p.travel)), total: distribution(served.map(p => p.total)),
  };
}

// ---- seeded traffic generator (mirrors scenarios/generate.py shapes, not its seeds) ----

export function mulberry32(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
export function poisson(rng, lam) { if (lam <= 0) return 0; const limit = Math.exp(-lam); let k = 0, p = 1; for (;;) { p *= rng(); if (p <= limit) return k; k += 1; } }
export const PATTERNS = {
  morning: { label: 'Morning rush', mix: [0.85, 0.10, 0.05] },
  lunch: { label: 'Lunch hour', mix: [0.45, 0.45, 0.10] },
  evening: { label: 'Evening exit', mix: [0.10, 0.85, 0.05] },
  interfloor: { label: 'Interfloor', mix: [0.0, 0.0, 1.0] },
};
export function makeTrip(rng, floors, mix) {
  const [up, down] = mix; const r = rng();
  const upper = () => 2 + Math.floor(rng() * (floors - 1));
  if (r < up) return [1, upper()];
  if (r < up + down) return [upper(), 1];
  const s = upper(); let d = upper(); while (d === s) d = upper();
  return [s, d];
}

/** Generate `people` requests for any building from a pattern's directional mix and arrival rate. Seeded. */
export function generateTraffic({ floors, people, mix, rate, seed = 1 }) {
  const rng = mulberry32(seed);
  const out = [];
  let tick = 0;
  while (out.length < people) {
    const n = poisson(rng, rate);
    for (let k = 0; k < n && out.length < people; k++) {
      const [source, dest] = makeTrip(rng, floors, mix);
      out.push({ time: tick, id: `p${String(out.length + 1).padStart(4, '0')}`, source, dest });
    }
    tick += 1;
  }
  return out;
}
