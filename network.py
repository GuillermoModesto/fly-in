from connection import Connection
from hubzone import HubZone
from zone import Zone


class Network:
	def __init__(self, nb_drones: int) -> None:
		if nb_drones < 1:
			raise ValueError(f"nb_drones must be a positive integer, got {nb_drones}")
		self.nb_drones = nb_drones
		self.zones: dict[str, Zone] = {}
		self.connections: list[Connection] = []
		self.start: Zone | None = None
		self.end: Zone | None = None
		self._pairs: set[frozenset[str]] = set()

	def add_zone(self, zone: Zone) -> None:
		if zone.name in self.zones:
			raise ValueError(f"duplicate zone name '{zone.name}'")
		if zone.role is HubZone.START:
			if self.start is not None:
				raise ValueError("more than one start_hub defined")
			self.start = zone
		if zone.role is HubZone.END:
			if self.end is not None:
				raise ValueError("more than one end_hub defined")
			self.end = zone
		self.zones[zone.name] = zone

	def add_connection(
			self,
			name1: str,
			name2: str,
			max_link_capacity: int = 1
			) -> None:
		if name1 == name2:
			raise ValueError(f"connection links zone '{name1}' to itself")
		if name1 not in self.zones:
			raise ValueError(f"connection references unknown zone '{name1}'")
		if name2 not in self.zones:
			raise ValueError(f"connection references unknown zone '{name2}'")
		pair = frozenset((name1, name2))
		if pair in self._pairs:
			raise ValueError(f"duplicate connection between '{name1}' and '{name2}'")
		self._pairs.add(pair)
		connection = Connection(
			self.zones[name1],
			self.zones[name2],
			max_link_capacity
			)
		self.connections.append(connection)

	def validate(self) -> None:
		if self.start is None:
			raise ValueError("no start_hub defined")
		if self.end is None:
			raise ValueError("no end_hub defined")
