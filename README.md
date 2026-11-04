# Elevator_is_too_SLOW

*How long do people wait for a lift in a 20-floor building, and would dedicated lifts be faster?*

This project simulates a building's lifts second by second. It compares today's two-system layout with a proposed layout of dedicated lifts, and reports the average wait and trip time for every floor.

![Python 3](https://img.shields.io/badge/python-3-3776AB?logo=python&logoColor=white) ![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen) ![Discrete time](https://img.shields.io/badge/model-discrete--time-orange)

**Jump to:** [At a glance](#at-a-glance) · [The two layouts](#the-two-layouts) · [How the model works](#how-the-model-works) · [Results](#results) · [Findings](#findings) · [Sensitivity checks](#sensitivity-checks) · [Limitations](#limitations) · [Next steps](#next-steps) · [Running the simulation](#running-the-simulation)

---

## At a glance

> [!IMPORTANT]
> **The dedicated-lift layout is faster on average, but not everywhere.** It cuts the average trip from 29.1 s to 27.6 s and reduces trips over a minute from 7% to 3%. It is clearly worse for anyone going to **floor 1** (36.3 s against 27.7 s), and it struggles when many people call the same floor at once.

| Measure (4,000 people, 1 hour, seed 1) | Current | New | New − current |
|---|---:|---:|---:|
| Average wait | 11.3 s | 11.3 s | 0 s |
| **Average trip** | 29.1 s | **27.6 s** | **−1.5 s** |
| Average ride | 17.7 s | **16.3 s** | −1.4 s |
| Median trip | **23 s** | 25 s | +2 s |
| 90th-percentile trip | 56 s | **49 s** | −7 s |
| Trips over 60 s | 290 (7%) | **122 (3%)** | −168 |
| Ground → floors 2–20, average trip | 29.2 s | **26.7 s** | −2.5 s |
| Floors 2–20 → floor 1, average trip | **27.7 s** | 36.3 s | +8.6 s |
| Most people in one lift at once | 6 | 10 (the limit) | — |
| Requests that queued for a seat | 0 | 9 | — |
| Floors stopped per one-way run | 1.39 | 1.04 | — |

---

## The two layouts

Both layouts have the same 24 lifts, speed and capacity. They differ only in how the lifts are grouped.

| Floors | Current layout | New layout |
|---|---|---|
| 11–20 | System 2: 12 lifts in teams A and B | System A: 11 ground lifts + 1 between-floor lift |
| 2–10 | System 1: 12 lifts in teams A and B | System B: 10 ground lifts + 2 between-floor lifts |
| 1 and G | Both systems | Both systems |

- **Current:** a passenger is assigned a system by their floors, then a team (A or B) at random. The lift in that team with the fewest planned stops takes them.
- **New:** a ground trip goes to the **ground lift for its destination**, which serves only that floor. Trips that do not start on the ground floor use the between-floor lifts.

Lift names: `A-G1` and `A-G11` to `A-G20`, plus `B-G1` to `B-G10`, are ground lifts (`-G` plus the floor). `A-M1`, `B-M1` and `B-M2` are between-floor lifts (`-M`).

---

## How the model works

### Pipeline

Each tick of the simulator is one second:

```text
make_trips()          creates 4,000 passengers with random request times
Simulator.run()       repeats every second until everyone has arrived
  ├─ request()          a passenger presses a button and joins a queue
  ├─ assign_pending()   queued requests go to a lift with room
  └─ update(lift)       each lift moves, opens its doors, boards and unloads
```

### Traffic

| Share | Trips | From | To |
|---|---:|---|---|
| 90% ground trips | 3,600 | Ground floor | Floors 2–20, evenly spread (189 or 190 each) |
| 10% trips to floor 1 | 400 | Floors 2–20, evenly spread | Floor 1 |

Each passenger makes one trip, and request times are spread at random across the hour. Nobody travels from the ground floor to floor 1.

### Lift rules

| Rule | Setting |
|---|---|
| Travel | 1 s per floor |
| Doors | 5 s at every stop. Passengers board and leave while the doors are open |
| Capacity | 10 people, counting everyone assigned to the lift, including those still waiting to board |
| Direction | Keeps going while it has stops ahead, then reverses |
| Idle | Stays where it last stopped |

### Dispatch

**Current layout**

1. The floors set the system. In this traffic, exactly one system serves each trip.
2. The team is chosen at random, 50/50.
3. The lift in that team with room and the fewest *planned stops* takes the passenger. Planned stops are the distinct floors a lift still has to visit. Ties go to the nearest lift.
4. If no lift in the team has room, the request waits in that team's queue.

**New layout**

1. Ground trips go to the ground lift for their destination.
2. Trips to floor 1 from floors 2–10 use System B's between-floor lifts. Trips to floor 1 from floors 11–20 use System A's. Within that system, the lift with the fewest planned stops takes the passenger.
3. If that lift is full, the request waits in its queue.

### Measures

| Measure | Definition |
|---|---|
| **Wait** | From pressing the button until the doors open at the starting floor |
| **Trip time** | From pressing the button until the doors open at the destination. Trip time = wait + ride |
| **Floors per one-way run** | Floors where a lift opens its doors during one continuous run in one direction, not counting its starting floor. This is the "one-way trip" from the study brief |
| **Utilisation** | Share of time a lift is not idle |
| **Queued** | Requests that had to wait for a free seat |
| **Peak load** | The most people riding in one lift at the same moment |

As a worked example, a lone passenger going from the ground floor to floor 10 waits 0 s and rides 15 s: 5 s with the doors open at the ground floor, then 10 s of travel.

Random choices are the request times, origins, destinations and (current layout only) the team. Each run uses a fixed seed, so results are repeatable.

---

## Model checks

Lone passengers, checked by hand. The results are the same in both layouts.

| Trip | Hand calculation | Model |
|---|---|---:|
| Ground → 1 | 5 s doors + 1 floor | 6 s |
| Ground → 10 | 5 s doors + 10 floors | 15 s |
| Ground → 20 | 5 s doors + 20 floors | 25 s |
| 14 → 1 (lift starts at ground) | 14 s to reach floor 14 + 5 s doors + 13 floors | 32 s |

- **Capacity:** 130 people call floor 10 at once. No lift ever holds more than 10 in either layout.
- **Full runs:** all 4,000 passengers arrive, and trip time equals wait plus ride for every one of them. Current-layout lifts only carry passengers within their system's floors. Each new ground lift only carries passengers for its own floor.
- **Saved results:** both `results.csv` files match the live numbers.

---

## Results

Seed 1 unless stated. 4,000 people, requests spread over one hour.

### By zone

| Destination | Passengers | Current wait | Current trip | New wait | New trip |
|---|---:|---:|---:|---:|---:|
| Floors 2–10 (from ground) | 1,710 | 6.3 s | 17.7 s | 6.2 s | **16.8 s** |
| Floors 11–20 (from ground) | 1,890 | 16.2 s | 39.7 s | 15.4 s | **35.6 s** |
| Floor 1 (from floors 2–20) | 400 | 9.8 s | **27.7 s** | 13.7 s | 36.3 s |

### By floor

Bold marks the faster average trip on each floor.

| Floor | Passengers | Current wait | Current trip | New wait | New trip |
|---:|---:|---:|---:|---:|---:|
| 1 | 400 | 9.8 s | **27.7 s** | 13.7 s | 36.3 s |
| 2 | 190 | 5.6 s | 12.1 s | 2.3 s | **8.8 s** |
| 3 | 190 | 6.8 s | 14.5 s | 3.0 s | **10.4 s** |
| 4 | 190 | 6.0 s | 14.7 s | 4.1 s | **12.7 s** |
| 5 | 190 | 6.6 s | 16.6 s | 5.1 s | **14.7 s** |
| 6 | 190 | 6.3 s | 17.8 s | 5.9 s | **16.3 s** |
| 7 | 190 | 5.6 s | **18.2 s** | 8.0 s | 19.7 s |
| 8 | 190 | 6.6 s | **20.5 s** | 8.5 s | 21.1 s |
| 9 | 190 | 6.6 s | **22.0 s** | 9.0 s | 22.7 s |
| 10 | 190 | 6.5 s | **22.9 s** | 10.3 s | 24.9 s |
| 11 | 189 | 15.2 s | 30.3 s | 10.5 s | **26.2 s** |
| 12 | 189 | 15.8 s | 32.8 s | 13.0 s | **29.8 s** |
| 13 | 189 | 15.0 s | 34.0 s | 12.9 s | **30.6 s** |
| 14 | 189 | 16.0 s | 36.9 s | 14.3 s | **33.0 s** |
| 15 | 189 | 16.3 s | 38.4 s | 15.0 s | **34.7 s** |
| 16 | 189 | 15.8 s | 40.1 s | 16.3 s | **37.1 s** |
| 17 | 189 | 17.1 s | 43.2 s | 16.7 s | **38.5 s** |
| 18 | 189 | 16.7 s | 44.9 s | 16.6 s | **39.3 s** |
| 19 | 189 | 17.0 s | 47.1 s | 18.6 s | **42.4 s** |
| 20 | 189 | 17.3 s | 48.9 s | 19.8 s | **44.4 s** |

The new layout is faster on 15 of the 20 floors. The current layout is faster on floor 1 and on floors 7–10.

### Trip time by floor

Each block (█) is 2 seconds. Current is on the left, new on the right. Longer bar means longer trip.

```text
                            current│new
 1  27.7             ██████████████│██████████████████         36.3
 2  12.1                     ██████│████                       8.8
 3  14.5                    ███████│█████                      10.4
 4  14.7                    ███████│██████                     12.7
 5  16.6                   ████████│███████                    14.7
 6  17.8                  █████████│████████                   16.3
 7  18.2                  █████████│██████████                 19.7
 8  20.5                 ██████████│███████████                21.1
 9  22.0                ███████████│███████████                22.7
10  22.9                ███████████│████████████               24.9
11  30.3            ███████████████│█████████████              26.2
12  32.8           ████████████████│███████████████            29.8
13  34.0          █████████████████│███████████████            30.6
14  36.9         ██████████████████│█████████████████          33.0
15  38.4        ███████████████████│█████████████████          34.7
16  40.1       ████████████████████│███████████████████        37.1
17  43.2     ██████████████████████│███████████████████        38.5
18  44.9     ██████████████████████│████████████████████       39.3
19  47.1   ████████████████████████│█████████████████████      42.4
20  48.9   ████████████████████████│██████████████████████     44.4
```

---

## Findings

1. **The new layout is faster on average, and the gain is all ride time.** The average trip falls from 29.1 s to 27.6 s, about 5%. Waits are identical at 11.3 s, so the saving comes entirely from shorter rides (17.7 s down to 16.3 s).

2. **It has fewer very long trips.** 122 passengers (3%) take over a minute, against 290 (7%) in the current layout. The 90th-percentile trip is 49 s, against 56 s.

3. **The typical trip is slightly longer.** The median is 24–25 s across seeds in the new layout, against 23 s in the current one. The new layout shortens the long tail (finding 2) but makes the middle of the distribution a little slower. Floors 7–10 are 0.6 to 2.0 s slower in the new layout, for the reason in finding 5.

4. **Floor 1 is the new layout's weak spot.** Trips to floor 1 average 36.3 s, against 27.7 s. All 222 trips from floors 11–20 use System A's single between-floor lift (`A-M1`). That lift is 91% busy, and passengers wait 20 s on average for it. Meanwhile System B's two between-floor lifts are only 45% busy, and the two floor-1 ground lifts (`A-G1` and `B-G1`) carry nothing at all.

5. **In the new layout, the wait roughly equals the floor number.** Waits are 2.3 s for floor 2, 10.3 s for floor 10 and 19.8 s for floor 20. An idle dedicated lift stays where it last stopped, so it has to travel back down to the ground floor before it can collect the next passenger. In the current layout, any of six lifts in a team can answer a call. That keeps waits near 6 s on floors 2–10.

6. **Upper floors are the busiest part of the current layout.** System 2 lifts are 99% busy, against 80% for System 1. System 2 carries 2,112 passengers and System 1 carries 1,888. The slowest current trip is a ground trip to floor 19 that waits 57 s. Teams A and B carry almost identical loads in each system (System 1: 80.2% and 80.3%; System 2: 98.9% and 98.5%), so the random 50/50 team choice works well.

7. **At one hour, only the new layout hits the capacity limit.** The current layout's busiest lift carries 6 people. The new layout's busiest lift carries 10, and 9 requests wait for a seat.

8. **Dedicated lifts are fragile under surges.** When 130 people press floor 10 at once, the new layout's longest trip is 375 s, because one lift serves them all. The current layout's longest is 45 s, because the 12 lifts in System 1 share the load.

9. **The new layout cannot reach 4 floors per run.** Each dedicated lift serves one destination, so most runs have a single stop (1.04 on average). The current layout reaches 4 only when the window drops to about 15 minutes, and then more than 2,400 requests queue. Across every window tested, the new layout stays between 1.0 and 1.3.

---

## Sensitivity checks

### Shorter arrival windows

The same 4,000 people, squeezed into a shorter window:

| Window | Floors per run (current / new) | Average trip (current / new) | Queued (current / new) |
|---|---:|---:|---:|
| 60 min (base) | 1.39 / 1.04 | 29.1 / 27.6 s | 0 / 9 |
| 30 min | 2.43 / 1.07 | 40.5 / 30.5 s | 0 / 183 |
| 20 min | 3.55 / 1.11 | 78.5 / 39.5 s | 1,603 / 429 |
| 15 min | 4.07 / 1.17 | 155.3 / 54.9 s | 2,409 / 1,027 |
| 10 min | 4.16 / 1.22 | 289.4 / 98.1 s | 3,619 / 2,240 |
| 5 min | 4.16 / 1.26 | 429.6 / 202.1 s | 3,717 / 3,516 |

Only the current layout reaches 4 floors per run, and only at about 15 minutes or shorter. There, more than 2,000 requests queue and the average trip passes two minutes.

### Idle lifts return to the ground floor

The brief does not say where idle lifts wait, so the base model leaves them where they last stopped. Parking them at the ground floor is a useful test:

| Layout | Idle lifts | Average wait | Average trip |
|---|---|---:|---:|
| Current | stay where they stopped (base) | 11.3 s | 29.1 s |
| Current | return to the ground floor | 10.2 s | 28.0 s |
| New | stay where they stopped (base) | 11.3 s | 27.6 s |
| New | return to the ground floor | 10.0 s | 26.2 s |

Parking saves 1 to 1.5 s in both layouts, and the new layout still wins by 1.8 s.

---

## Limitations

- **Uniform arrivals over one hour.** Real buildings have much burstier peaks, so rush-hour queues would be worse. These results describe an average hour, not the busiest minute.
- **One seed in the tables.** Across seeds 1–5, the average trip is 28.9–29.4 s (current) and 27.0–27.6 s (new). The gap is at least 1.3 s in every pairing.
- **Idle lifts stay put by default.** The brief does not say where they wait. The parking test is in the sensitivity checks.
- **No breakdowns, door delays or acceleration.** Lifts move at a fixed 1 s per floor, and doors take a fixed 5 s.
- **Passengers never give up,** and nobody makes a second trip.
- **Team choice is random and ignores load,** as specified. It happened to balance well (finding 6).
- **Transfers are coded but unused.** A trip between floors 2–10 and floors 11–20 would transfer at floor 1. The current traffic never creates one.

---

## Next steps

1. **Give System A a second between-floor lift.** Reassign the idle `A-G1` lift. This should roughly halve the load on `A-M1`, which is 91% busy today. Not yet tested.
2. **Decide on parking.** Parking idle lifts at the ground floor saves about 1 s in both layouts (see Sensitivity checks).
3. **Test peak-hour traffic.** A morning burst from the ground floor would show how both layouts cope when demand is uneven over time.
4. **Test a breakdown.** In the new layout, a failed ground lift leaves its floor with no service at all. In the current layout, the other five lifts in that team keep serving the floors.

---

## Project structure

```text
Elevator_is_too_SLOW/
├── README.md
├── Current_System/
│   ├── lift_simulation.py     simulator for the current two-system layout
│   └── results.csv            per-floor results (4,000 people, 1 hour)
└── New_System/
    ├── lift_simulation.py     simulator for the dedicated-lift layout
    └── results.csv            per-floor results (same settings)
```

---

## Running the simulation

Requires Python 3 only (standard library). Tested with Python 3.12.

```bash
cd Current_System                           # or New_System
python3 lift_simulation.py                  # defaults: 4,000 people, 1 hour, seed 1
python3 lift_simulation.py --window 900     # same people in a 15-minute window
python3 lift_simulation.py --seed 3         # a different random seed
python3 lift_simulation.py --csv out.csv    # also save the per-floor table
```

| Option | Default | Meaning |
|---|---:|---|
| `--people` | 4000 | number of passengers |
| `--window` | 3600 | seconds over which requests arrive |
| `--floor-time` | 1 | seconds to travel one floor |
| `--dwell` | 5 | seconds the doors stay open at each stop |
| `--capacity` | 10 | maximum passengers assigned to one lift |
| `--seed` | 1 | random seed |
| `--csv` | none | write the per-floor table to a file |
