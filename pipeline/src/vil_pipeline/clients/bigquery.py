"""BigQuery client."""

from collections.abc import Iterable, Sequence
from typing import Any

from google.api_core.exceptions import NotFound
from google.cloud import bigquery
from google.cloud.bigquery import LoadJob, QueryJob
from google.cloud.bigquery.job import WriteDisposition
from google.cloud.bigquery.query import ScalarQueryParameter
from google.cloud.bigquery.table import RowIterator


class BigQueryClient:
	"""Thin wrapper around the Google BigQuery client."""

	def __init__(
		self,
		project_id: str,
		location: str | None = None,
		*,
		dry_run: bool = False,
		client: bigquery.Client | None = None,
	) -> None:
		self._location = location
		self._dry_run = dry_run
		self._client = (
			client
			if client is not None
			else bigquery.Client(project=project_id, location=location)
		)

	def query(
		self,
		sql: str,
		parameters: Sequence[ScalarQueryParameter] = (),
	) -> RowIterator | QueryJob:
		"""Run SQL with BigQuery parameters; return the dry-run job when enabled."""
		job = self.query_job(sql, parameters)
		if self._dry_run:
			return job
		return job.result()

	def query_job(
		self,
		sql: str,
		parameters: Sequence[ScalarQueryParameter] = (),
	) -> QueryJob:
		"""Create a query job so callers can inspect its execution statistics."""
		job_config = bigquery.QueryJobConfig(
			query_parameters=list(parameters),
			dry_run=self._dry_run,
		)
		query_options: dict[str, Any] = {"job_config": job_config}
		if self._location is not None:
			query_options["location"] = self._location

		return self._client.query(sql, **query_options)

	def insert(
		self,
		table_id: str,
		rows: Iterable[dict[str, Any]],
		*,
		schema: Sequence[bigquery.SchemaField] | None = None,
		write_disposition: WriteDisposition | None = None,
	) -> LoadJob | None:
		"""Load rows into a table, or do nothing when dry-run mode is enabled."""
		if self._dry_run:
			return None

		job_config = bigquery.LoadJobConfig(
			schema=list(schema) if schema is not None else None,
		)
		if write_disposition is not None:
			job_config.write_disposition = write_disposition
		load_options: dict[str, Any] = {"job_config": job_config}
		if self._location is not None:
			load_options["location"] = self._location

		job = self._client.load_table_from_json(rows, table_id, **load_options)
		job.result()
		return job

	def exists_table(self, table_id: str) -> bool:
		"""Return whether a BigQuery table exists."""
		try:
			self._client.get_table(table_id)
		except NotFound:
			return False
		return True

	def delete_table(self, table_id: str) -> None:
		"""Delete a table, ignoring it if it does not exist."""
		self._client.delete_table(table_id, not_found_ok=True)
