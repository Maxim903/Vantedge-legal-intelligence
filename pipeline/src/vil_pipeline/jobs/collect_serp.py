"""Collect the top-10 Google results for the highest-volume candidate queries."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from google.cloud.bigquery import QueryJob

from vil_pipeline.archive import archive_dataforseo_response
from vil_pipeline.cache import find_fresh_archive_keys, list_fresh_archive_blobs
from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.clients.dataforseo import SerpResponse
from vil_pipeline.clients.gcs import GCSClient
from vil_pipeline.config import DATAFORSEO_TTL_JOURS
from vil_pipeline.jobs.collect_volumes import (
	_COST_SCHEMA,
	LANGUAGE_CODE_FRENCH,
	LOCATION_CODE_FRANCE,
	_decimal,
)
from vil_pipeline.jobs.collect_volumes import ENDPOINT as VOLUME_ENDPOINT
from vil_pipeline.keys import idempotency_key
from vil_pipeline.tracking import tracked_run

SERP_ENDPOINT = "serp/google/organic/live/regular"
SERP_DEPTH = 10

_CANDIDATES_SQL = """
SELECT DISTINCT requete
FROM `raw.requetes_candidates`
WHERE requete IS NOT NULL AND TRIM(requete) != ''
ORDER BY requete
"""



class SerpProvider(Protocol):
	def serp_organic(
		self,
		keyword: str,
		*,
		location_code: int,
		language_code: str,
		depth: int = SERP_DEPTH,
	) -> SerpResponse: ...


@dataclass(frozen=True)
class SerpCollectionStats:
	run_id: str
	status: str
	ranked: int
	selected: int
	cached: int
	calls: int
	estimated_cost: Decimal
	actual_cost: Decimal


def _archived_volumes(
	gcs: GCSClient, candidates: set[str], today: date
) -> dict[str, int]:
	"""Latest fresh archived volume per candidate keyword."""
	blobs = list_fresh_archive_blobs(
		VOLUME_ENDPOINT,
		DATAFORSEO_TTL_JOURS[VOLUME_ENDPOINT],
		client=gcs,
		today=today,
	)
	volumes: dict[str, int] = {}
	for blob_name in blobs:
		payload = gcs.download_json(blob_name)
		for task in payload.get("tasks") or []:
			for result in task.get("result") or []:
				keyword = " ".join(str(result.get("keyword", "")).casefold().split())
				volume = result.get("search_volume")
				if keyword in candidates and isinstance(volume, int):
					volumes[keyword] = volume
	return volumes


def collect_serp(
	client: BigQueryClient,
	gcs: GCSClient,
	provider: SerpProvider | None,
	*,
	top_n: int,
	max_cost: Decimal | float | int,
	cost_per_call: Decimal | float | int,
	dry_run: bool = False,
	period: str | None = None,
	today: date | None = None,
) -> SerpCollectionStats:
	"""Fetch, archive and cost the SERP of the top-N volume queries (France/fr)."""
	ranked = selected_count = cached = calls = 0
	estimated_cost = Decimal(0)
	actual_cost = Decimal(0)
	cost_rows: list[dict[str, object]] = []
	job_error: BaseException | None = None

	with tracked_run(client, "collect_serp") as run:
		try:
			if top_n < 1:
				raise ValueError("top_n must be at least one")
			maximum = _decimal(max_cost, "max_cost", allow_zero=True)
			unit_cost = _decimal(cost_per_call, "cost_per_call", allow_zero=False)
			if not dry_run and provider is None:
				raise ValueError("provider is required unless dry_run is enabled")

			current_date = today or datetime.now(UTC).date()
			request_period = period or current_date.strftime("%Y-%m")
			try:
				date.fromisoformat(f"{request_period}-01")
			except ValueError as error:
				raise ValueError("period must use YYYY-MM format") from error


			query_result = client.query(_CANDIDATES_SQL)
			if isinstance(query_result, QueryJob):
				raise ValueError("Le client BigQuery ne doit pas être en mode dry-run")
			candidates = {
				" ".join(row["requete"].casefold().split())
				for row in query_result
				if isinstance(row.get("requete"), str) and row["requete"].strip()
			}
			volumes = _archived_volumes(gcs, candidates, current_date)
			ranked = len(volumes)
			top = sorted(
				volumes, key=lambda keyword: (-volumes[keyword], keyword)
			)[:top_n]
			selected_count = len(top)

			fresh_keys = find_fresh_archive_keys(
				SERP_ENDPOINT,
				DATAFORSEO_TTL_JOURS[SERP_ENDPOINT],
				client=gcs,
				today=current_date,
			)
			uncached = [
				keyword
				for keyword in top
				if idempotency_key(
					SERP_ENDPOINT,
					keyword,
					LOCATION_CODE_FRANCE,
					LANGUAGE_CODE_FRENCH,
					request_period,
				) not in fresh_keys
			]
			cached = selected_count - len(uncached)

			if not volumes:
				run.status = "NO_VOLUME_DATA"
			elif dry_run:
				calls = len(uncached)
				estimated_cost = calls * unit_cost
				run.status = (
					"DRY_RUN_OVER_BUDGET" if estimated_cost > maximum else "DRY_RUN"
				)
			else:
				for keyword in uncached:
					if estimated_cost + unit_cost > maximum:
						run.status = "BUDGET_EXHAUSTED"
						break
					estimated_cost += unit_cost
					calls += 1
					if provider is None:
						raise RuntimeError("DataForSEO provider missing")
					response = provider.serp_organic(
						keyword,
						location_code=LOCATION_CODE_FRANCE,
						language_code=LANGUAGE_CODE_FRENCH,
						depth=SERP_DEPTH,
					)
					if response.status_code != 20000 or response.tasks_error:
						raise RuntimeError(
							"DataForSEO reported an unsuccessful SERP task"
						)
					call_cost = Decimal(str(response.cost))
					actual_cost += call_cost
					# Record first so a GCS failure cannot hide a billed call.
					cost_rows.append({
						"cout_id": str(uuid4()),
						"lot_id": run.run_id,
						"fournisseur": "DataForSEO",
						"service": SERP_ENDPOINT,
						"date_cout": current_date,
						"montant": call_cost,
						"devise": "USD",
						"details": {
							"mot_cle": keyword,
							"localisation": LOCATION_CODE_FRANCE,
							"langue": LANGUAGE_CODE_FRENCH,
							"periode": request_period,
						},
					})
					archive_dataforseo_response(
						gcs,
						response,
						endpoint=SERP_ENDPOINT,
						mot_cle=keyword,
						localisation=LOCATION_CODE_FRANCE,
						langue=LANGUAGE_CODE_FRENCH,
						periode=request_period,
						cout=call_cost,
						date_archive=current_date,
					)
		except BaseException as error:
			job_error = error
			run.status = "FAILED"
			raise
		finally:
			try:
				if cost_rows:
					client.insert("ops.couts_api", cost_rows, schema=_COST_SCHEMA)
			except BaseException as cost_error:
				run.status = "FAILED"
				if job_error is not None:
					raise BaseExceptionGroup(
						"Job execution and cost persistence failed",
						[job_error, cost_error],
					) from None
				raise
			finally:
				run.counts = {
					"status": run.status, "ranked": ranked,
					"selected": selected_count, "cached": cached, "calls": calls,
				}
				run.estimated_cost = estimated_cost
	stats = SerpCollectionStats(
		run.run_id, run.status, ranked, selected_count, cached, calls,
		estimated_cost, actual_cost,
	)
	return stats
