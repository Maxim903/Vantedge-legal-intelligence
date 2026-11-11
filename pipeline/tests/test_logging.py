"""Tests for pipeline logging."""

import json

from vil_pipeline.logging import configure_logging


def test_configure_logging_emits_json_with_run_and_job(capsys):
	logger = configure_logging(run_id="run-123", job="extract")

	logger.info("job_started", item_count=3)

	record = json.loads(capsys.readouterr().out)
	assert record["event"] == "job_started"
	assert record["run_id"] == "run-123"
	assert record["job"] == "extract"
	assert record["item_count"] == 3
