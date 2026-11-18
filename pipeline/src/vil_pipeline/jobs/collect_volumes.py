"""Collect uncached Google Ads search volumes for candidate queries."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from google.cloud import bigquery
from google.cloud.bigquery import QueryJob

from vil_pipeline.archive import archive_dataforseo_response
from vil_pipeline.cache import find_fresh_archive_keys
from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.clients.dataforseo import SearchVolumeResponse
from vil_pipeline.clients.gcs import GCSClient
from vil_pipeline.config import DATAFORSEO_TTL_JOURS
from vil_pipeline.keys import idempotency_key
from vil_pipeline.tracking import tracked_run

ENDPOINT = "keywords_data/google_ads/search_volume/live"
LOCATION_CODE_FRANCE = 2250
LANGUAGE_CODE_FRENCH = "fr"

_CANDIDATES_SQL = """
SELECT DISTINCT requete
FROM `raw.requetes_candidates`
WHERE requete IS NOT NULL AND TRIM(requete) != ''
ORDER BY requete
"""

_COST_SCHEMA = [
	bigquery.SchemaField("cout_id", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("lot_id", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("fournisseur", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("service", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("date_cout", "DATE", mode="REQUIRED"),
	bigquery.SchemaField("montant", "NUMERIC", mode="REQUIRED"),
	bigquery.SchemaField("devise", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("details", "JSON"),
]


class VolumeProvider(Protocol):
	def search_volume(
		self,
		keywords: Sequence[str],
		*,
		location_code: int,
		language_code: str | None = None,
	) -> SearchVolumeResponse: ...


@dataclass(frozen=True)
class VolumeCollectionStats:
	run_id: str
	status: str
	read: int
	cached: int
	calls: int
	estimated_cost: Decimal
	actual_cost: Decimal


def _decimal(value: Decimal | float | int, name: str, *, allow_zero: bool) -> Decimal:
	try:
		result = Decimal(str(value))
	except Exception as error:
		raise ValueError(f"{name} must be a finite decimal") from error
	if not result.is_finite() or result < 0 or (not allow_zero and result == 0):
		qualifier = "non-negative" if allow_zero else "positive"
		raise ValueError(f"{name} must be finite and {qualifier}")
	exponent = result.as_tuple().exponent
	if not isinstance(exponent, int) or exponent < -9:
		qualifier = "non-negative" if allow_zero else "positive"
		raise ValueError(
			f"{name} must be {qualifier} with at most 9 decimals"
		)
	return result


def collect_volumes(
	client: BigQueryClient,
	gcs: GCSClient,
	provider: VolumeProvider | None,
	*,
	max_cost: Decimal | float | int,
	cost_per_call: Decimal | float | int,
	dry_run: bool = False,
	period: str | None = None,
	today: date | None = None,
) -> VolumeCollectionStats:
	"""Fetch, archive and cost uncached candidate keywords for France/French."""
	read = cached = calls = 0
	estimated_cost = Decimal(0)
	actual_cost = Decimal(0)
	cost_rows: list[dict[str, object]] = []
	job_error: BaseException | None = None

	with tracked_run(client, "collect_volumes") as run:
		try:
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
			queries = sorted({
				" ".join(row["requete"].casefold().split())
				for row in query_result
				if isinstance(row.get("requete"), str) and row["requete"].strip()
			})
			read = len(queries)
			fresh_keys = find_fresh_archive_keys(
				ENDPOINT,
				DATAFORSEO_TTL_JOURS[ENDPOINT],
				client=gcs,
				today=current_date,
			)
			uncached = [
				keyword
				for keyword in queries
				if idempotency_key(
					ENDPOINT,
					keyword,
					LOCATION_CODE_FRANCE,
					LANGUAGE_CODE_FRENCH,
					request_period,
				) not in fresh_keys
			]
			cached = read - len(uncached)

			if dry_run:
				calls = len(uncached)
				estimated_cost = calls * unit_cost
				if estimated_cost > maximum:
					run.status = "DRY_RUN_OVER_BUDGET"
				else:
					run.status = "DRY_RUN"
			else:
				for keyword in uncached:
					if estimated_cost + unit_cost > maximum:
						run.status = "BUDGET_EXHAUSTED"
						break
					estimated_cost += unit_cost
					calls += 1
					if provider is None:
						raise RuntimeError("DataForSEO provider missing")
					response = provider.search_volume(
						[keyword],
						location_code=LOCATION_CODE_FRANCE,
						language_code=LANGUAGE_CODE_FRENCH,
					)
					if response.status_code != 20000 or response.tasks_error:
						raise RuntimeError(
							"DataForSEO reported an unsuccessful search-volume task"
						)
					call_cost = Decimal(str(response.cost))
					actual_cost += call_cost
					cost_rows.append({
						"cout_id": str(uuid4()),
						"lot_id": run.run_id,
						"fournisseur": "DataForSEO",
						"service": ENDPOINT,
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
						endpoint=ENDPOINT,
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
					"status": run.status, "read": read, "cached": cached,
					"calls": calls,
				}
				run.estimated_cost = estimated_cost
	stats = VolumeCollectionStats(
		run.run_id, run.status, read, cached, calls, estimated_cost, actual_cost
	)
	return stats