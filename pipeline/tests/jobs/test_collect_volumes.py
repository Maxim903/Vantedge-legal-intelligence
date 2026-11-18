"""Volume collection tests with BigQuery, GCS and DataForSEO doubles."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.clients.dataforseo import SearchVolumeResponse
from vil_pipeline.clients.gcs import GCSClient
from vil_pipeline.jobs.collect_volumes import (
	ENDPOINT,
	LANGUAGE_CODE_FRENCH,
	LOCATION_CODE_FRANCE,
	collect_volumes,
)
from vil_pipeline.keys import idempotency_key

FIXTURE = Path(__file__).parents[1] / "fixtures" / "dataforseo" / (
	"search_volume_success.json"
)


class FakeDataForSEOClient:
	def __init__(self) -> None:
		self.calls: list[tuple[list[str], int, str]] = []
		self.response = SearchVolumeResponse.model_validate_json(
			FIXTURE.read_text(encoding="utf-8")
		)

	def search_volume(
		self,
		keywords: list[str],
		*,
		location_code: int,
		language_code: str,
	) -> SearchVolumeResponse:
		self.calls.append((keywords, location_code, language_code))
		return self.response


def _clients(rows, blob_names=()):
	bq = Mock(spec=BigQueryClient)
	bq.query.side_effect = [[], rows, []]
	gcs = Mock(spec=GCSClient)
	gcs.list_blob_names.return_value = list(blob_names)
	api = FakeDataForSEOClient()
	return bq, gcs, api


def test_dry_run_counts_only_uncached_queries_without_provider_calls():
	today = date(2026, 11, 15)
	fresh_key = idempotency_key(ENDPOINT, "cached query", 2250, "fr", "2026-11")
	blob = f"dataforseo/{ENDPOINT}/2026/11/01/{fresh_key}.json"
	bq, gcs, api = _clients(
		[{"requete": "cached query"}, {"requete": "buy laptop"}], [blob]
	)

	stats = collect_volumes(
		bq,
		gcs,
		api,
		max_cost=Decimal("0.10"),
		cost_per_call=Decimal("0.075"),
		dry_run=True,
		period="2026-11",
		today=today,
	)

	assert stats.status == "DRY_RUN"
	assert (stats.read, stats.cached, stats.calls) == (2, 1, 1)
	assert stats.estimated_cost == Decimal("0.075")
	assert api.calls == []
	gcs.upload_json_immutable.assert_not_called()
	bq.insert.assert_not_called()
	assert "ops.pipeline_runs" in bq.query.call_args_list[-1].args[0]


def test_collection_stops_before_budget_exceeded_and_logs_call_cost():
	today = date(2026, 11, 15)
	bq, gcs, api = _clients([
		{"requete": "buy laptop"},
		{"requete": "second keyword"},
	])

	stats = collect_volumes(
		bq,
		gcs,
		api,
		max_cost=Decimal("0.075"),
		cost_per_call=Decimal("0.075"),
		period="2026-11",
		today=today,
	)

	assert stats.status == "BUDGET_EXHAUSTED"
	assert (stats.read, stats.cached, stats.calls) == (2, 0, 1)
	assert stats.estimated_cost == Decimal("0.075")
	assert stats.actual_cost == Decimal("0.075")
	assert api.calls == [(["buy laptop"], LOCATION_CODE_FRANCE, LANGUAGE_CODE_FRENCH)]
	key = idempotency_key(ENDPOINT, "buy laptop", 2250, "fr", "2026-11")
	archived_path = f"dataforseo/{ENDPOINT}/2026/11/15/{key}.json"
	gcs.upload_json_immutable.assert_called_once()
	assert gcs.upload_json_immutable.call_args.args[0] == archived_path
	assert bq.insert.call_args.args[0] == "ops.couts_api"
	cost_row = bq.insert.call_args.args[1][0]
	assert cost_row["lot_id"] == stats.run_id
	assert cost_row["montant"] == Decimal("0.075")
	assert cost_row["details"]["mot_cle"] == "buy laptop"
	assert "ops.pipeline_runs" in bq.query.call_args_list[-1].args[0]
	assert bq.query.call_count == 3
	start = {p.name: p.value for p in bq.query.call_args_list[0].args[1]}
	finish = {p.name: p.value for p in bq.query.call_args_list[-1].args[1]}
	assert start["run_id"] == finish["run_id"] == stats.run_id
	assert finish["status"] == "BUDGET_EXHAUSTED"


def test_cost_is_logged_even_if_gcs_archiving_fails(monkeypatch):
	today = date(2026, 11, 15)
	bq, gcs, api = _clients([{"requete": "buy laptop"}])
	monkeypatch.setattr(
		"vil_pipeline.jobs.collect_volumes.archive_dataforseo_response",
		Mock(side_effect=RuntimeError("GCS unavailable")),
	)

	try:
		collect_volumes(
			bq,
			gcs,
			api,
			max_cost=Decimal("0.10"),
			cost_per_call=Decimal("0.075"),
			period="2026-11",
			today=today,
		)
	except RuntimeError as error:
		assert str(error) == "GCS unavailable"
	else:
		raise AssertionError("Expected the archive failure to propagate")

	assert bq.insert.call_args.args[0] == "ops.couts_api"
	assert bq.insert.call_args.args[1][0]["montant"] == Decimal("0.075")
	start = {p.name: p.value for p in bq.query.call_args_list[0].args[1]}
	finish = {p.name: p.value for p in bq.query.call_args_list[-1].args[1]}
	assert bq.query.call_count == 3
	assert bq.insert.call_args.args[1][0]["lot_id"] == start["run_id"]
	assert finish["run_id"] == start["run_id"]
	assert finish["status"] == "FAILED"
	assert finish["error"] == "RuntimeError: GCS unavailable"
	assert finish["cost"] == Decimal("0.075")
	assert json.loads(finish["counts"])["calls"] == 1


@pytest.mark.parametrize(
	"business_error", [RuntimeError("GCS unavailable"), KeyboardInterrupt()]
)
def test_cost_write_failure_is_tracked_and_retains_archive_failure(
	monkeypatch, business_error
):
	bq, gcs, api = _clients([{"requete": "buy laptop"}])
	monkeypatch.setattr(
		"vil_pipeline.jobs.collect_volumes.archive_dataforseo_response",
		Mock(side_effect=business_error),
	)
	cost_error = ValueError("cost write failed")
	bq.insert.side_effect = cost_error

	with pytest.raises(BaseExceptionGroup) as raised:
		collect_volumes(
			bq, gcs, api, max_cost=Decimal("0.10"), cost_per_call=Decimal("0.075"),
		)
	assert raised.value.exceptions == (business_error, cost_error)
	assert bq.query.call_count == 3
	finish = {p.name: p.value for p in bq.query.call_args_list[-1].args[1]}
	assert finish["status"] == "FAILED"
	assert "2 sub-exceptions" in finish["error"]
	assert finish["cost"] == Decimal("0.075")
	assert json.loads(finish["counts"]) == {
		"status": "FAILED", "read": 1, "cached": 0, "calls": 1,
	}


def test_cost_write_failure_alone_is_propagated():
	bq, gcs, api = _clients([{"requete": "buy laptop"}])
	bq.insert.side_effect = ValueError("cost write failed")

	with pytest.raises(ValueError, match="cost write failed"):
		collect_volumes(
			bq, gcs, api, max_cost=Decimal("0.10"), cost_per_call=Decimal("0.075"),
		)
	finish = {p.name: p.value for p in bq.query.call_args_list[-1].args[1]}
	assert finish["status"] == "FAILED"
	assert json.loads(finish["counts"])["calls"] == 1