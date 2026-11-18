"""Track pipeline executions in BigQuery."""

import json
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from google.cloud import bigquery
from google.cloud.bigquery import QueryJob, ScalarQueryParameter
from google.cloud.bigquery.table import RowIterator

from vil_pipeline.clients.bigquery import BigQueryClient


@dataclass
class TrackedRun:
	"""Mutable execution information captured on completion or failure."""

	run_id: str
	started: datetime
	status: str = "SUCCESS"
	counts: dict[str, object] = field(default_factory=dict)
	estimated_cost: Decimal | None = None
	error: str | None = None


def _error_message(error: BaseException) -> str:
	message = type(error).__name__
	if isinstance(error, BaseExceptionGroup):
		message += " [" + "; ".join(_error_message(e) for e in error.exceptions) + "]"
	return message


def _write(
	client: BigQueryClient | bigquery.Client,
	sql: str,
	params: Sequence[ScalarQueryParameter],
	dataset: bigquery.DatasetReference | None,
) -> None:
	if isinstance(client, BigQueryClient):
		if dataset is not None:
			raise ValueError("A custom dataset requires a native BigQuery client")
		result = client.query(sql, params)
		if isinstance(result, QueryJob):
			raise ValueError("Le client de journalisation ne doit pas être en dry-run")
	else:
		if dataset is None:
			raise ValueError("A dataset is required for a native BigQuery client")
		result = client.query(
			sql,
			job_config=bigquery.QueryJobConfig(
				default_dataset=dataset, query_parameters=list(params)
			),
		).result()
	if isinstance(result, RowIterator) and result.num_dml_affected_rows != 1:
		raise RuntimeError(
			"Le journal BigQuery doit modifier exactement une ligne ; "
			f"lignes modifiées : {result.num_dml_affected_rows}."
		)


@contextmanager
def tracked_run(
	client: BigQueryClient | bigquery.Client,
	job: str,
	*,
	dataset: bigquery.DatasetReference | None = None,
) -> Generator[TrackedRun, None, None]:
	"""Create a RUNNING record, then finalize it, including on failure."""
	if not job.strip():
		raise ValueError("job must not be empty")
	run = TrackedRun(run_id=str(uuid4()), started=datetime.now(UTC))
	table = "`pipeline_runs`" if dataset is not None else "`ops.pipeline_runs`"
	_write(client, f"""
INSERT INTO {table} (run_id, job, debut, statut, compteurs)
VALUES (@run_id, @job, @started, 'RUNNING', PARSE_JSON('{{}}'))
""", [  # noqa: S608
		ScalarQueryParameter("run_id", "STRING", run.run_id),
		ScalarQueryParameter("job", "STRING", job),
		ScalarQueryParameter("started", "TIMESTAMP", run.started),
	], dataset)

	def finish() -> None:
		_write(client, f"""
UPDATE {table}
SET fin = @finished, statut = @status, compteurs = PARSE_JSON(@counts),
    erreur = @error, cout_estime = @cost
WHERE run_id = @run_id AND debut = @started
""", [  # noqa: S608
			ScalarQueryParameter("run_id", "STRING", run.run_id),
			ScalarQueryParameter("started", "TIMESTAMP", run.started),
			ScalarQueryParameter("finished", "TIMESTAMP", datetime.now(UTC)),
			ScalarQueryParameter("status", "STRING", run.status),
			ScalarQueryParameter("counts", "STRING", json.dumps(run.counts)),
			ScalarQueryParameter("error", "STRING", run.error),
			ScalarQueryParameter("cost", "NUMERIC", run.estimated_cost),
		], dataset)

	try:
		yield run
	except BaseException as error:
		run.status = "FAILED"
		run.error = _error_message(error)
		try:
			finish()
		except BaseException as log_error:
			raise BaseExceptionGroup(
				"Job execution and journaling failed", [error, log_error]
			) from None
		raise
	else:
		finish()
