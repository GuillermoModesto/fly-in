from enum import Enum


class ZoneType(Enum):

	NORMAL = "normal"
	BLOCKED = "blocked"
	RESTRICTED = "restricted"
	PRIORITY = "priority"

	def movement_cost(self) -> int:
		if self is ZoneType.RESTRICTED:
			return 2
		if self is ZoneType.BLOCKED:
			raise ValueError("blocked zones cannot be entered")
		return 1
