"""Raw market loading tests with stateful BigQuery and GCS doubles."""

import json
from pathlib import Path

import pytest

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.jobs.collect_serp import SERP_ENDPOINT
from vil_pipeline.jobs.collect_volumes import ENDPOINT as VOLUME_ENDPOINT
from vil_pipeline.jobs.load_raw_market import INTENT_ENDPOINT, load_raw_market

FIXTURES = Path(__file__).parents[1] / "fixtures" / "dataforseo"


class FakeGCS:
	def __init__(self, blobs):
		self.blobs = blobs

	def list_blob_names(self, prefix):
		return [name for name in self.blobs if name.startswith(prefix)]

	def download_json(self, name):
		return self.blobs[name]


class FakeBigQuery(BigQueryClient):
	"""Keeps loaded tables in memory; ops.archives_chargees feeds the next run."""

	def __init__(self):
		self.tables = {}
		self.fail_on = None
		self.starts = []
		self.runs = []

	def query(self, sql, parameters=()):
		if "INSERT INTO `ops.pipeline_runs`" in sql:
			self.starts.append({p.name: p.value for p in parameters})
		elif "UPDATE `ops.pipeline_runs`" in sql:
			self.runs.append({p.name: p.value for p in parameters})
		if "FROM `ops.archives_chargees`" in sql:
			return list(self.tables.get("ops.archives_chargees", []))
		if sql.lstrip().startswith("DELETE FROM"):
			table = sql.split("`")[1]
			blob = parameters[0].value
			self.tables[table] = [
				r for r in self.tables.get(table, []) if r["archive_blob"] != blob
			]
		return []

	def insert(self, table_id, rows, *, schema=None, write_disposition=None):
		if table_id == self.fail_on:
			raise RuntimeError("load failed")
		self.tables.setdefault(table_id, []).extend(rows)


def _blobs():
	volume = json.loads((FIXTURES / "search_volume_success.json").read_text())
	serp = json.loads((FIXTURES / "serp_organic_success.json").read_text())
	intent = {"tasks": [{"status_code": 20000, "result": [{"items": [
		{"keyword": "licenciement", "keyword_intent": {
			"label": "informational", "probability": 0.9}},
	]}]}]}
	failed = {"tasks": [{"status_code": 40501, "result": None}]}
	return {
		f"dataforseo/{VOLUME_ENDPOINT}/2026/11/01/a.json": volume,
		f"dataforseo/{SERP_ENDPOINT}/2026/11/02/b.json": serp,
		f"dataforseo/{INTENT_ENDPOINT}/2026/11/03/c.json": intent,
		f"dataforseo/{VOLUME_ENDPOINT}/2026/11/04/d.json": failed,
	}


def test_loads_each_endpoint_into_its_raw_table_and_records_archives():
	bq, gcs = FakeBigQuery(), FakeGCS(_blobs())

	stats = load_raw_market(bq, gcs)

	assert len(bq.starts) == len(bq.runs) == 1
	assert bq.starts[0]["run_id"] == bq.runs[0]["run_id"] == stats.run_id
	assert stats.status == "SUCCESS"
	assert stats.archives_loaded == 4
	volumes = bq.tables["raw.dataforseo_volumes"]
	assert volumes[0]["mot_cle"] == "buy laptop"
	assert volumes[0]["volume"] == 2900
	assert volumes[0]["volumes_mensuels"][0] == {
		"annee": 2023, "mois": 10, "volume": 2400
	}
	assert volumes[0]["date_archive"] == "2026-11-01"
	assert bq.tables["raw.dataforseo_serp"][0]["mot_cle"] == "droit du travail"
	assert bq.tables["raw.dataforseo_intent"] == [{
		"archive_blob": f"dataforseo/{INTENT_ENDPOINT}/2026/11/03/c.json",
		"date_archive": "2026-11-03",
		"mot_cle": "licenciement",
		"intention": "informational",
		"probabilite": 0.9,
	}]
	assert len(bq.tables["ops.archives_chargees"]) == 4
	assert all(
		row["run_id"] == stats.run_id for row in bq.tables["ops.archives_chargees"]
	)


def test_second_run_loads_nothing():
	bq, gcs = FakeBigQuery(), FakeGCS(_blobs())
	load_raw_market(bq, gcs)
	snapshot = {k: list(v) for k, v in bq.tables.items()}

	stats = load_raw_market(bq, gcs)

	assert stats.archives_found == 0
	assert stats.rows_loaded == 0
	assert {k: v for k, v in bq.tables.items()} == snapshot


def test_new_archive_only_is_loaded_on_next_run():
	bq, gcs = FakeBigQuery(), FakeGCS(_blobs())
	load_raw_market(bq, gcs)
	gcs.blobs[f"dataforseo/{INTENT_ENDPOINT}/2026/11/05/e.json"] = _blobs()[
		f"dataforseo/{INTENT_ENDPOINT}/2026/11/03/c.json"
	]

	stats = load_raw_market(bq, gcs)

	assert stats.archives_loaded == 1
	assert len(bq.tables["raw.dataforseo_intent"]) == 2


def test_failed_load_is_not_recorded_and_retried_without_duplicates():
	bq, gcs = FakeBigQuery(), FakeGCS(_blobs())
	bq.fail_on = "raw.dataforseo_serp"
	with pytest.raises(RuntimeError):
		load_raw_market(bq, gcs)
	assert bq.runs[-1]["status"] == "FAILED"
	assert bq.runs[-1]["error"] == "RuntimeError"
	assert json.loads(bq.runs[-1]["counts"])["archives_loaded"] == 2
	bq.fail_on = None
	recorded = {r["archive_blob"] for r in bq.tables["ops.archives_chargees"]}
	assert not any(SERP_ENDPOINT in blob for blob in recorded)

	load_raw_market(bq, gcs)

	volumes = bq.tables["raw.dataforseo_volumes"]
	assert len(volumes) == 1
	assert len(bq.tables["ops.archives_chargees"]) == 4


def test_dry_run_loads_nothing():
	bq, gcs = FakeBigQuery(), FakeGCS(_blobs())

	stats = load_raw_market(bq, gcs, dry_run=True)

	assert stats.status == "DRY_RUN"
	assert stats.archives_found == 4
	assert bq.tables == {}
