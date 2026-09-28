from typing import Callable, TypeVar

from hubzone import HubZone
from network import Network
from parsererror import ParserError
from zone import Zone
from zonetype import ZoneType

T = TypeVar("T")


class Parser:
	"""Turns the text of a map file into a validated Network.

	The parser only reads text and tracks line numbers. Every actual rule lives
	in Zone, Connection, and Network, which raise ValueError on violation; the
	parser catches those and re-raises them as ParserError with a line number.
	"""

	_ZONE_KEYS = {"zone", "color", "max_drones"}
	_CONNECTION_KEYS = {"max_link_capacity"}

	def parse(self, text: str) -> Network:
		"""Parse the full text of a map file and return a validated Network."""
		lines = text.splitlines()
		network = self._read_header(lines)
		self._read_body(lines, network)
		self._wrap(network.validate, None)
		return network

	def _read_header(self, lines: list[str]) -> Network:
		"""Read the first meaningful line, which must be `nb_drones: <int>`."""
		for i, raw in enumerate(lines):
			line = self._strip(raw)
			if not line:
				continue
			line_number = i + 1
			if not line.startswith("nb_drones:"):
				raise ParserError(line_number, "first line must be 'nb_drones: <n>'")
			value = line[len("nb_drones:"):].strip()
			nb_drones = self._to_int(value, line_number, "nb_drones")
			return self._wrap(lambda: Network(nb_drones), line_number)
		raise ParserError(None, "file is empty or has no 'nb_drones:' line")

	def _read_body(self, lines: list[str], network: Network) -> None:
		"""Read every line after the header, dispatching on its prefix."""
		seen_header = False
		for index, raw in enumerate(lines):
			line = self._strip(raw)
			if not line:
				continue
			line_number = index + 1
			if not seen_header:
				seen_header = True
				continue
			if line.startswith("nb_drones:"):
				raise ParserError(line_number, "'nb_drones:' defined more than once")
			elif line.startswith("start_hub:"):
				self._parse_zone(line, line_number, network, HubZone.START, "start_hub:")
			elif line.startswith("end_hub:"):
				self._parse_zone(line, line_number, network, HubZone.END, "end_hub:")
			elif line.startswith("hub:"):
				self._parse_zone(line, line_number, network, HubZone.REGULAR, "hub:")
			elif line.startswith("connection:"):
				self._parse_connection(line, line_number, network)
			else:
				raise ParserError(line_number, f"unrecognized line: '{line}'")

	def _parse_zone(
		self,
		line: str,
		line_number: int,
		network: Network,
		role: HubZone,
		prefix: str,
	) -> None:
		"""Parse a `<prefix> name x y [metadata]` line and add the zone."""
		rest, meta = self._split_metadata(line[len(prefix):], line_number)
		tokens = rest.split()
		if len(tokens) != 3:
			raise ParserError(
				line_number, "zone must be '<name> <x> <y>' before any metadata"
			)
		name, x_str, y_str = tokens
		if "-" in name:
			raise ParserError(line_number, f"zone name '{name}' may not contain '-'")
		x = self._to_int(x_str, line_number, "x coordinate")
		y = self._to_int(y_str, line_number, "y coordinate")

		meta = self._check_keys(meta, self._ZONE_KEYS, line_number)
		zone_type = self._parse_zone_type(meta.get("zone"), line_number)
		color = meta.get("color")
		if role in (HubZone.START, HubZone.END):
			max_drones = 1
		else:
			max_drones = self._to_int(
				meta.get("max_drones", "1"), line_number, "max_drones"
			)

		zone = self._wrap(
			lambda: Zone(name, role, (x, y), zone_type, color, max_drones),
			line_number,
		)
		self._wrap(lambda: network.add_zone(zone), line_number)

	def _parse_zone_type(self, value: str | None, line_number: int) -> ZoneType:
		"""Convert a zone-type string into a ZoneType, defaulting to NORMAL."""
		if value is None:
			return ZoneType.NORMAL
		try:
			return ZoneType(value)
		except ValueError:
			raise ParserError(line_number, f"unknown zone type '{value}'")

	def _parse_connection(
			self,
			line: str,
			line_number: int,
			network: Network
			) -> None:
		"""Parse a `connection: name1-name2 [metadata]` line and add the link."""
		rest, meta = self._split_metadata(line[len("connection:"):], line_number)
		tokens = rest.split()
		if len(tokens) != 1:
			raise ParserError(
				line_number, "connection must be 'name1-name2' before any metadata"
			)
		pair = tokens[0]
		if pair.count("-") != 1:
			raise ParserError(
				line_number, f"connection '{pair}' must be exactly 'name1-name2'"
			)
		name1, name2 = pair.split("-")
		if not name1 or not name2:
			raise ParserError(
				line_number,
				f"connection '{pair}' has an empty zone name"
				)

		meta = self._check_keys(meta, self._CONNECTION_KEYS, line_number)
		capacity = self._to_int(
			meta.get("max_link_capacity", "1"), line_number, "max_link_capacity"
		)
		self._wrap(
			lambda: network.add_connection(name1, name2, capacity), line_number
		)

	def _strip(self, raw: str) -> str:
		"""Remove any comment (from '#' onward) and surrounding whitespace."""
		comment = raw.find("#")
		if comment != -1:
			raw = raw[:comment]
		return raw.strip()

	def _split_metadata(
		self, text: str, line_number: int
	) -> tuple[str, dict[str, str]]:
		"""Split trailing '[...]' metadata off a line, returning (body, dict)."""
		start = text.find("[")
		if start == -1:
			return text.strip(), {}
		if not text.rstrip().endswith("]"):
			raise ParserError(line_number, "malformed metadata: missing closing ']'")
		body = text[:start]
		inside = text[start + 1:text.rfind("]")]
		meta: dict[str, str] = {}
		for token in inside.split():
			if token.count("=") != 1:
				raise ParserError(line_number, f"malformed metadata tag '{token}'")
			key, value = token.split("=")
			if not key or not value:
				raise ParserError(line_number, f"malformed metadata tag '{token}'")
			if key in meta:
				raise ParserError(line_number, f"duplicate metadata key '{key}'")
			meta[key] = value
		return body.strip(), meta

	def _check_keys(
		self, meta: dict[str, str], allowed: set[str], line_number: int
	) -> dict[str, str]:
		"""Reject any metadata key that isn't in the allowed set."""
		for key in meta:
			if key not in allowed:
				raise ParserError(line_number, f"unknown metadata key '{key}'")
		return meta

	def _to_int(self, value: str, line_number: int, field: str) -> int:
		"""Convert a string to int, raising a ParserError naming the field."""
		try:
			return int(value)
		except ValueError:
			raise ParserError(line_number, f"{field} must be an integer, got '{value}'")

	def _wrap(self, action: Callable[[], T], line_number: int | None) -> T:
		"""Run an action, converting any ValueError into a ParserError.

		This is how rule violations raised by Zone/Connection/Network (which know
		nothing about line numbers) get a line number attached. Whatever the
		action returns is passed straight back, so it works both for calls that
		build an object (Zone, Network) and calls that just mutate (add_zone).
		"""
		try:
			return action()
		except ValueError as error:
			raise ParserError(line_number, str(error))
