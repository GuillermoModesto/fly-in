class ParserError(Exception):
	"""Raised when a map file violates the expected structure or syntax.

	Carries the line number where the problem occurred (when one applies) and a
	human-readable cause, so the program can report both as required by the
	subject. Some problems are whole-file issues with no specific line (for
	example, no end_hub anywhere); those are created with line_number=None and
	print without a line prefix.
	"""

	def __init__(self, line_number: int | None, message: str) -> None:
		self.line_number = line_number
		self.message = message
		if line_number is None:
			super().__init__(message)
		else:
			super().__init__(f"Line {line_number}: {message}")
