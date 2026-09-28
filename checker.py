from network import Network
from zonetype import ZoneType


class SimulationChecker:
	"""Independently verifies a move trace against all simulation rules.

	Shares no logic with the Simulator: it replays the emitted lines from
	scratch and confirms every move is legal. If the Simulator and this checker
	disagree, one of them is wrong -- which is exactly what makes it useful.
	"""

	def __init__(self, network: Network) -> None:
		self.network = network
		self.zones = network.zones
		self.connections = {
			frozenset((c.zone1.name, c.zone2.name)): c
			for c in network.connections
		}

	def check(self, lines: list[str]) -> None:
		"""Replay `lines` and raise AssertionError on any rule violation."""
		start = self.network.start
		end = self.network.end
		assert start is not None and end is not None, "network missing start/end"

		# Every drone starts at the start zone. Track each drone's current zone
		# and whether it is mid-transit toward a restricted zone.
		positions: dict[str, str] = {
			f"D{i + 1}": start.name for i in range(self.network.nb_drones)
		}
		transiting: dict[str, str] = {}  # drone -> destination zone name

		for turn_no, line in enumerate(lines, start=1):
			tokens = line.split()
			link_usage: dict[frozenset[str], int] = {}
			seen_this_turn: set[str] = set()

			for token in tokens:
				drone, target = self._split_token(token, turn_no)
				assert drone in positions or drone in transiting, \
					f"turn {turn_no}: unknown {drone}"
				assert drone not in seen_this_turn, \
					f"turn {turn_no}: {drone} moved twice"
				seen_this_turn.add(drone)

				if drone in transiting:
					# Must be landing at its reserved restricted destination.
					dest = transiting[drone]
					assert target == dest, (
						f"turn {turn_no}: {drone} was bound for '{dest}' "
						f"but moved to '{target}'"
					)
					positions[drone] = dest
					del transiting[drone]
					continue

				here = positions[drone]
				if "-" in target and target not in self.zones:
					# A connection token: launching toward a restricted zone.
					src, dst = self._parse_link(target, turn_no)
					assert src == here, (
						f"turn {turn_no}: {drone} on connection from '{src}' "
						f"but is in '{here}'"
					)
					self._assert_adjacent(src, dst, turn_no)
					assert self.zones[dst].zone_type is ZoneType.RESTRICTED, (
						f"turn {turn_no}: connection move to non-restricted '{dst}'"
					)
					transiting[drone] = dst
					# The drone is no longer resting in a zone; it is tracked in
					# `transiting` (occupying only its reserved destination).
					del positions[drone]
					link_usage[frozenset((src, dst))] = \
						link_usage.get(frozenset((src, dst)), 0) + 1
				else:
					# A normal one-turn move into an adjacent zone.
					assert target in self.zones, \
						f"turn {turn_no}: move to unknown zone '{target}'"
					self._assert_adjacent(here, target, turn_no)
					assert self.zones[target].zone_type is not ZoneType.BLOCKED, \
						f"turn {turn_no}: {drone} entered blocked '{target}'"
					positions[drone] = target
					link_usage[frozenset((here, target))] = \
						link_usage.get(frozenset((here, target)), 0) + 1

			self._check_capacities(positions, transiting, turn_no)
			self._check_links(link_usage, turn_no)

		assert not transiting, \
			f"simulation ended with drones still in transit: {transiting}"
		for drone, zone in positions.items():
			assert zone == end.name, f"{drone} ended at '{zone}', not the end zone"

	def _split_token(self, token: str, turn_no: int) -> tuple[str, str]:
		"""Split 'D3-zone' into ('D3', 'zone'). The drone id has no dashes."""
		assert token.startswith("D"), f"turn {turn_no}: bad token '{token}'"
		dash = token.find("-")
		assert dash != -1, f"turn {turn_no}: bad token '{token}'"
		return token[:dash], token[dash + 1:]

	def _parse_link(self, target: str, turn_no: int) -> tuple[str, str]:
		"""Split a 'source-dest' connection token into its two zone names."""
		parts = target.split("-")
		assert len(parts) == 2, f"turn {turn_no}: bad connection token '{target}'"
		return parts[0], parts[1]

	def _assert_adjacent(self, a: str, b: str, turn_no: int) -> None:
		key = frozenset((a, b))
		assert key in self.connections, \
			f"turn {turn_no}: no connection between '{a}' and '{b}'"

	def _check_capacities(
		self, positions: dict[str, str], transiting: dict[str, str], turn_no: int
	) -> None:
		"""No zone may hold more drones than its capacity allows."""
		counts: dict[str, int] = {}
		for zone_name in positions.values():
			counts[zone_name] = counts.get(zone_name, 0) + 1
		for dest in transiting.values():
			counts[dest] = counts.get(dest, 0) + 1
		for name, count in counts.items():
			zone = self.zones[name]
			assert not zone.is_full(count - 1), (
				f"turn {turn_no}: zone '{name}' holds {count}, "
				f"over capacity {zone.max_drones}"
			)

	def _check_links(
		self, link_usage: dict[frozenset[str], int], turn_no: int
	) -> None:
		"""No connection may carry more drones than its link capacity allows."""
		for key, used in link_usage.items():
			connection = self.connections[key]
			assert used <= connection.max_link_capacity, (
				f"turn {turn_no}: connection {tuple(key)} carried {used}, "
				f"over capacity {connection.max_link_capacity}"
			)
