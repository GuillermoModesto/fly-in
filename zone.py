from hubzone import HubZone
from zonetype import ZoneType


class Zone:
	def __init__(
		self,
		name: str,
		role: HubZone,
		coords: tuple[int, int],
		zone_type: ZoneType = ZoneType.NORMAL,
		color: str | None = None,
		max_drones: int = 1,
	) -> None:
		if max_drones < 1:
			raise ValueError(f"max_drones must be a positive integer, got {max_drones}")
		self.name = name
		self.role = role
		self.coords = coords
		self.zone_type = zone_type
		self.color = color
		self.max_drones = max_drones

	def is_full(self, count: int) -> bool:
		if self.role in (HubZone.START, HubZone.END):
			return False
		return count >= self.max_drones
