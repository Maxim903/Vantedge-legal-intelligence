"""Tests for the shared BigQuery execution journal."""

import json
from decimal import Decimal
from unittest.mock import Mock

import pytest
from google.cloud import bigquery
from google.cloud.bigquery.table import RowIterator

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.tracking import tracked_run


def _params(call):
	return {item.name: item.value for item in call.args[1]}


def test_running_and_completion_share_identity_and_record_counts():
	client = Mock(spec=BigQueryClient)
	with tracked_run(client, "collect") as run:
		assert client.query.call_count == 1
		assert "'RUNNING'" in client.query.call_args.args[0]
		run.status = "DRY_RUN"
		run.counts.update(read=3, processed=2)
		run.estimated_cost = Decimal("1.25")
	start, finish = client.query.call_args_list
	initial, final = _params(start), _params(finish)
	assert "INSERT INTO `ops.pipeline_runs`" in start.args[0]
	assert "UPDATE `ops.pipeline_runs`" in finish.args[0]
	assert initial["job"] == "collect"
	assert initial["run_id"] == final["run_id"] == run.run_id
	assert initial["started"] == final["started"] <= final["finished"]
	assert final["status"] == "DRY_RUN"
	assert json.loads(final["counts"]) == {"read": 3, "processed": 2}
	assert final["cost"] == Decimal("1.25")
	assert final["error"] is None


def test_failure_retains_partial_counts_and_propagates_original_error():
	client = Mock(spec=BigQueryClient)
	with pytest.raises(ValueError, match="private@example.invalid"):
		with tracked_run(client, "job") as run:
			run.counts["read"] = 2
			raise ValueError("private@example.invalid")
	final = _params(client.query.call_args_list[-1])
	assert final["status"] == "FAILED"
	assert final["error"] == "ValueError"
	assert json.loads(final["counts"]) == {"read": 2}


def test_initial_failure_prevents_work_and_finalization():
	client = Mock(spec=BigQueryClient)
	client.query.side_effect = RuntimeError("journal unavailable")
	did_work = False
	with pytest.raises(RuntimeError, match="journal unavailable"):
		with tracked_run(client, "job"):
			did_work = True
	assert not did_work
	assert client.query.call_count == 1


def test_both_job_and_finalization_errors_are_preserved():
	client = Mock(spec=BigQueryClient)
	client.query.side_effect = [None, RuntimeError("journal unavailable")]
	with pytest.raises(ExceptionGroup) as error:
		with tracked_run(client, "job"):
			raise ValueError("bad data")
	assert [str(e) for e in error.value.exceptions] == [
		"bad data", "journal unavailable",
	]


def test_grouped_job_errors_record_types_without_messages():
	client = Mock(spec=BigQueryClient)
	with pytest.raises(ExceptionGroup):
		with tracked_run(client, "job"):
			raise ExceptionGroup(
				"private group", [
					ValueError("private job"),
					ExceptionGroup("private nested", [RuntimeError("private cost")]),
				]
			)
	error = _params(client.query.call_args_list[-1])["error"]
	assert error == "ExceptionGroup [ValueError; ExceptionGroup [RuntimeError]]"


def test_native_client_uses_explicit_ops_dataset():
	client = Mock(spec=bigquery.Client)
	dataset = bigquery.DatasetReference("test-project", "custom_ops")
	with tracked_run(client, "graph_sync", dataset=dataset):
		pass
	for call in client.query.call_args_list:
		assert call.kwargs["job_config"].default_dataset == dataset
		assert "`pipeline_runs`" in call.args[0]
	assert client.query.return_value.result.call_count == 2


def test_missing_or_duplicate_journal_row_is_an_error():
	client = Mock(spec=BigQueryClient)
	start = Mock(spec=RowIterator)
	start.num_dml_affected_rows = 1
	finish = Mock(spec=RowIterator)
	finish.num_dml_affected_rows = 0
	client.query.side_effect = [start, finish]
	with pytest.raises(RuntimeError, match="exactement une ligne"):
		with tracked_run(client, "job"):
			pass
