"""Tests for the BigQuery client."""

from unittest.mock import Mock

import pytest
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from vil_pipeline.clients.bigquery import BigQueryClient


@pytest.fixture
def bq_client():
	client = Mock(spec=bigquery.Client)
	return BigQueryClient("test-project", "US", client=client), client


def test_query_passes_sql_and_parameters_to_bigquery_without_rewriting(bq_client):
	wrapper, client = bq_client
	job = Mock()
	rows = Mock()
	job.result.return_value = rows
	client.query.return_value = job
	sql = "SELECT * FROM `test-project.dataset.table` WHERE id = @record_id"
	parameters = [bigquery.ScalarQueryParameter("record_id", "STRING", "abc")]

	result = wrapper.query(sql, parameters)

	assert result is rows
	client.query.assert_called_once()
	called_sql, = client.query.call_args.args
	assert called_sql == sql
	config = client.query.call_args.kwargs["job_config"]
	assert config.query_parameters == parameters
	assert config.dry_run is False
	assert client.query.call_args.kwargs["location"] == "US"


def test_query_in_dry_run_returns_job_without_fetching_results(bq_client):
	_, client = bq_client
	job = Mock()
	client.query.return_value = job
	wrapper = BigQueryClient("test-project", dry_run=True, client=client)

	result = wrapper.query("SELECT 1")

	assert result is job
	assert client.query.call_args.kwargs["job_config"].dry_run is True
	job.result.assert_not_called()


def test_query_job_returns_job_without_running_it(bq_client):
	wrapper, client = bq_client
	job = Mock()
	client.query.return_value = job

	result = wrapper.query_job(
		"MERGE target USING source ON TRUE WHEN NOT MATCHED THEN INSERT ROW",
	)

	assert result is job
	client.query.assert_called_once()
	job.result.assert_not_called()


def test_insert_uses_load_job_and_waits_for_completion(bq_client):
	wrapper, client = bq_client
	job = Mock()
	client.load_table_from_json.return_value = job
	rows = [{"id": "abc"}]
	schema = [bigquery.SchemaField("id", "STRING")]

	result = wrapper.insert(
		"test-project.dataset.table",
		rows,
		schema=schema,
		write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
	)

	assert result is job
	client.load_table_from_json.assert_called_once()
	assert client.load_table_from_json.call_args.args == (
		rows,
		"test-project.dataset.table",
	)
	assert client.load_table_from_json.call_args.kwargs["location"] == "US"
	config = client.load_table_from_json.call_args.kwargs["job_config"]
	assert config.schema == schema
	assert config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
	job.result.assert_called_once_with()


def test_insert_in_dry_run_does_not_start_a_load_job(bq_client):
	_, client = bq_client
	wrapper = BigQueryClient("test-project", dry_run=True, client=client)

	assert wrapper.insert("test-project.dataset.table", [{"id": "abc"}]) is None

	client.load_table_from_json.assert_not_called()


def test_exists_table_returns_true_when_table_is_found(bq_client):
	wrapper, client = bq_client

	assert wrapper.exists_table("test-project.dataset.table") is True

	client.get_table.assert_called_once_with("test-project.dataset.table")


def test_exists_table_returns_false_only_for_not_found(bq_client):
	wrapper, client = bq_client
	client.get_table.side_effect = NotFound("missing")

	assert wrapper.exists_table("test-project.dataset.missing") is False


def test_exists_table_propagates_other_errors(bq_client):
	wrapper, client = bq_client
	client.get_table.side_effect = RuntimeError("unavailable")

	with pytest.raises(RuntimeError, match="unavailable"):
		wrapper.exists_table("test-project.dataset.table")


def test_delete_table_ignores_missing_table(bq_client):
	wrapper, client = bq_client

	wrapper.delete_table("test-project.dataset.table")

	client.delete_table.assert_called_once_with(
		"test-project.dataset.table",
		not_found_ok=True,
	)
