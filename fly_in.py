import sys

from checker import SimulationChecker
from network import Network
from parser import Parser
from parsererror import ParserError
from pathfinder import Pathfinder
from renderer import Renderer
from simulator import Simulator
from zone import Zone


def load_network(path: str) -> Network:
	"""Read and parse a map file at `path`, returning a validated Network."""
	with open(path, encoding="utf-8") as handle:
		text = handle.read()
	return Parser().parse(text)


<<<<<<< HEAD
def assign_paths(
	network: Network, paths: list[list[Zone]]
) -> list[list[Zone]]:
	"""Assign one path to each drone by round-robin across the found paths."""
	return [paths[i % len(paths)] for i in range(network.nb_drones)]
=======
def _path_turn_cost(path: list[Zone]) -> int:
	"""Turns a single drone needs to traverse `path` (sum of entry costs)."""
	return sum(zone.zone_type.movement_cost() for zone in path[1:])


def assign_paths(
	network: Network, paths: list[list[Zone]]
) -> list[list[Zone]]:
	"""Assign one path to each drone, balancing the load by path length.

	Drones are handed out one at a time to the path whose projected finish
	time -- its single-drone traversal cost plus the drones already queued on
	it -- is currently smallest. This beats naive round-robin when paths differ
	in length: a longer detour is only used once the short routes are saturated,
	which lowers the total turn count.
	"""
	if not paths:
		return []
	costs = [_path_turn_cost(path) for path in paths]
	queued = [0] * len(paths)
	assignment: list[list[Zone]] = []
	for _ in range(network.nb_drones):
		best = min(
			range(len(paths)), key=lambda i: costs[i] + queued[i]
		)
		queued[best] += 1
		assignment.append(paths[best])
	return assignment
>>>>>>> 45a99c5edc2fa3228068c074d2348e2b7d589709


def run_simulation(network: Network) -> list[str]:
	"""Find paths, assign drones, and simulate. Returns the turn lines.

	Returns an empty list if the end is unreachable.
	"""
	paths = Pathfinder(network).find_paths()
	if not paths:
		return []
	assignment = assign_paths(network, paths)
	return Simulator(network, assignment).run()


def parse_args(argv: list[str]) -> tuple[str, set[str]]:
	"""Split argv into (map_path, flags). Raises ValueError on bad usage."""
	flags = {a for a in argv[1:] if a.startswith("-")}
	files = [a for a in argv[1:] if not a.startswith("-")]
	known = {"--visual"}
	unknown = flags - known
	if unknown:
		raise ValueError(f"unknown option(s): {' '.join(sorted(unknown))}")
	if len(files) != 1:
		raise ValueError("expected exactly one map file")
	return files[0], flags


def main() -> int:
	"""Entry point: parse the map named on the command line and simulate it.

	Returns a process exit code: 0 on success, non-zero on any handled error.
	"""
	try:
		path, flags = parse_args(sys.argv)
	except ValueError as error:
		print(f"Usage: {sys.argv[0]} [--visual] <map_file>", file=sys.stderr)
		print(f"  {error}", file=sys.stderr)
		return 1

	try:
		network = load_network(path)
	except ParserError as error:
		print(f"Parse error: {error}", file=sys.stderr)
		return 1
	except OSError as error:
		reason = error.strerror or str(error)
		print(f"Could not read '{path}': {reason}", file=sys.stderr)
		return 1

	lines = run_simulation(network)
	if not lines:
		print(
			"No path from start to end: no drones can be delivered.",
			file=sys.stderr,
		)
		return 1

	# Verify our own output obeys every rule before showing anything.
	try:
		SimulationChecker(network).check(lines)
	except AssertionError as error:
		print(
			f"Internal error: produced an invalid simulation: {error}",
			file=sys.stderr,
		)
		return 1

	if "--visual" in flags:
		Renderer(network).render(lines)
	else:
		for line in lines:
			print(line)

	print(
		f"\nDelivered {network.nb_drones} drones in {len(lines)} turns.",
		file=sys.stderr,
	)
	return 0


if __name__ == "__main__":
	sys.exit(main())
