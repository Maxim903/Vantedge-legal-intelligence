"""Load archived DataForSEO responses from GCS into the raw BigQuery tables."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import PurePosixPath
from typing import Any, cast

from google.cloud import bigquery
from google.cloud.bigquery import QueryJob, ScalarQueryParameter
from google.cloud.bigquery.job import WriteDisposition

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.clients.gcs import GCSClient
from vil_pipeline.jobs.collect_serp import SERP_ENDPOINT
from vil_pipeline.jobs.collect_volumes import ENDPOINT as VOLUME_ENDPOINT
from vil_pipeline.tracking import tracked_run

INTENT_ENDPOINT = "dataforseo_labs/google/search_intent/live"

_APPEND = cast(WriteDisposition, bigquery.WriteDisposition.WRITE_APPEND)
_LOADED_SQL = "SELECT archive_blob FROM `ops.archives_chargees`"


_COMMON_FIELDS = [
	bigquery.SchemaField("archive_blob", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("date_archive", "DATE", mode="REQUIRED"),
	bigquery.SchemaField("mot_cle", "STRING", mode="REQUIRED"),
]
_VOLUMES_SCHEMA = [
	*_COMMON_FIELDS,
	bigquery.SchemaField("localisation", "INT64"),
	bigquery.SchemaField("langue", "STRING"),
	bigquery.SchemaField("volume", "INT64"),
	bigquery.SchemaField("concurrence", "STRING"),
	bigquery.SchemaField("indice_concurrence", "INT64"),
	bigquery.SchemaField("cpc", "FLOAT64"),
	bigquery.SchemaField("cpc_bas", "FLOAT64"),
	bigquery.SchemaField("cpc_haut", "FLOAT64"),
	bigquery.SchemaField(
		"volumes_mensuels",
		"RECORD",
		mode="REPEATED",
		fields=[
			bigquery.SchemaField("annee", "INT64"),
			bigquery.SchemaField("mois", "INT64"),
			bigquery.SchemaField("volume", "INT64"),
		],
	),
]
_SERP_SCHEMA = [
	*_COMMON_FIELDS,
	bigquery.SchemaField("localisation", "INT64"),
	bigquery.SchemaField("langue", "STRING"),
	bigquery.SchemaField("type_resultat", "STRING"),
	bigquery.SchemaField("rang_groupe", "INT64"),
	bigquery.SchemaField("rang_absolu", "INT64"),
	bigquery.SchemaField("domaine", "STRING"),
	bigquery.SchemaField("titre", "STRING"),
	bigquery.SchemaField("url", "STRING"),
]
_INTENT_SCHEMA = [
	*_COMMON_FIELDS,
	bigquery.SchemaField("intention", "STRING"),
	bigquery.SchemaField("probabilite", "FLOAT64"),
]
_LOADED_SCHEMA = [
	bigquery.SchemaField("archive_blob", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("endpoint", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("table_cible", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("lignes", "INT64", mode="REQUIRED"),
	bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("date_chargement", "TIMESTAMP", mode="REQUIRED"),
]


def _results(payload: dict[str, Any]) -> list[dict[str, Any]]:
	"""Results of successful tasks; failed tasks carry no result."""
	return [
		result
		for task in payload.get("tasks") or []
		if task.get("status_code") == 20000
		for result in task.get("result") or []
	]


def _volume_rows(
	payload: dict[str, Any], base: dict[str, Any]
) -> Iterator[dict[str, Any]]:
	for result in _results(payload):
		yield {
			**base,
			"mot_cle": result["keyword"],
			"localisation": result.get("location_code"),
			"langue": result.get("language_code"),
			"volume": result.get("search_volume"),
			"concurrence": result.get("competition"),
			"indice_concurrence": result.get("competition_index"),
			"cpc": result.get("cpc"),
			"cpc_bas": result.get("low_top_of_page_bid"),
			"cpc_haut": result.get("high_top_of_page_bid"),
			"volumes_mensuels": [
				{
					"annee": month.get("year"),
					"mois": month.get("month"),
					"volume": month.get("search_volume"),
				}
				for month in result.get("monthly_searches") or []
			],
		}


def _serp_rows(
	payload: dict[str, Any], base: dict[str, Any]
) -> Iterator[dict[str, Any]]:
	for result in _results(payload):
		for item in result.get("items") or []:
			yield {
				**base,
				"mot_cle": result["keyword"],
				"localisation": result.get("location_code"),
				"langue": result.get("language_code"),
				"type_resultat": item.get("type"),
				"rang_groupe": item.get("rank_group"),
				"rang_absolu": item.get("rank_absolute"),
				"domaine": item.get("domain"),
				"titre": item.get("title"),
				"url": item.get("url"),
			}


def _intent_rows(
	payload: dict[str, Any], base: dict[str, Any]
) -> Iterator[dict[str, Any]]:
	for result in _results(payload):
		for item in result.get("items") or []:
			intent = item.get("keyword_intent") or {}
			yield {
				**base,
				"mot_cle": item["keyword"],
				"intention": intent.get("label"),
				"probabilite": intent.get("probability"),
			}


@dataclass(frozen=True)
class _Target:
	table: str
	schema: list[bigquery.SchemaField]
	rows: Callable[[dict[str, Any], dict[str, Any]], Iterator[dict[str, Any]]]


_TARGETS: dict[str, _Target] = {
	VOLUME_ENDPOINT: _Target(
		"raw.dataforseo_volumes", _VOLUMES_SCHEMA, _volume_rows
	),
	SERP_ENDPOINT: _Target("raw.dataforseo_serp", _SERP_SCHEMA, _serp_rows),
	INTENT_ENDPOINT: _Target(
		"raw.dataforseo_intent", _INTENT_SCHEMA, _intent_rows
	),
}


@dataclass(frozen=True)
class RawMarketLoadStats:
	run_id: str
	status: str
	archives_found: int
	archives_loaded: int
	rows_loaded: int


def _archive_date(blob_name: str) -> date:
	parts = PurePosixPath(blob_name).parts
	return date(int(parts[-4]), int(parts[-3]), int(parts[-2]))


def load_raw_market(
	client: BigQueryClient,
	gcs: GCSClient,
	*,
	dry_run: bool = False,
) -> RawMarketLoadStats:
	"""Load every not-yet-loaded archive into its raw table via load jobs.

	An archive is recorded in ``ops.archives_chargees`` only after its rows are
	loaded; rows left by an interrupted attempt are deleted before reloading,
	so the job can be re-run safely.
	"""
	found = loaded = row_count = 0

	with tracked_run(client, "load_raw_market") as run:
		try:
			query_result = client.query(_LOADED_SQL)
			if isinstance(query_result, QueryJob):
				raise ValueError("Le client BigQuery ne doit pas être en mode dry-run")
			done = {row["archive_blob"] for row in query_result}

			pending: list[tuple[str, str]] = []
			for endpoint in _TARGETS:
				prefix = f"dataforseo/{endpoint}/"
				pending.extend(
					(endpoint, name)
					for name in sorted(gcs.list_blob_names(prefix))
					if name.endswith(".json") and name not in done
				)
			found = len(pending)

			if dry_run:
				run.status = "DRY_RUN"
			for endpoint, blob_name in [] if dry_run else pending:
				target = _TARGETS[endpoint]
				base = {
					"archive_blob": blob_name,
					"date_archive": _archive_date(blob_name).isoformat(),
				}
				rows = list(target.rows(gcs.download_json(blob_name), base))
				client.query(
					f"DELETE FROM `{target.table}` WHERE archive_blob = @blob",  # noqa: S608
					[ScalarQueryParameter("blob", "STRING", blob_name)],
				)
				if rows:
					client.insert(
						target.table,
						rows,
						schema=target.schema,
						write_disposition=_APPEND,
					)
				client.insert(
					"ops.archives_chargees",
					[{
						"archive_blob": blob_name,
						"endpoint": endpoint,
						"table_cible": target.table,
						"lignes": len(rows),
						"run_id": run.run_id,
						"date_chargement": datetime.now(UTC).isoformat(),
					}],
					schema=_LOADED_SCHEMA,
					write_disposition=_APPEND,
				)
				loaded += 1
				row_count += len(rows)
		except BaseException:
			run.status = "FAILED"
			raise
		finally:
			run.counts = {
				"status": run.status,
				"archives_found": found,
				"archives_loaded": loaded,
				"rows_loaded": row_count,
			}
	return RawMarketLoadStats(run.run_id, run.status, found, loaded, row_count)
