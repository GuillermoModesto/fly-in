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


def assign_paths(
	network: Network, paths: list[list[Zone]]
) -> list[list[Zone]]:
	"""Assign one path to each drone by round-robin across the found paths."""
	return [paths[i % len(paths)] for i in range(network.nb_drones)]


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
