import heapq
from itertools import count

from connection import Connection
from network import Network
from zone import Zone
from zonetype import ZoneType

# A path's cost: (total turns, number of non-priority zones entered).
# Compared turns-first, so priority zones only ever break ties between paths of
# equal turn cost. Lower is better on both elements.
Cost = tuple[int, int]


class Pathfinder:
	"""Finds least-cost paths through a Network.

	Cost is measured in simulation turns (restricted zones cost 2, everything
	else 1). Among paths of equal turn cost, those through more priority zones
	are preferred, via the second element of the cost tuple.
	"""

	def __init__(self, network: Network) -> None:
		self.network = network

	# --- public API ---------------------------------------------------------

	def shortest_path(self) -> tuple[list[Zone], Cost] | None:
		"""Return the single least-cost path from start to end and its cost.

		Returns None if the end is unreachable. Ignores capacity: this is the
		plain cheapest route.
		"""
		zone_cap, link_cap = self._unlimited_capacity()
		return self._search(zone_cap, link_cap)

	def find_paths(self) -> list[list[Zone]]:
		"""Find a set of paths that can run in parallel within all capacities.

		Repeatedly takes the cheapest remaining path; each path consumes one unit
		of capacity from every interior zone and every connection it uses. A zone
		or connection stops being available once its remaining capacity reaches
		zero. Because each path carries drones single-file, one path needs exactly
		one unit of each resource, so the returned paths are collectively safe to
		simulate at once. Paths come out cheapest-first.
		"""
		zone_cap, link_cap = self._real_capacity()
		paths: list[list[Zone]] = []
		while True:
			result = self._search(zone_cap, link_cap)
			if result is None:
				break
			path, _cost = result
			paths.append(path)
			self._consume(path, zone_cap, link_cap)
		return paths

	# --- capacity bookkeeping ----------------------------------------------

	def _real_capacity(self) -> tuple[dict[str, int], dict[int, int]]:
		"""Remaining-capacity dicts initialised from the map's real limits.

		Start and end are given effectively unlimited capacity, matching their
		special "no capacity limit" status.
		"""
		big = self.network.nb_drones + 1
		zone_cap: dict[str, int] = {}
		for name, zone in self.network.zones.items():
			if zone is self.network.start or zone is self.network.end:
				zone_cap[name] = big
			else:
				zone_cap[name] = zone.max_drones
		link_cap: dict[int, int] = {
			id(c): c.max_link_capacity for c in self.network.connections
		}
		return zone_cap, link_cap

	def _unlimited_capacity(self) -> tuple[dict[str, int], dict[int, int]]:
		"""Remaining-capacity dicts large enough to never constrain a search."""
		big = self.network.nb_drones + 1
		zone_cap = {name: big for name in self.network.zones}
		link_cap = {id(c): big for c in self.network.connections}
		return zone_cap, link_cap

	def _consume(
		self, path: list[Zone], zone_cap: dict[str, int], link_cap: dict[int, int]
	) -> None:
		"""Decrement remaining capacity for one path's interior zones and links."""
		for zone in path[1:-1]:
			zone_cap[zone.name] -= 1
		for a, b in zip(path, path[1:]):
			connection = self._connection_between(a, b)
			link_cap[id(connection)] -= 1

	# --- core search --------------------------------------------------------

	def _search(
		self, zone_cap: dict[str, int], link_cap: dict[int, int]
	) -> tuple[list[Zone], Cost] | None:
		"""Dijkstra from start to end, honouring remaining zone/link capacity."""
		start = self.network.start
		end = self.network.end
		if start is None or end is None:
			return None

		counter = count()  # unique tie-breaker so the heap never compares Zones
		best: dict[str, Cost] = {start.name: (0, 0)}
		came_from: dict[str, Zone] = {}
		heap: list[tuple[Cost, int, Zone]] = [((0, 0), next(counter), start)]

		while heap:
			cost_so_far, _, zone = heapq.heappop(heap)
			if cost_so_far > best.get(zone.name, cost_so_far):
				continue  # stale, superseded entry
			if zone is end:
				return self._rebuild(came_from, end), cost_so_far

			for neighbour, connection in self._neighbours(zone):
				if link_cap[id(connection)] < 1:
					continue
				if neighbour is not end and zone_cap[neighbour.name] < 1:
					continue
				step = self._entry_cost(neighbour)
				new_cost = (cost_so_far[0] + step[0], cost_so_far[1] + step[1])
				known = best.get(neighbour.name)
				if known is None or new_cost < known:
					best[neighbour.name] = new_cost
					came_from[neighbour.name] = zone
					heapq.heappush(heap, (new_cost, next(counter), neighbour))

		return None

	def _neighbours(self, zone: Zone) -> list[tuple[Zone, Connection]]:
		"""Each (neighbour, connection) reachable from `zone`, skipping blocked."""
		result: list[tuple[Zone, Connection]] = []
		for connection in self.network.connections:
			if not connection.connects(zone):
				continue
			neighbour = connection.other(zone)
			if neighbour.zone_type is ZoneType.BLOCKED:
				continue
			result.append((neighbour, connection))
		return result

	def _entry_cost(self, zone: Zone) -> Cost:
		"""The cost of moving *into* `zone`: (turn cost, 0 if priority else 1)."""
		turns = zone.zone_type.movement_cost()
		non_priority = 0 if zone.zone_type is ZoneType.PRIORITY else 1
		return (turns, non_priority)

	def _connection_between(self, a: Zone, b: Zone) -> Connection:
		"""Find the connection linking two adjacent path zones."""
		for connection in self.network.connections:
			if connection.connects(a) and connection.other(a) is b:
				return connection
		raise ValueError(f"no connection between '{a.name}' and '{b.name}'")

	def _rebuild(self, came_from: dict[str, Zone], end: Zone) -> list[Zone]:
		"""Walk predecessor links backwards from end to reconstruct the path."""
		path: list[Zone] = [end]
		current = end
		while current.name in came_from:
			current = came_from[current.name]
			path.append(current)
		path.reverse()
		return path
