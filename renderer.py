from network import Network

# Map common colour words to ANSI 256-colour codes (used as 38;5;<code>).
# Covers the colours that appear in the provided maps; anything not listed
# falls back to a default colour so every zone is still coloured.
_COLOURS: dict[str, int] = {
	"black": 240, "white": 255, "gray": 245, "grey": 245,
	"red": 196, "green": 46, "blue": 33, "yellow": 226,
	"cyan": 51, "magenta": 201, "orange": 208, "gold": 220,
	"purple": 129, "violet": 141, "pink": 213, "brown": 130,
	"maroon": 88, "crimson": 160, "darkred": 52, "lime": 118,
	"teal": 30, "navy": 18, "olive": 100, "silver": 250,
	"rainbow": 213,
}
_DEFAULT = 244  # fallback colour for unrecognised colour words
_RESET = "\033[0m"


class Renderer:
	"""Renders a colour-coded, turn-by-turn view of a simulation.

	Works purely from the emitted move lines: it replays them to track where
	each drone is, then prints a snapshot each turn. The simulator is left
	untouched -- the renderer is a separate display concern.
	"""

	def __init__(self, network: Network) -> None:
		self.network = network

	def _colour(self, zone_name: str, text: str) -> str:
		"""Wrap `text` in the ANSI colour of the zone.

		Every zone is coloured: a known colour word maps to its code, and any
		other value (or none) uses a default colour.
		"""
		zone = self.network.zones.get(zone_name)
		word = zone.color.lower() if (zone and zone.color) else None
		code = _COLOURS.get(word, _DEFAULT) if word else _DEFAULT
		return f"\033[38;5;{code}m{text}{_RESET}"

	def render(self, lines: list[str]) -> None:
		"""Replay the move `lines` and print a coloured snapshot per turn."""
		start = self.network.start
		end = self.network.end
		if start is None or end is None:
			return

		# drone id -> current zone name (or connection token while in transit)
		positions: dict[str, str] = {
			f"D{i + 1}": start.name for i in range(self.network.nb_drones)
		}

		for turn_no, line in enumerate(lines, start=1):
			for token in line.split():
				drone, target = self._split(token)
				positions[drone] = target
			self._print_turn(turn_no, positions)

	def _print_turn(self, turn_no: int, positions: dict[str, str]) -> None:
		"""Print one turn: header, then each occupied zone on its own line."""
		by_zone: dict[str, list[str]] = {}
		for drone, where in positions.items():
			by_zone.setdefault(where, []).append(drone)

		print(f"Turn {turn_no}")
		for zone_name in sorted(by_zone, key=self._sort_key):
			drones = " ".join(sorted(by_zone[zone_name], key=_drone_key))
			label = self._colour(zone_name, f"{zone_name:<24}")
			print(f"  {label} {drones}")
		print()

	def _sort_key(self, name: str) -> tuple[int, str]:
		"""Sort zones: connections (in-transit) last, otherwise alphabetical."""
		is_link = "-" in name and name not in self.network.zones
		return (1 if is_link else 0, name)

	def _split(self, token: str) -> tuple[str, str]:
		"""Split 'D3-zone' or 'D3-src-dst' into (drone, target)."""
		dash = token.find("-")
		return token[:dash], token[dash + 1:]


def _drone_key(drone: str) -> int:
	"""Sort key so D2 comes before D10 (numeric, not lexicographic)."""
	return int(drone[1:])
