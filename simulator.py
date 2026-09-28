from connection import Connection
from drone import Drone
from network import Network
from zone import Zone
from zonetype import ZoneType


class Simulator:
	"""Runs drones along their assigned paths and records the moves.

	Each drone carries its own path from start to end. Drones are pipelined and
	may share zones/connections with other drones, so capacity is enforced
	globally each turn. Movement into a restricted zone takes two turns (one
	shown on the connection, arrival the next turn).
	"""

	def __init__(self, network: Network, paths: list[list[Zone]]) -> None:
		"""Build a simulator. `paths[i]` is the route for drone i+1.

		`paths` must have exactly network.nb_drones entries.
		"""
		self.network = network
		self.drones = [Drone(i + 1, paths[i]) for i in range(network.nb_drones)]

	def run(self) -> list[str]:
		"""Play the simulation to completion and return one output line per turn.

		Turns where nothing moves are not emitted. A safety cap prevents an
		impossible map from looping forever.
		"""
		lines: list[str] = []
		max_turns = self._turn_cap()
		turns = 0
		while not self._all_delivered() and turns < max_turns:
			moves = self._step()
			turns += 1
			if moves:
				lines.append(" ".join(moves))
		return lines

	def _all_delivered(self) -> bool:
		return all(d.delivered() for d in self.drones)

	def _step(self) -> list[str]:
		"""Advance the simulation by one turn, returning this turn's move tokens."""
		moves: list[str] = []
		occupancy = self._occupancy()
		link_usage: dict[int, int] = {}

		# Drones nearest their own end move first, so a vacated zone frees up for
		# a following drone within the same turn.
		order = sorted(
			(d for d in self.drones if not d.delivered()),
			key=lambda d: d.position,
			reverse=True,
		)

		for drone in order:
			if drone.in_transit:
				self._land(drone, moves)
			else:
				self._try_advance(drone, occupancy, link_usage, moves)

		return moves

	def _land(self, drone: Drone, moves: list[str]) -> None:
		"""Complete a restricted-zone arrival that was launched last turn."""
		assert drone.arriving_at is not None
		dest = drone.path[drone.arriving_at]
		drone.position = drone.arriving_at
		drone.arriving_at = None
		moves.append(f"D{drone.id}-{dest.name}")

	def _try_advance(
		self,
		drone: Drone,
		occupancy: dict[str, int],
		link_usage: dict[int, int],
		moves: list[str],
	) -> None:
		"""Move a resting drone one step forward if all constraints allow."""
		nxt = drone.position + 1
		if nxt > drone.end_index:
			return
		source = drone.path[drone.position]
		dest = drone.path[nxt]
		connection = self._connection_between(source, dest)

		if not self._can_enter(dest, occupancy, nxt == drone.end_index):
			return
		if not self._link_free(connection, link_usage):
			return

		# The drone leaves its source and claims the destination, in both the
		# live occupancy snapshot and the drone's own state.
		occupancy[source.name] = occupancy.get(source.name, 0) - 1
		occupancy[dest.name] = occupancy.get(dest.name, 0) + 1
		link_usage[id(connection)] = link_usage.get(id(connection), 0) + 1

		if dest.zone_type is ZoneType.RESTRICTED:
			# Two-turn move: shown on the connection now, lands next turn. The
			# drone already occupies (reserves) the destination via `arriving_at`.
			drone.arriving_at = nxt
			moves.append(f"D{drone.id}-{self._link_name(source, dest)}")
		else:
			drone.position = nxt
			moves.append(f"D{drone.id}-{dest.name}")

	def _occupancy(self) -> dict[str, int]:
		"""How many drones occupy each zone right now, by zone name (global)."""
		counts: dict[str, int] = {}
		for drone in self.drones:
			if drone.delivered():
				continue
			name = drone.current_zone().name
			counts[name] = counts.get(name, 0) + 1
		return counts

	def _can_enter(
		self, dest: Zone, occupancy: dict[str, int], is_end: bool
	) -> bool:
		"""Whether `dest` has room for one more drone this turn."""
		if is_end:
			return True  # end zone has unlimited capacity
		return not dest.is_full(occupancy.get(dest.name, 0))

	def _link_free(
		self, connection: Connection, link_usage: dict[int, int]
	) -> bool:
		"""Whether `connection` can carry one more drone this turn."""
		return link_usage.get(id(connection), 0) < connection.max_link_capacity

	def _connection_between(self, a: Zone, b: Zone) -> Connection:
		"""Find the connection linking two adjacent path zones."""
		for connection in self.network.connections:
			if connection.connects(a) and connection.other(a) is b:
				return connection
		raise ValueError(f"no connection between '{a.name}' and '{b.name}'")

	def _link_name(self, a: Zone, b: Zone) -> str:
		"""The name used in output for a move a->b: 'source-dest'."""
		return f"{a.name}-{b.name}"

	def _turn_cap(self) -> int:
		"""A generous safety cap so a bad map can never loop forever."""
		longest = max((len(d.path) for d in self.drones), default=1)
		return (longest + 2) * (self.network.nb_drones + 2) + 10
