"""Discrete-time simulation of the lift layout with dedicated ground-trip lifts.

Floors: 0 is the ground floor, 1-20 are the upper floors.
System A serves floors 0, 1 and 11-20. It has 11 lifts, each carrying ground trips to one of its
destinations (1 and 11-20), plus 1 lift for trips between floors.
System B serves floors 0-10. It has 10 lifts, each carrying ground trips to one of its destinations
(1-10), plus 2 lifts for trips between floors.
A passenger going from the ground floor to floor 1 picks System A or B (50/50).
Trips between floors 2-10 and 11-20 transfer at floor 1.
A lift holds at most --capacity people, counting passengers assigned to it including those not yet picked up.
A request waits in a queue until its lift (or one of the system's between-floor lifts) has room.
Between-floor requests go to the system's between-floor lift with the fewest planned stops; ties go to the nearest lift.
"""

import argparse
import csv
import random
from collections import deque

SYSTEMS = {
    "A": {
        "floors": {0, 1} | set(range(11, 21)),
        "ground_destinations": [1] + list(range(11, 21)),
        "between_lifts": 1,
    },
    "B": {
        "floors": set(range(0, 11)),
        "ground_destinations": list(range(1, 11)),
        "between_lifts": 2,
    },
}
TRANSFER_FLOOR = 1


class Trip:
    def __init__(self, origin, final_dest, route):
        self.origin = origin
        self.final_dest = final_dest
        self.route = route
        self.request_time = 0
        self.wait = 0
        self.ride = 0
        self.arrival_time = None

    @property
    def trip_time(self):
        return self.arrival_time - self.request_time


class Leg:
    def __init__(self, trip, origin, dest):
        self.trip = trip
        self.origin = origin
        self.dest = dest
        self.request_time = 0
        self.board_time = 0
        self.status = "waiting"


class Lift:
    def __init__(self, name, system, pool):
        self.name = name
        self.system = system
        self.pool = pool
        self.floor = 0
        self.direction = 0
        self.state = "idle"
        self.next_floor = 0
        self.timer = 0
        self.legs = []
        self.run_stops = 0

    def stops(self):
        return {leg.origin if leg.status == "waiting" else leg.dest for leg in self.legs}

    def planned_stops(self):
        floors = {leg.dest for leg in self.legs}
        floors |= {leg.origin for leg in self.legs if leg.status == "waiting"}
        return len(floors)


def make_route(origin, dest):
    if any(origin in spec["floors"] and dest in spec["floors"] for spec in SYSTEMS.values()):
        return [(origin, dest)]
    return [(origin, TRANSFER_FLOOR), (TRANSFER_FLOOR, dest)]


class Simulator:
    def __init__(self, rng, floor_time, dwell, capacity):
        self.rng = rng
        self.floor_time = floor_time
        self.dwell = dwell
        self.capacity = capacity
        self.t = 0
        self.peak_load = 0
        self.queued = 0
        self.run_stop_counts = []
        self.leg_waits = []
        self.lifts = []
        for system, spec in SYSTEMS.items():
            for floor in spec["ground_destinations"]:
                self.lifts.append(Lift(f"{system}-G{floor}", system, floor))
            for number in range(1, spec["between_lifts"] + 1):
                self.lifts.append(Lift(f"{system}-M{number}", system, "between"))
        self.queues = {(lift.system, lift.pool): deque() for lift in self.lifts}

    def run(self, trips):
        trips = sorted(trips, key=lambda trip: trip.request_time)
        i = 0
        while i < len(trips) or any(self.queues.values()) or any(lift.legs for lift in self.lifts):
            while i < len(trips) and trips[i].request_time <= self.t:
                trip = trips[i]
                i += 1
                origin, dest = trip.route.pop(0)
                self.request(Leg(trip, origin, dest))
            self.assign_pending()
            for lift in self.lifts:
                self.update(lift)
            self.t += 1

    def request(self, leg):
        leg.request_time = self.t
        if leg.origin == 0:
            systems = [name for name, spec in SYSTEMS.items() if leg.dest in spec["ground_destinations"]]
            pool = leg.dest
        else:
            systems = [name for name, spec in SYSTEMS.items()
                       if leg.origin in spec["floors"] and leg.dest in spec["floors"]]
            pool = "between"
        system = self.rng.choice(systems)
        self.queues[(system, pool)].append(leg)

    def assign_pending(self):
        for (system, pool), queue in self.queues.items():
            if not queue:
                continue
            candidates = [lift for lift in self.lifts if lift.system == system and lift.pool == pool]
            while queue:
                open_lifts = [lift for lift in candidates if len(lift.legs) < self.capacity]
                if not open_lifts:
                    break
                leg = queue.popleft()
                if self.t > leg.request_time:
                    self.queued += 1
                lift = min(open_lifts, key=lambda c: (c.planned_stops(), abs(c.floor - leg.origin), c.name))
                lift.legs.append(leg)

    def update(self, lift):
        if lift.state == "moving" and self.t >= lift.timer:
            lift.floor = lift.next_floor
            self.arrive(lift)
        elif lift.state == "dwelling":
            self.serve(lift)
            if self.t >= lift.timer:
                self.move_on(lift)
        elif lift.state == "idle" and lift.stops():
            self.arrive(lift)

    def arrive(self, lift):
        if lift.floor in lift.stops():
            self.serve(lift)
            if lift.direction:
                lift.run_stops += 1
            lift.state = "dwelling"
            lift.timer = self.t + self.dwell
        else:
            self.move_on(lift)

    def move_on(self, lift):
        stops = lift.stops()
        if not stops:
            self.record_run(lift)
            lift.state = "idle"
            lift.direction = 0
            return
        direction = lift.direction
        if direction == 0:
            nearest = min(stops, key=lambda f: (abs(f - lift.floor), f))
            direction = 1 if nearest > lift.floor else -1
        elif direction == 1 and not any(f > lift.floor for f in stops):
            direction = -1
        elif direction == -1 and not any(f < lift.floor for f in stops):
            direction = 1
        if direction != lift.direction:
            self.record_run(lift)
            lift.direction = direction
        lift.next_floor = lift.floor + direction
        lift.state = "moving"
        lift.timer = self.t + self.floor_time

    def record_run(self, lift):
        if lift.direction:
            self.run_stop_counts.append(lift.run_stops)
        lift.run_stops = 0

    def serve(self, lift):
        for leg in [leg for leg in lift.legs if leg.status == "onboard" and leg.dest == lift.floor]:
            lift.legs.remove(leg)
            trip = leg.trip
            trip.ride += self.t - leg.board_time
            if trip.route:
                origin, dest = trip.route.pop(0)
                self.request(Leg(trip, origin, dest))
            else:
                trip.arrival_time = self.t
        self.assign_pending()
        for leg in lift.legs:
            if leg.status == "waiting" and leg.origin == lift.floor:
                leg.status = "onboard"
                leg.board_time = self.t
                leg.trip.wait += self.t - leg.request_time
                self.leg_waits.append((lift.system, lift.pool, self.t - leg.request_time))
        self.peak_load = max(self.peak_load, sum(leg.status == "onboard" for leg in lift.legs))


def make_trips(rng, people, window):
    ground_count = round(people * 0.9)
    destinations = [2 + i % 19 for i in range(ground_count)]
    rng.shuffle(destinations)
    pairs = [(0, dest) for dest in destinations]
    for _ in range(people - ground_count):
        pairs.append((rng.randint(2, 20), 1))
    trips = []
    for origin, dest in pairs:
        trip = Trip(origin, dest, make_route(origin, dest))
        trip.request_time = rng.randrange(window)
        trips.append(trip)
    return trips


def average(values):
    return sum(values) / len(values) if values else 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--people", type=int, default=4000)
    parser.add_argument("--window", type=int, default=3600, help="seconds over which requests arrive")
    parser.add_argument("--floor-time", type=int, default=1, help="seconds to travel one floor")
    parser.add_argument("--dwell", type=int, default=5, help="seconds doors stay open at each stop")
    parser.add_argument("--capacity", type=int, default=10, help="maximum people per lift")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--csv", help="write per-floor results to this file")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    trips = make_trips(rng, args.people, args.window)
    sim = Simulator(rng, args.floor_time, args.dwell, args.capacity)
    sim.run(trips)

    rows = []
    for floor in range(1, 21):
        arriving = [t for t in trips if t.final_dest == floor]
        rows.append({
            "floor": floor,
            "trips": len(arriving),
            "avg_wait_s": round(average([t.wait for t in arriving]), 1),
            "avg_trip_s": round(average([t.trip_time for t in arriving]), 1),
        })

    print(f"{args.people} people, requests over {args.window} s, {args.floor_time} s per floor, "
          f"{args.dwell} s per stop, capacity {args.capacity}, seed {args.seed}")
    print(f"{'Floor':>5} {'Trips':>6} {'Avg wait (s)':>13} {'Avg trip (s)':>13}")
    for row in rows:
        print(f"{row['floor']:>5} {row['trips']:>6} {row['avg_wait_s']:>13} {row['avg_trip_s']:>13}")
    print()
    groups = [
        ("Ground to floor", [t for t in trips if t.origin == 0]),
        ("Between floors", [t for t in trips if t.origin != 0]),
        ("All trips", trips),
    ]
    for label, group in groups:
        print(f"{label:<17} trips={len(group):<5} avg wait={average([t.wait for t in group]):.1f} s  avg trip={average([t.trip_time for t in group]):.1f} s")
    print()
    for system in SYSTEMS:
        ground_waits = [w for s, pool, w in sim.leg_waits if s == system and pool != "between"]
        between_waits = [w for s, pool, w in sim.leg_waits if s == system and pool == "between"]
        print(f"System {system} ground-trip lifts:    {len(ground_waits):>5} boardings, avg wait={average(ground_waits):.1f} s")
        print(f"System {system} between-floor lifts:  {len(between_waits):>5} boardings, avg wait={average(between_waits):.1f} s")
    print(f"Peak passengers in one lift: {sim.peak_load}")
    print(f"Lift requests that queued for a free seat: {sim.queued}")
    print(f"Average floors stopped at per one-way trip: {average(sim.run_stop_counts):.2f} ({len(sim.run_stop_counts)} one-way trips)")
    print(f"Last passenger arrived at {max(t.arrival_time for t in trips)} s")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
