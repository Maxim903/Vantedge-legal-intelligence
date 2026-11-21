"""Tests for the pipeline command-line interface."""

import re
import tarfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

from typer.testing import CliRunner

import vil_pipeline.cli as cli
from vil_pipeline.jobs.collect_intent import IntentCollectionStats
from vil_pipeline.jobs.collect_serp import SerpCollectionStats
from vil_pipeline.jobs.collect_volumes import VolumeCollectionStats
from vil_pipeline.jobs.load_corpus import LoadStats, iter_corpus

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "legi"
runner = CliRunner()


def test_load_corpus_command_passes_options_and_prints_summary(
	tmp_path,
	monkeypatch,
):
	archive = tmp_path / "legi.tar.gz"
	archive.touch()
	load = Mock(
		return_value=LoadStats(read=12, inserted=8, updated=2, ignored=2),
	)
	monkeypatch.setattr(cli, "load_corpus", load)
	times = iter((10.0, 12.345))
	monkeypatch.setattr(cli, "perf_counter", lambda: next(times))

	result = runner.invoke(
		cli.app,
		[
			"load-corpus",
			"--archive",
			str(archive),
			"--livre",
			"II",
			"--dry-run",
		],
	)

	assert result.exit_code == 0, result.output
	load.assert_called_once_with(archive, livre="II", dry_run=True)
	assert "lus 12" in result.output
	assert "insérés 8" in result.output
	assert "mis à jour 2" in result.output
	assert "ignorés 2" in result.output
	assert "durée 2.35 s" in result.output


def test_load_corpus_command_requires_archive_option():
	result = runner.invoke(cli.app, ["load-corpus"])

	assert result.exit_code != 0
	assert "--archive" in re.sub(r"\x1b\[[0-9;]*m", "", result.output)


def test_load_corpus_command_help_lists_requested_options():
	result = runner.invoke(cli.app, ["load-corpus", "--help"])

	assert result.exit_code == 0
	output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
	assert "--archive" in output
	assert "--livre" in output
	assert "--dry-run" in output


def test_migrate_command_uses_configured_project_and_location(monkeypatch):
	client = Mock()
	factory = Mock(return_value=client)
	migrate = Mock(return_value=["0003_entites_extraites", "0004_ops_pipeline_runs"])
	monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
	monkeypatch.setenv("BQ_LOCATION", "EU")
	monkeypatch.setattr(cli.bigquery, "Client", factory)
	monkeypatch.setattr(cli, "apply_migrations", migrate)

	result = runner.invoke(cli.app, ["migrate"])

	assert result.exit_code == 0, result.output
	factory.assert_called_once_with(project="test-project", location="EU")
	migrate.assert_called_once_with(client)
	assert "0003_entites_extraites" in result.output
	assert "0004_ops_pipeline_runs" in result.output


def test_migrate_command_reports_no_pending_migrations(monkeypatch):
	monkeypatch.setattr(cli.bigquery, "Client", Mock())
	monkeypatch.setattr(cli, "apply_migrations", Mock(return_value=[]))

	result = runner.invoke(
		cli.app, ["migrate", "--project-id", "test-project", "--location", "EU"]
	)

	assert result.exit_code == 0, result.output
	assert "Aucune migration en attente." in result.output


def test_migrate_command_propagates_migration_failure(monkeypatch):
	monkeypatch.setattr(cli.bigquery, "Client", Mock())
	monkeypatch.setattr(
		cli, "apply_migrations", Mock(side_effect=RuntimeError("migration échouée"))
	)

	result = runner.invoke(cli.app, ["migrate", "--project-id", "test-project"])

	assert result.exit_code != 0
	assert isinstance(result.exception, RuntimeError)
	assert str(result.exception) == "migration échouée"


def test_check_graph_consistency_command_reports_mismatches(monkeypatch):
	from vil_pipeline.jobs.check_graph_consistency import CountDifference

	monkeypatch.setenv("NEO4J_USER", "neo4j")
	monkeypatch.setenv("NEO4J_PASSWORD", "test-secret")
	monkeypatch.setattr(cli.bigquery, "Client", Mock())
	driver = Mock()
	context = Mock()
	context.__enter__ = Mock(return_value=driver)
	context.__exit__ = Mock(return_value=False)
	factory = Mock(return_value=context)
	monkeypatch.setattr(cli.GraphDatabase, "driver", factory)
	check = Mock(return_value=[CountDifference("SE_FONDE_SUR", 2, 3)])
	monkeypatch.setattr(cli, "check_graph_consistency", check)
	args = [
		"check-graph-consistency", "--project-id", "test-project",
		"--neo4j-uri", "bolt://localhost:7687", "--dataset", "test_marts",
	]
	result = runner.invoke(cli.app, args)
	assert result.exit_code == 1
	assert "SE_FONDE_SUR : marts=2, Neo4j=3" in result.output
	assert "test-secret" not in result.output
	assert check.call_args.args[2].dataset_id == "test_marts"
	context.__exit__.assert_called_once()

	check.return_value = []
	result = runner.invoke(cli.app, args)
	assert result.exit_code == 0
	assert "cohérents" in result.output

	check.side_effect = RuntimeError("BigQuery indisponible")
	result = runner.invoke(cli.app, args)
	assert result.exit_code == 1
	assert "Contrôle impossible" in result.output
	assert "BigQuery indisponible" in result.output


def test_check_graph_consistency_requires_neo4j_credentials(monkeypatch):
	monkeypatch.delenv("NEO4J_USER", raising=False)
	monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
	result = runner.invoke(cli.app, [
		"check-graph-consistency", "--project-id", "test-project",
		"--neo4j-uri", "bolt://localhost:7687",
	])
	assert result.exit_code != 0
	assert "NEO4J_USER et NEO4J_PASSWORD" in result.output


def test_extract_entities_dry_run_does_not_create_llm(monkeypatch):
	from decimal import Decimal

	from vil_pipeline.jobs.extract_entities import ExtractionStats

	bq = Mock()
	monkeypatch.setattr(cli, "BigQueryClient", Mock(return_value=bq))
	gemini = Mock()
	monkeypatch.setattr(cli, "GeminiLLMClient", gemini)
	extract = Mock(
		return_value=ExtractionStats(
			run_id="test", read=2, estimated_cost=Decimal("0.2"), dry_run=True
		)
	)
	monkeypatch.setattr(cli, "extract_entities", extract)
	result = runner.invoke(cli.app, [
		"extract-entities", "--project-id", "test-project", "--max-cost", "1",
		"--cost-per-call", "0.1", "--dry-run",
	])
	assert result.exit_code == 0, result.output
	gemini.assert_not_called()
	assert extract.call_args.args == (bq, None)
	assert extract.call_args.kwargs["dry_run"] is True
	assert "coût estimé 0.2" in result.output


def test_extract_entities_uses_model_client_and_closes_it(monkeypatch):
	from vil_pipeline.jobs.extract_entities import ExtractionStats

	monkeypatch.setenv("LLM_API_KEY", "test-secret")
	monkeypatch.setattr(cli, "BigQueryClient", Mock())
	client = Mock()
	context = Mock()
	context.__enter__ = Mock(return_value=client)
	context.__exit__ = Mock(return_value=False)
	gemini = Mock(return_value=context)
	monkeypatch.setattr(cli, "GeminiLLMClient", gemini)
	extract = Mock(return_value=ExtractionStats(run_id="test"))
	monkeypatch.setattr(cli, "extract_entities", extract)
	result = runner.invoke(cli.app, [
		"extract-entities", "--project-id", "test-project", "--max-cost", "1",
		"--cost-per-call", "0.1", "--model", "custom-model",
	])
	assert result.exit_code == 0, result.output
	assert gemini.call_args.kwargs["model"] == "custom-model"
	assert extract.call_args.args[1] is client
	context.__exit__.assert_called_once()
	assert "test-secret" not in result.output


def test_collect_volumes_dry_run_reports_calls_and_estimated_cost(monkeypatch):
	monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
	monkeypatch.setenv("GCS_BUCKET_RAW", "raw-bucket")
	bq = Mock()
	gcs = Mock()
	monkeypatch.setattr(cli, "BigQueryClient", Mock(return_value=bq))
	monkeypatch.setattr(cli, "GCSClient", Mock(return_value=gcs))
	provider = Mock()
	monkeypatch.setattr(cli, "DataForSEOClient", provider)
	stats = VolumeCollectionStats(
		run_id="run-1",
		status="DRY_RUN",
		read=3,
		cached=1,
		calls=2,
		estimated_cost=Decimal("0.15"),
		actual_cost=Decimal("0"),
	)
	collect = Mock(return_value=stats)
	monkeypatch.setattr(cli, "collect_volumes", collect)

	result = runner.invoke(cli.app, [
		"collect-volumes", "--max-cost", "1", "--cost-per-call", "0.075",
		"--dry-run",
	])

	assert result.exit_code == 0, result.output
	collect.assert_called_once_with(
		bq,
		gcs,
		None,
		max_cost=Decimal("1"),
		cost_per_call=Decimal("0.075"),
		dry_run=True,
	)
	provider.assert_not_called()
	assert "appels 2" in result.output
	assert "coût estimé 0.15 USD" in result.output


def test_collect_serp_dry_run_passes_top_n_and_reports_estimate(monkeypatch):
	monkeypatch.setenv("GCS_BUCKET_RAW", "raw-bucket")
	bq, gcs, provider = Mock(), Mock(), Mock()
	monkeypatch.setattr(cli, "BigQueryClient", Mock(return_value=bq))
	monkeypatch.setattr(cli, "GCSClient", Mock(return_value=gcs))
	monkeypatch.setattr(cli, "DataForSEOClient", provider)
	stats = SerpCollectionStats(
		run_id="run-1", status="DRY_RUN", ranked=40, selected=10, cached=3,
		calls=7, estimated_cost=Decimal("0.021"), actual_cost=Decimal("0"),
	)
	collect = Mock(return_value=stats)
	monkeypatch.setattr(cli, "collect_serp", collect)

	result = runner.invoke(cli.app, [
		"collect-serp", "--top-n", "10", "--max-cost", "1",
		"--cost-per-call", "0.003", "--project-id", "test-project", "--dry-run",
	])

	assert result.exit_code == 0, result.output
	collect.assert_called_once_with(
		bq, gcs, None, top_n=10, max_cost=Decimal("1"),
		cost_per_call=Decimal("0.003"), dry_run=True,
	)
	provider.assert_not_called()
	assert "appels 7" in result.output
	assert "coût estimé 0.021 USD" in result.output


def test_collect_serp_requires_a_positive_top_n():
	result = runner.invoke(cli.app, [
		"collect-serp", "--top-n", "0", "--max-cost", "1",
		"--cost-per-call", "0.003", "--project-id", "test-project",
	])

	assert result.exit_code != 0


def test_collect_intent_command_passes_options_and_reports_summary(monkeypatch):
	bq = Mock()
	monkeypatch.setattr(cli, "BigQueryClient", Mock(return_value=bq))
	stats = IntentCollectionStats(
		run_id="run-intent",
		status="SUCCESS",
		read=10,
		classified=10,
		distribution={"informationnelle": 7, "transactionnelle": 3},
	)
	collect = Mock(return_value=stats)
	monkeypatch.setattr(cli, "collect_intent", collect)

	result = runner.invoke(cli.app, [
		"collect-intent", "--project-id", "test-project", "--location", "EU",
		"--dry-run",
	])

	assert result.exit_code == 0, result.output
	collect.assert_called_once_with(bq, dry_run=True)
	assert "requêtes 10" in result.output
	assert "classées 10" in result.output
	assert "informationnelle" in result.output


def test_evaluate_extraction_command_passes_options(tmp_path, monkeypatch):
	client = Mock()
	monkeypatch.setattr(cli, "BigQueryClient", Mock(return_value=client))
	report = tmp_path / "report.md"
	evaluate = Mock(return_value=report)
	monkeypatch.setattr(cli, "evaluate_extraction", evaluate)
	result = runner.invoke(cli.app, [
		"evaluate-extraction", "--project-id", "test-project", "--location", "EU",
		"--model", "test-model", "--version-prompt", "prompt-hash",
		"--golden", str(tmp_path / "golden.csv"),
		"--titles", str(tmp_path / "titres.csv"), "--output", str(report),
	])
	assert result.exit_code == 0, result.output
	assert evaluate.call_args.args == (client,)
	assert evaluate.call_args.kwargs == {
		"model": "test-model", "version_prompt": "prompt-hash",
		"golden_path": tmp_path / "golden.csv",
		"titles_path": tmp_path / "titres.csv", "output_path": report,
	}
	assert str(report) in result.output


def test_export_review_command_passes_options(tmp_path, monkeypatch):
	client = Mock()
	monkeypatch.setattr(cli, "BigQueryClient", Mock(return_value=client))
	export = Mock(return_value=2)
	monkeypatch.setattr(cli, "export_review", export)
	output = tmp_path / "review.csv"
	result = runner.invoke(cli.app, [
		"export-review", "--project-id", "test-project", "--location", "EU",
		"--output", str(output), "--threshold", "0.8",
	])
	assert result.exit_code == 0, result.output
	export.assert_called_once_with(client, output, threshold=0.8)
	assert "Entités exportées : 2" in result.output


def test_import_review_command_passes_options(tmp_path, monkeypatch):
	client = Mock()
	monkeypatch.setattr(cli, "BigQueryClient", Mock(return_value=client))
	importer = Mock(return_value=1)
	monkeypatch.setattr(cli, "import_review", importer)
	source = tmp_path / "review.csv"
	source.touch()
	result = runner.invoke(cli.app, [
		"import-review", "--project-id", "test-project", "--input", str(source),
	])
	assert result.exit_code == 0, result.output
	importer.assert_called_once_with(client, source)
	assert "Décisions importées : 1" in result.output


def test_iter_corpus_reads_xml_members_from_tar_archive(tmp_path):
	archive_path = tmp_path / "legi.tar.gz"
	with tarfile.open(archive_path, "w:gz") as archive:
		archive.add(FIXTURES_DIR / "article_vigueur.xml", arcname="article.xml")

	result = list(iter_corpus(archive_path, livre="II"))

	assert len(result) == 1
	assert result[0][0].article_id == "LEGIARTI000006901674"


def test_load_raw_market_reports_counts(monkeypatch):
	monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
	monkeypatch.setenv("GCS_BUCKET_RAW", "raw-bucket")
	bq, gcs = Mock(), Mock()
	monkeypatch.setattr(cli, "BigQueryClient", Mock(return_value=bq))
	monkeypatch.setattr(cli, "GCSClient", Mock(return_value=gcs))
	stats = Mock(status="SUCCESS", archives_found=3, archives_loaded=3, rows_loaded=9)
	load = Mock(return_value=stats)
	monkeypatch.setattr(cli, "load_raw_market", load)

	result = runner.invoke(cli.app, ["load-raw-market"])

	assert result.exit_code == 0, result.output
	load.assert_called_once_with(bq, gcs, dry_run=False)
	assert "chargées 3" in result.output
