from zone import Zone


class Connection:
	def __init__(
		self,
		zone1: Zone,
		zone2: Zone,
		max_link_capacity: int = 1,
	) -> None:
		if max_link_capacity < 1:
			raise ValueError(
				f"max_link_capacity must be a positive integer, got {max_link_capacity}"
			)
		self.zone1 = zone1
		self.zone2 = zone2
		self.max_link_capacity = max_link_capacity

	def connects(self, zone: Zone) -> bool:
		return zone is self.zone1 or zone is self.zone2

	def other(self, zone: Zone) -> Zone:
		if zone is self.zone1:
			return self.zone2
		if zone is self.zone2:
			return self.zone1
		raise ValueError("zone is not an endpoint of this connection")
