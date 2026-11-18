"""Tests for the graph synchronization entry point."""

import sys
from unittest.mock import MagicMock

import pytest
from google.cloud import bigquery
from graph import __main__ as graph_main
from graph.sync import SyncStats


def test_main_runs_sync_and_closes_clients(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["graph", "--project-id", "test-project"])
    monkeypatch.setenv("NEO4J_URI", "bolt://example")
    monkeypatch.setenv("NEO4J_USER", "user")
    monkeypatch.setenv("NEO4J_PASSWORD", "password")
    monkeypatch.setenv("BQ_LOCATION", "europe-west9")
    client = MagicMock()
    driver = MagicMock()
    client_factory = MagicMock(return_value=client)
    driver_factory = MagicMock(return_value=driver)
    sync = MagicMock(return_value=SyncStats(run_id="run", node_rows=3))
    monkeypatch.setattr(graph_main.bigquery, "Client", client_factory)
    monkeypatch.setattr(graph_main.GraphDatabase, "driver", driver_factory)
    monkeypatch.setattr(graph_main, "sync_graph", sync)

    graph_main.main()

    client_factory.assert_called_once_with(
        project="test-project", location="europe-west9"
    )
    sync.assert_called_once_with(
        driver.__enter__.return_value,
        client.__enter__.return_value,
        bigquery.DatasetReference("test-project", "marts"),
        batch_size=1000,
    )
    driver_factory.assert_called_once_with("bolt://example", auth=("user", "password"))
    assert driver.__exit__.call_count == client.__exit__.call_count == 1
    assert "nœuds 3" in capsys.readouterr().out


def test_main_propagates_sync_failure_and_closes_clients(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["graph", "--project-id", "test-project"])
    for name in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"):
        monkeypatch.setenv(name, "value")
    client, driver = MagicMock(), MagicMock()
    monkeypatch.setattr(graph_main.bigquery, "Client", lambda **kwargs: client)
    monkeypatch.setattr(
        graph_main.GraphDatabase, "driver", lambda *args, **kwargs: driver
    )
    monkeypatch.setattr(
        graph_main, "sync_graph", MagicMock(side_effect=RuntimeError("failed"))
    )

    with pytest.raises(RuntimeError, match="failed"):
        graph_main.main()
    assert driver.__exit__.call_count == client.__exit__.call_count == 1


def test_main_rejects_missing_neo4j_credentials(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["graph", "--project-id", "test-project"])
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    client_factory = MagicMock()
    monkeypatch.setattr(graph_main.bigquery, "Client", client_factory)
    with pytest.raises(SystemExit) as exc:
        graph_main.main()
    assert exc.value.code == 2
    client_factory.assert_not_called()
