"""SERP collection tests with BigQuery, GCS and DataForSEO doubles."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.clients.dataforseo import SerpResponse
from vil_pipeline.jobs.collect_serp import (
	LANGUAGE_CODE_FRENCH,
	LOCATION_CODE_FRANCE,
	SERP_ENDPOINT,
	VOLUME_ENDPOINT,
	collect_serp,
)
from vil_pipeline.keys import idempotency_key

FIXTURES = Path(__file__).parents[1] / "fixtures" / "dataforseo"
PERIOD = "2026-11"
TODAY = date(2026, 11, 15)


class FakeGCS:
	def __init__(self, blobs=None):
		self.blobs = dict(blobs or {})
		self.uploads = []

	def list_blob_names(self, prefix):
		return [name for name in self.blobs if name.startswith(prefix)]

	def download_json(self, name):
		return self.blobs[name]

	def upload_json_immutable(self, name, data, *, metadata=None):
		self.uploads.append((name, data, metadata))
		self.blobs[name] = data


class FakeSerpProvider:
	def __init__(self):
		self.calls = []
		self.response = SerpResponse.model_validate_json(
			(FIXTURES / "serp_organic_success.json").read_text(encoding="utf-8")
		)

	def serp_organic(self, keyword, *, location_code, language_code, depth=10):
		self.calls.append((keyword, location_code, language_code, depth))
		return self.response


def _key(endpoint, keyword):
	return idempotency_key(
		endpoint, keyword, LOCATION_CODE_FRANCE, LANGUAGE_CODE_FRENCH, PERIOD
	)


def _volume_blob(keyword, volume):
	payload = json.loads(
		(FIXTURES / "search_volume_success.json").read_text(encoding="utf-8")
	)
	result = payload["tasks"][0]["result"][0]
	result["keyword"] = keyword
	result["search_volume"] = volume
	key = _key(VOLUME_ENDPOINT, keyword)
	name = f"dataforseo/{VOLUME_ENDPOINT}/2026/11/10/{key}.json"
	return name, payload


def _setup(volumes, candidates, extra_blobs=None):
	blobs = dict(_volume_blob(k, v) for k, v in volumes.items())
	blobs.update(extra_blobs or {})
	bq = Mock(spec=BigQueryClient)
	bq.query.side_effect = [[], [{"requete": c} for c in candidates], []]
	return bq, FakeGCS(blobs), FakeSerpProvider()


def _run(bq, gcs, provider, **overrides):
	options = {
		"top_n": 2,
		"max_cost": Decimal("0.01"),
		"cost_per_call": Decimal("0.003"),
		"period": PERIOD,
		"today": TODAY,
	}
	options.update(overrides)
	return collect_serp(bq, gcs, provider, **options)


def test_only_the_top_n_highest_volume_queries_are_fetched_and_archived():
	bq, gcs, provider = _setup(
		{"a": 100, "b": 500, "c": 300}, ["a", "b", "c", "d"]
	)

	stats = _run(bq, gcs, provider)

	assert provider.calls == [
		("b", LOCATION_CODE_FRANCE, LANGUAGE_CODE_FRENCH, 10),
		("c", LOCATION_CODE_FRANCE, LANGUAGE_CODE_FRENCH, 10),
	]
	assert (stats.ranked, stats.selected, stats.cached, stats.calls) == (3, 2, 0, 2)
	assert stats.status == "SUCCESS"
	assert stats.estimated_cost == stats.actual_cost == Decimal("0.006")
	assert [name for name, _, _ in gcs.uploads] == [
		f"dataforseo/{SERP_ENDPOINT}/2026/11/15/{_key(SERP_ENDPOINT, k)}.json"
		for k in ("b", "c")
	]
	assert gcs.uploads[0][2]["endpoint"] == SERP_ENDPOINT
	assert bq.insert.call_args.args[0] == "ops.couts_api"
	assert len(bq.insert.call_args.args[1]) == 2
	run_sql = bq.query.call_args_list[-1].args[0]
	assert "UPDATE `ops.pipeline_runs`" in run_sql
	start = {p.name: p.value for p in bq.query.call_args_list[0].args[1]}
	finish = {p.name: p.value for p in bq.query.call_args_list[-1].args[1]}
	assert bq.query.call_count == 3
	assert start["run_id"] == finish["run_id"] == stats.run_id
	assert all(row["lot_id"] == stats.run_id for row in bq.insert.call_args.args[1])


def test_fresh_serp_archive_is_not_fetched_again():
	fresh = f"dataforseo/{SERP_ENDPOINT}/2026/11/05/{_key(SERP_ENDPOINT, 'b')}.json"
	bq, gcs, provider = _setup(
		{"a": 100, "b": 500, "c": 300}, ["a", "b", "c"], {fresh: {}}
	)

	stats = _run(bq, gcs, provider)

	assert [call[0] for call in provider.calls] == ["c"]
	assert (stats.selected, stats.cached, stats.calls) == (2, 1, 1)


@pytest.mark.parametrize(
	("max_cost", "status"),
	[(Decimal("0.01"), "DRY_RUN"), (Decimal("0.005"), "DRY_RUN_OVER_BUDGET")],
)
def test_dry_run_estimates_calls_and_cost_without_side_effects(max_cost, status):
	bq, gcs, _ = _setup({"a": 100, "b": 500, "c": 300}, ["a", "b", "c"])

	stats = _run(bq, gcs, None, dry_run=True, max_cost=max_cost)

	assert stats.status == status
	assert (stats.calls, stats.estimated_cost) == (2, Decimal("0.006"))
	assert stats.actual_cost == 0
	assert gcs.uploads == []
	bq.insert.assert_not_called()
	assert "ops.pipeline_runs" in bq.query.call_args_list[-1].args[0]


def test_collection_stops_before_exceeding_the_budget():
	bq, gcs, provider = _setup({"a": 100, "b": 500}, ["a", "b"])

	stats = _run(bq, gcs, provider, max_cost=Decimal("0.003"))

	assert stats.status == "BUDGET_EXHAUSTED"
	assert [call[0] for call in provider.calls] == ["b"]
	assert stats.calls == 1


def test_candidates_without_archived_volume_are_reported_not_silently_ignored():
	bq, gcs, provider = _setup({}, ["a", "b"])

	stats = _run(bq, gcs, provider)

	assert stats.status == "NO_VOLUME_DATA"
	assert provider.calls == []


@pytest.mark.parametrize("top_n", [0, -1])
def test_invalid_top_n_is_tracked(top_n):
	bq, gcs, provider = _setup({}, [])

	with pytest.raises(ValueError, match="top_n"):
		_run(bq, gcs, provider, top_n=top_n)
	assert bq.query.call_count == 2
	assert "INSERT INTO `ops.pipeline_runs`" in bq.query.call_args_list[0].args[0]
	assert "UPDATE `ops.pipeline_runs`" in bq.query.call_args_list[1].args[0]
	finish = {p.name: p.value for p in bq.query.call_args_list[1].args[1]}
	assert finish["status"] == "FAILED"
	assert finish["error"] == "ValueError"
	assert json.loads(finish["counts"])["calls"] == 0


def test_cost_is_logged_even_if_archiving_fails(monkeypatch):
	bq, gcs, provider = _setup({"a": 100}, ["a"])
	monkeypatch.setattr(
		"vil_pipeline.jobs.collect_serp.archive_dataforseo_response",
		Mock(side_effect=RuntimeError("GCS unavailable")),
	)

	with pytest.raises(RuntimeError, match="GCS unavailable"):
		_run(bq, gcs, provider)

	assert bq.insert.call_args.args[0] == "ops.couts_api"
	assert bq.insert.call_args.args[1][0]["montant"] == Decimal("0.003")
	start = {p.name: p.value for p in bq.query.call_args_list[0].args[1]}
	finish = {p.name: p.value for p in bq.query.call_args_list[-1].args[1]}
	assert bq.query.call_count == 3
	assert bq.insert.call_args.args[1][0]["lot_id"] == start["run_id"]
	assert finish["run_id"] == start["run_id"]
	assert finish["status"] == "FAILED"
	assert finish["error"] == "RuntimeError"
	assert finish["cost"] == Decimal("0.003")
	assert json.loads(finish["counts"])["calls"] == 1


@pytest.mark.parametrize(
	"business_error", [RuntimeError("GCS unavailable"), KeyboardInterrupt()]
)
def test_cost_write_failure_is_tracked_and_retains_archive_failure(
	monkeypatch, business_error
):
	bq, gcs, provider = _setup({"a": 100}, ["a"])
	monkeypatch.setattr(
		"vil_pipeline.jobs.collect_serp.archive_dataforseo_response",
		Mock(side_effect=business_error),
	)
	cost_error = ValueError("cost write failed")
	bq.insert.side_effect = cost_error

	with pytest.raises(BaseExceptionGroup) as raised:
		_run(bq, gcs, provider)

	assert raised.value.exceptions == (business_error, cost_error)
	assert bq.query.call_count == 3
	finish = {p.name: p.value for p in bq.query.call_args_list[-1].args[1]}
	assert finish["status"] == "FAILED"
	assert finish["error"].startswith(type(raised.value).__name__)
	assert "ValueError" in finish["error"]
	assert finish["cost"] == Decimal("0.003")
	assert json.loads(finish["counts"]) == {
		"status": "FAILED", "ranked": 1, "selected": 1, "cached": 0, "calls": 1,
	}


def test_cost_write_failure_alone_is_propagated():
	bq, gcs, provider = _setup({"a": 100}, ["a"])
	bq.insert.side_effect = ValueError("cost write failed")

	with pytest.raises(ValueError, match="cost write failed"):
		_run(bq, gcs, provider)
	finish = {p.name: p.value for p in bq.query.call_args_list[-1].args[1]}
	assert finish["status"] == "FAILED"
	assert json.loads(finish["counts"])["calls"] == 1
