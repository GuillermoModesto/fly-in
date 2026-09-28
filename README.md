*This project has been created as part of the 42 curriculum by guantino.*

# Fly-in

## Description

Fly-in is a drone routing simulator. Given a map file describing a network of
**zones** (nodes) linked by **connections** (edges), it routes a fleet of drones
from the single **start** zone to the single **end** zone in as few simulation
turns as possible, while respecting every movement and capacity rule.

The problem is solved in two stages:

1. **Pathfinding** — find a set of good routes through the graph, taking zone
   movement costs and capacities into account.
2. **Simulation** — march the drones along those routes turn by turn, never
   letting a zone or connection exceed its capacity, and print each turn's moves.

The project is written in plain Python with no third-party graph library: the
graph, Dijkstra search and simulation are all implemented from scratch, as the
subject requires. It is fully object-oriented and passes `flake8` and `mypy`.

### Zone types

| Type       | Cost to enter | Notes                                             |
|------------|---------------|---------------------------------------------------|
| normal     | 1 turn        | default                                           |
| priority   | 1 turn        | preferred by the pathfinder on equal-cost routes  |
| restricted | 2 turns       | one turn on the connection, arrival the next turn |
| blocked    | —             | can never be entered or crossed                   |

Start and end zones have unlimited capacity; every other zone holds at most
`max_drones` drones (default 1). Each connection carries at most
`max_link_capacity` drones per turn (default 1).

## Instructions

Requirements: **Python 3.10 or later** (the code uses `X | None` type syntax).

```bash
make install       # create a .venv and install flake8 + mypy
make run           # run on the default map (maps/01_linear_path.txt)
make run MAP=maps/02_simple_fork.txt      # run on another map
make visual MAP=maps/02_simple_fork.txt   # coloured turn-by-turn view
make debug         # run under pdb
make lint          # flake8 . and mypy . (with the subject's flags)
make lint-strict   # flake8 . and mypy . --strict
make clean         # remove caches
make fclean        # also remove the virtualenv
```

You can also run it directly without the Makefile:

```bash
python3 fly_in.py maps/01_linear_path.txt
python3 fly_in.py --visual maps/01_linear_path.txt
```

On success the program prints one line per turn to stdout and a short summary
(`Delivered N drones in T turns.`) to stderr. On any error it prints a clear
message (with a line number for parse errors) and exits with a non-zero code.

## Map file format

```
nb_drones: 5

start_hub: start 0 0 [color=green]
end_hub: goal 4 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: tunnel 2 0 [zone=restricted color=red]
connection: start-junction [max_link_capacity=2]
connection: junction-tunnel
```

- First line: `nb_drones: <positive integer>`.
- `start_hub:` / `end_hub:` / `hub:` define zones as `<name> <x> <y> [metadata]`.
- Zone names may not contain dashes or spaces.
- Metadata is optional, in any order: `zone=<type>`, `color=<word>`,
  `max_drones=<n>` (ignored on start/end).
- `connection: <name1>-<name2> [max_link_capacity=<n>]` links two existing zones.
- Lines starting with `#` are comments.

## Algorithm choices and implementation strategy

**Data model (object-oriented).** `Zone`, `Connection` and `Network` hold the
graph and enforce their own invariants by raising `ValueError`. The `Parser`
only reads text and tracks line numbers; it catches those `ValueError`s and
re-raises them as `ParserError` with the offending line, so the rules live in
one place and are not duplicated. `HubZone` (start/end/regular) and `ZoneType`
(normal/blocked/restricted/priority) are enums.

**Pathfinding (`Pathfinder`).** Because entering a restricted zone costs 2 turns,
edges are weighted, so a **Dijkstra** search is used rather than plain BFS. The
cost of a path is a tuple `(turns, non_priority_zones)`, compared turns-first, so
among equally fast routes the one through more priority zones wins. To route many
drones in parallel, `find_paths()` repeatedly takes the cheapest remaining route
and **consumes one unit of capacity** from each interior zone and connection it
uses; a route stops being available once a resource on it is exhausted. Since a
route carries drones single-file, one route needs exactly one unit of each
resource, so the returned routes are collectively safe to simulate at once.

**Drone assignment (`assign_paths` in `fly_in.py`).** Drones are distributed
round-robin across the found routes, so they queue single-file behind one another
on each route.

**Simulation (`Simulator`).** Each turn, active drones are advanced closest-to-end
first, so a zone freed by a leading drone can be reused by its follower in the
same turn. A drone entering a restricted zone spends one turn on the connection
(printed as `D<id>-<src>-<dst>`) and **must** land the next turn; it reserves its
destination up front so the landing is always legal. Zone and connection
capacities are checked against a live per-turn snapshot before every move.

**Self-checking (`SimulationChecker`).** After the simulation, an independent
checker replays the emitted lines from scratch and asserts every rule
(adjacency, capacities, restricted transits, all drones ending at the end zone).
It shares no logic with the simulator on purpose: if the two ever disagree, one
has a bug. The program refuses to print a trace that fails this check.

**Complexity.** One Dijkstra search is `O(E log V)`; `find_paths` runs at most a
bounded number of searches, and the simulation is `O(turns × drones)`. No path is
recomputed during simulation — routes are found once and cached in the drones.

## Visual representation

Running with `--visual` (`make visual`) replays the moves and prints a coloured
snapshot each turn: every occupied zone on its own line, coloured with the ANSI
code matching its `color=` metadata, followed by the drones currently in it
(in-transit drones are shown on their connection). This makes it easy to watch
the pipeline fill and drain, spot bottlenecks, and confirm capacities visually,
without touching the simulator itself — the renderer is a separate display layer
that works purely from the output lines.

## Example

Input (`maps/02_simple_fork.txt`), 4 drones over two routes:

```
nb_drones: 4
start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]
connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

Output:

```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

All four drones are delivered in 4 turns.

## Resources

- Dijkstra's shortest-path algorithm (weighted graphs).
- Maximum-flow / disjoint-paths intuition for routing multiple drones in
  parallel (the greedy capacity-consuming variant used here).
- `flake8` and `mypy` documentation for style and static typing.

### Use of AI

AI was used as a support tool for: brainstorming the module breakdown, reviewing
the code for edge cases, explaining the restricted-zone transit rule, and
drafting documentation.
