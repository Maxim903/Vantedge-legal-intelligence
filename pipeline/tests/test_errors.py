"""Tests for pipeline errors."""

import pytest

from vil_pipeline.errors import (
	ApiBudgetExceeded,
	ExtractionError,
	SchemaValidationError,
	VilError,
)


@pytest.mark.parametrize(
	"error_type",
	[VilError, ExtractionError, ApiBudgetExceeded, SchemaValidationError],
)
def test_pipeline_errors_preserve_message_and_share_base(error_type):
	error = error_type("operation failed")

	assert isinstance(error, VilError)
	assert str(error) == "operation failed"
