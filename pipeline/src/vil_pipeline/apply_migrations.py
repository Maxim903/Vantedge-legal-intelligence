"""Apply ordered BigQuery SQL migrations."""

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

from google.cloud import bigquery
from google.cloud.bigquery.query import ScalarQueryParameter
from google.cloud.bigquery.table import RowIterator

DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "sql" / "raw"

_CREATE_DATASETS_SQL = (
	"CREATE SCHEMA IF NOT EXISTS `raw`",
	"CREATE SCHEMA IF NOT EXISTS `ops`",
)
_CREATE_MIGRATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `ops.schema_migrations` (
  migration_id STRING NOT NULL,
  applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() NOT NULL
)
"""
_LIST_MIGRATIONS_SQL = "SELECT migration_id FROM `ops.schema_migrations`"
_RECORD_MIGRATION_SQL = """
INSERT INTO `ops.schema_migrations` (migration_id)
VALUES (@migration_id)
"""


def _query(
	client: bigquery.Client,
	sql: str,
	parameters: Sequence[ScalarQueryParameter] = (),
) -> RowIterator:
	job = client.query(
		sql,
		job_config=bigquery.QueryJobConfig(query_parameters=list(parameters)),
	)
	return job.result()


def apply_migrations(
	client: bigquery.Client,
	migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
) -> list[str]:
	"""Apply unapplied migration files in lexical filename order."""
	if not migrations_dir.is_dir():
		raise FileNotFoundError(f"Migration directory not found: {migrations_dir}")

	for sql in _CREATE_DATASETS_SQL:
		_query(client, sql)
	_query(client, _CREATE_MIGRATIONS_TABLE_SQL)
	applied = {row["migration_id"] for row in _query(client, _LIST_MIGRATIONS_SQL)}

	newly_applied: list[str] = []
	for migration_path in sorted(migrations_dir.glob("*.sql")):
		migration_id = migration_path.stem
		if migration_id in applied:
			continue

		_query(client, migration_path.read_text(encoding="utf-8"))
		_query(
			client,
			_RECORD_MIGRATION_SQL,
			[ScalarQueryParameter("migration_id", "STRING", migration_id)],
		)
		newly_applied.append(migration_id)

	return newly_applied


def main() -> None:
	"""Run migrations using the configured GCP project and BigQuery location."""
	parser = argparse.ArgumentParser(description="Apply BigQuery SQL migrations.")
	project_id = os.environ.get("GCP_PROJECT_ID")
	parser.add_argument(
		"--project-id",
		default=project_id,
		required=project_id is None,
		help="GCP project ID (defaults to GCP_PROJECT_ID).",
	)
	parser.add_argument(
		"--location",
		default=os.environ.get("BQ_LOCATION"),
		help="BigQuery location (defaults to BQ_LOCATION).",
	)
	args = parser.parse_args()

	client = bigquery.Client(project=args.project_id, location=args.location)
	applied = apply_migrations(client)
	for migration_id in applied:
		print(f"Applied migration: {migration_id}")
	if not applied:
		print("No pending migrations.")


if __name__ == "__main__":
	main()
