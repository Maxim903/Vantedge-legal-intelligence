"""Failure handling for graph synchronization."""

import json
from unittest.mock import MagicMock, Mock

import pytest
from google.cloud import bigquery
from graph.export import Code, ExportBatch
from graph.sync import sync_graph
from neo4j import Driver


def _failing_sync(monkeypatch, *, journal_error=None):
    dataset = bigquery.DatasetReference("test-project", "marts")
    client = Mock(spec=bigquery.Client)
    if journal_error is not None:
        client.query.side_effect = [Mock(), journal_error]
    driver = MagicMock(spec=Driver)
    session = driver.session.return_value.__enter__.return_value
    session.execute_write.side_effect = RuntimeError("Neo4j unavailable")
    code = Code(code_id="c", legifrance_id="lc", libelle="Code", ordre=1)

    def batches(client, dataset, table, *, batch_size):
        if table == "dim_code":
            yield ExportBatch(table=table, rows=[code], next_page_token=None)

    monkeypatch.setattr("graph.sync.iter_table_batches", batches)
    return driver, client, dataset


def test_failed_run_is_journaled_and_error_propagates(monkeypatch):
    driver, client, dataset = _failing_sync(monkeypatch)
    with pytest.raises(RuntimeError, match="Neo4j unavailable"):
        sync_graph(driver, client, dataset)

    options = client.query.call_args.kwargs["job_config"]
    assert options.default_dataset == bigquery.DatasetReference("test-project", "ops")
    params = {param.name: param.value for param in options.query_parameters}
    assert params["status"] == "FAILED"
    assert "Neo4j unavailable" in params["error"]
    assert json.loads(params["counts"])["batches"] == 0
    assert client.query.return_value.result.call_count == 2


def test_journal_failure_does_not_hide_sync_failure(monkeypatch):
    driver, client, dataset = _failing_sync(
        monkeypatch, journal_error=RuntimeError("BigQuery unavailable")
    )
    with pytest.raises(ExceptionGroup) as error:
        sync_graph(driver, client, dataset)
    assert [str(exc) for exc in error.value.exceptions] == [
        "Neo4j unavailable",
        "BigQuery unavailable",
    ]


def test_invalid_batch_size_does_not_open_a_session():
    driver = MagicMock(spec=Driver)
    client = Mock(spec=bigquery.Client)
    with pytest.raises(ValueError, match="batch_size"):
        sync_graph(
            driver,
            client,
            bigquery.DatasetReference("test-project", "marts"),
            batch_size=0,
        )
    driver.session.assert_not_called()
    assert client.query.call_count == 2
    params = client.query.call_args.kwargs["job_config"].query_parameters
    assert {param.name: param.value for param in params}["status"] == "FAILED"
