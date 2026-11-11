"""Pipeline errors."""


class VilError(Exception):
	"""Base exception for pipeline errors."""


class ExtractionError(VilError):
	"""Raised when extraction fails."""


class ApiBudgetExceeded(VilError):
	"""Raised when an API budget is exhausted."""


class SchemaValidationError(VilError):
	"""Raised when data does not match the expected schema."""
