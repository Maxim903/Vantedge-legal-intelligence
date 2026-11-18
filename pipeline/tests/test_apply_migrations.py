"""Tests for BigQuery SQL migrations."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from google.cloud import bigquery

import vil_pipeline.apply_migrations as migrations
from vil_pipeline.apply_migrations import apply_migrations


def _client_with_results(*results):
	client = Mock(spec=bigquery.Client)
	jobs = []
	for result in results:
		job = Mock()
		job.result.return_value = result
		jobs.append(job)
	client.query.side_effect = jobs
	return client


def test_apply_migrations_runs_files_in_order_and_records_each(tmp_path: Path):
	(tmp_path / "0002_second.sql").write_text("SELECT 2", encoding="utf-8")
	(tmp_path / "0001_first.sql").write_text("SELECT 1", encoding="utf-8")
	client = _client_with_results([], [], [], [], [], [], [], [])

	applied = apply_migrations(client, tmp_path)

	assert applied == ["0001_first", "0002_second"]
	query_calls = client.query.call_args_list
	assert query_calls[0].args[0] == "CREATE SCHEMA IF NOT EXISTS `raw`"
	assert query_calls[1].args[0] == "CREATE SCHEMA IF NOT EXISTS `ops`"
	assert "`ops.schema_migrations`" in query_calls[2].args[0]
	assert "applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() NOT NULL" in (
		query_calls[2].args[0]
	)
	assert query_calls[3].args[0] == (
		"SELECT migration_id FROM `ops.schema_migrations`"
	)
	assert query_calls[4].args[0] == "SELECT 1"
	assert query_calls[6].args[0] == "SELECT 2"
	for index, migration_id in ((5, "0001_first"), (7, "0002_second")):
		assert "INSERT INTO `ops.schema_migrations`" in query_calls[index].args[0]
		parameter = query_calls[index].kwargs["job_config"].query_parameters[0]
		assert parameter.name == "migration_id"
		assert parameter.type_ == "STRING"
		assert parameter.value == migration_id


def test_apply_migrations_skips_recorded_migrations(tmp_path: Path):
	(tmp_path / "0001_first.sql").write_text("SELECT 1", encoding="utf-8")
	client = _client_with_results([], [], [], [{"migration_id": "0001_first"}])

	assert apply_migrations(client, tmp_path) == []

	assert client.query.call_count == 4


def test_apply_migrations_propagates_failure_without_recording_migration(
	tmp_path: Path,
):
	(tmp_path / "0001_broken.sql").write_text("INVALID SQL", encoding="utf-8")
	client = _client_with_results([], [], [], [])
	failed_job = Mock()
	failed_job.result.side_effect = RuntimeError("migration failed")
	client.query.side_effect = [
		*client.query.side_effect,
		failed_job,
	]

	with pytest.raises(RuntimeError, match="migration failed"):
		apply_migrations(client, tmp_path)

	assert client.query.call_count == 5


def test_apply_migrations_requires_existing_directory(tmp_path: Path):
	client = Mock(spec=bigquery.Client)

	with pytest.raises(FileNotFoundError):
		apply_migrations(client, tmp_path / "missing")

	client.query.assert_not_called()


def test_article_migrations_match_marts_columns_and_partition_by_load_date():
	migrations_dir = Path(__file__).parents[1] / "sql" / "raw"
	articles_sql = (migrations_dir / "0001_articles.sql").read_text(
		encoding="utf-8",
	)
	versions_sql = (migrations_dir / "0002_article_versions.sql").read_text(
		encoding="utf-8",
	)

	for column in ("article_id STRING", "chapitre_id STRING", "numero STRING"):
		assert column in articles_sql
	for column in (
		"article_version_id STRING",
		"article_id STRING",
		"date_debut DATE",
		"date_fin DATE",
		"etat STRING",
		"texte STRING",
		"texte_ref STRING",
	):
		assert column in versions_sql
	assert articles_sql.count("date_chargement DATE") == 1
	assert versions_sql.count("date_chargement DATE") == 1
	assert "date_chargement DATE DEFAULT CURRENT_DATE() NOT NULL" in articles_sql
	assert "date_chargement DATE DEFAULT CURRENT_DATE() NOT NULL" in versions_sql
	assert "PARTITION BY date_chargement" in articles_sql
	assert "PARTITION BY date_chargement" in versions_sql
	add_text_column_sql = (
		migrations_dir / "0003_article_versions_texte.sql"
	).read_text(encoding="utf-8")
	assert "ADD COLUMN IF NOT EXISTS texte STRING" in add_text_column_sql


def test_extraction_and_pipeline_runs_migration_columns():
	migrations_dir = Path(__file__).parents[1] / "sql" / "raw"
	extractions = (migrations_dir / "0003_entites_extraites.sql").read_text(
		encoding="utf-8"
	)
	runs = (migrations_dir / "0004_ops_pipeline_runs.sql").read_text(
		encoding="utf-8"
	)
	assert "CREATE TABLE IF NOT EXISTS `raw.entites_extraites`" in extractions
	for column in (
		"extraction_id STRING NOT NULL",
		"article_version_id STRING NOT NULL",
		"notion_libelle STRING NOT NULL",
		"situation_de_vie STRING",
		"score_confiance FLOAT64 NOT NULL",
		"modele_llm STRING NOT NULL",
		"version_prompt STRING NOT NULL",
		"extrait_le TIMESTAMP NOT NULL",
		"statut_validation STRING NOT NULL",
		"valide_par STRING",
	):
		assert column in extractions
	assert "PARTITION BY DATE(extrait_le)" in extractions
	assert "CREATE TABLE IF NOT EXISTS `ops.pipeline_runs`" in runs
	for column in (
		"run_id STRING NOT NULL",
		"job STRING NOT NULL",
		"debut TIMESTAMP NOT NULL",
		"fin TIMESTAMP",
		"statut STRING NOT NULL",
		"compteurs JSON",
		"erreur STRING",
		"cout_estime NUMERIC",
	):
		assert column in runs
	assert "PARTITION BY DATE(debut)" in runs
	costs = (migrations_dir / "0006_ops_couts_api.sql").read_text(
		encoding="utf-8"
	)
	assert "CREATE TABLE IF NOT EXISTS `ops.couts_api`" in costs
	for column in (
		"cout_id STRING NOT NULL",
		"lot_id STRING NOT NULL",
		"fournisseur STRING NOT NULL",
		"service STRING NOT NULL",
		"date_cout DATE NOT NULL",
		"montant NUMERIC NOT NULL",
		"devise STRING NOT NULL",
		"details JSON",
	):
		assert column in costs
	assert "PARTITION BY date_cout" in costs


def test_default_migrations_apply_and_record_new_files_in_order():
	migrations_dir = migrations.DEFAULT_MIGRATIONS_DIR
	recorded = [
		{"migration_id": path.stem}
		for path in sorted(migrations_dir.glob("*.sql"))
		if path.stem not in {
			"0003_entites_extraites",
			"0004_ops_pipeline_runs",
			"0006_ops_couts_api",
		}
	]
	client = _client_with_results([], [], [], recorded, [], [], [], [], [], [])

	assert apply_migrations(client) == [
		"0003_entites_extraites",
		"0004_ops_pipeline_runs",
		"0006_ops_couts_api",
	]
	assert "`raw.entites_extraites`" in client.query.call_args_list[4].args[0]
	assert "`ops.pipeline_runs`" in client.query.call_args_list[6].args[0]
	assert "`ops.couts_api`" in client.query.call_args_list[8].args[0]


@pytest.mark.parametrize(
	"applied, output",
	[
		(["0001_articles"], "Applied migration: 0001_articles"),
		([], "No pending migrations."),
	],
)
def test_main_builds_client_from_environment_and_reports_result(
	monkeypatch,
	capsys,
	applied,
	output,
):
	monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
	monkeypatch.setenv("BQ_LOCATION", "EU")
	monkeypatch.setattr(sys, "argv", ["apply-migrations"])
	client = Mock(spec=bigquery.Client)
	client_factory = Mock(return_value=client)
	monkeypatch.setattr(migrations.bigquery, "Client", client_factory)
	apply = Mock(return_value=applied)
	monkeypatch.setattr(migrations, "apply_migrations", apply)

	migrations.main()

	client_factory.assert_called_once_with(project="test-project", location="EU")
	apply.assert_called_once_with(client)
	assert output in capsys.readouterr().out
