from zone import Zone


class Drone:
	"""A single drone travelling along its own assigned path.

	Position is an index into `path`: 0 is the start, the last index is the end.
	A drone moving toward a restricted zone spends one turn in transit;
	`arriving_at` records the path index it will land on next turn, and is None
	whenever the drone is resting in a zone.
	"""

	def __init__(self, drone_id: int, path: list[Zone]) -> None:
		self.id = drone_id
		self.path = path
		self.position = 0
		self.arriving_at: int | None = None

	@property
	def in_transit(self) -> bool:
		"""True if the drone is mid-flight toward a restricted zone."""
		return self.arriving_at is not None

	@property
	def end_index(self) -> int:
		"""The index of this drone's final (end) zone on its own path."""
		return len(self.path) - 1

	def current_zone(self) -> Zone:
		"""The zone this drone currently occupies.

		Returns its reserved destination while it is in transit.
		"""
		index = self.arriving_at if self.in_transit else self.position
		assert index is not None
		return self.path[index]

	def delivered(self) -> bool:
		"""True if the drone has reached its end zone and is resting there."""
		return self.position == self.end_index and self.arriving_at is None
