"""Review queue tests with BigQuery doubles; no network access."""

import csv
import json
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from google.cloud.bigquery import QueryJob

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.jobs.review_queue import export_review, import_review


def entity(id_="id-1", *, status="AUTO", reviewer=None):
	return {
		"extraction_id": id_, "article_version_id": "LEGIARTI000006901674",
		"notion_libelle": "Congé, payé", "situation_de_vie": None,
		"score_confiance": 0.3, "modele_llm": "modèle", "version_prompt": "hash",
		"extrait_le": datetime(2026, 1, 1, tzinfo=UTC),
		"statut_validation": status, "valide_par": reviewer,
	}


def read_csv(path):
	with path.open(encoding="utf-8", newline="") as stream:
		reader = csv.DictReader(stream)
		return reader.fieldnames, list(reader)


def write_csv(path, fields, rows):
	with path.open("w", encoding="utf-8", newline="") as stream:
		writer = csv.DictWriter(stream, fieldnames=fields)
		writer.writeheader()
		writer.writerows(rows)


def test_export_filters_with_bound_threshold_and_writes_review_columns(tmp_path):
	client = Mock(spec=BigQueryClient)
	client.query.return_value = [
		entity(), entity("id-2", status="A_REVOIR", reviewer="Élodie")
	]
	path = tmp_path / "nested" / "review.csv"
	assert export_review(client, path, threshold=0.8) == 2
	sql, params = client.query.call_args.args
	assert "statut_validation = 'A_REVOIR' OR score_confiance < @threshold" in sql
	assert params[0].name == "threshold"
	assert params[0].value == 0.8
	fields, rows = read_csv(path)
	assert fields[-4:] == [
		"statut_validation", "valide_par_initial_json", "nouveau_statut",
		"nouveau_valide_par",
	]
	assert rows[0]["notion_libelle"] == "Congé, payé"
	assert rows[0]["valide_par_initial_json"] == "null"
	assert json.loads(rows[1]["valide_par_initial_json"]) == "Élodie"
	assert rows[0]["nouveau_statut"] == rows[0]["nouveau_valide_par"] == ""
	with pytest.raises(FileExistsError):
		export_review(client, path, threshold=0.8)


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_threshold_fails_without_query(tmp_path, threshold):
	client = Mock(spec=BigQueryClient)
	with pytest.raises(ValueError, match="seuil"):
		export_review(client, tmp_path / "review.csv", threshold=threshold)
	client.query.assert_not_called()


def test_export_rejects_duplicate_ids(tmp_path):
	client = Mock(spec=BigQueryClient)
	client.query.return_value = [entity(), entity()]
	path = tmp_path / "review.csv"
	with pytest.raises(ValueError, match="dupliqué"):
		export_review(client, path, threshold=0)
	assert not path.exists()


def test_empty_export_is_importable_without_writes(tmp_path):
	client = Mock(spec=BigQueryClient)
	client.query.return_value = []
	path = tmp_path / "review.csv"
	assert export_review(client, path, threshold=0) == 0
	client.reset_mock()
	assert import_review(client, path) == 0
	client.query.assert_not_called()


def test_import_updates_only_decided_rows_with_transaction_and_original_state(tmp_path):
	client = Mock(spec=BigQueryClient)
	client.query.return_value = [entity(), entity("id-2", reviewer="ancien")]
	path = tmp_path / "review.csv"
	export_review(client, path, threshold=0.5)
	fields, rows = read_csv(path)
	rows[0]["nouveau_statut"] = "VALIDE"
	rows[0]["nouveau_valide_par"] = " Anne "
	rows[1]["nouveau_statut"] = "REJETE"
	rows[1]["nouveau_valide_par"] = "Bob"
	write_csv(path, fields, rows)
	client.reset_mock()
	client.query.return_value = []
	assert import_review(client, path) == 2
	sql, params = client.query.call_args.args
	assert "BEGIN TRANSACTION" in sql and "COMMIT TRANSACTION" in sql
	assert "COUNT(e.extraction_id) != 1" in sql
	assert "e.valide_par IS NOT DISTINCT FROM r.valide_par_initial" in sql
	assert "e.statut_validation = r.statut_initial" in sql
	assert "ASSERT @@row_count" in sql
	assert json.loads(params[0].value) == [
		{
			"extraction_id": "id-1", "statut_initial": "AUTO",
			"valide_par_initial": None, "nouveau_statut": "VALIDE",
			"nouveau_valide_par": "Anne",
		},
		{
			"extraction_id": "id-2", "statut_initial": "AUTO",
			"valide_par_initial": "ancien", "nouveau_statut": "REJETE",
			"nouveau_valide_par": "Bob",
		},
	]


@pytest.mark.parametrize(("status", "reviewer"), [
	("VALIDE", ""), ("", "Anne"), ("AUTO", "Anne"), ("INVALIDE", "Anne"),
])
def test_import_rejects_incomplete_or_invalid_decisions_before_write(
	tmp_path, status, reviewer
):
	client = Mock(spec=BigQueryClient)
	client.query.return_value = [entity(), entity("id-2")]
	path = tmp_path / "review.csv"
	export_review(client, path, threshold=0.5)
	fields, rows = read_csv(path)
	rows[0]["nouveau_statut"], rows[0]["nouveau_valide_par"] = "VALIDE", "Bob"
	rows[1]["nouveau_statut"], rows[1]["nouveau_valide_par"] = status, reviewer
	write_csv(path, fields, rows)
	client.reset_mock()
	with pytest.raises(ValueError, match="Décision ou validateur"):
		import_review(client, path)
	client.query.assert_not_called()


def test_import_duplicate_and_invalid_header_are_rejected(tmp_path):
	client = Mock(spec=BigQueryClient)
	client.query.return_value = [entity()]
	path = tmp_path / "review.csv"
	export_review(client, path, threshold=0.5)
	fields, rows = read_csv(path)
	write_csv(path, fields, rows * 2)
	client.reset_mock()
	with pytest.raises(ValueError, match="dupliqué"):
		import_review(client, path)
	client.query.assert_not_called()
	path.write_text("extraction_id,nouveau_statut\nid-1,VALIDE\n", encoding="utf-8")
	with pytest.raises(ValueError, match="Colonnes"):
		import_review(client, path)


def test_import_propagates_transaction_failure(tmp_path):
	client = Mock(spec=BigQueryClient)
	client.query.return_value = [entity()]
	path = tmp_path / "review.csv"
	export_review(client, path, threshold=0.5)
	fields, rows = read_csv(path)
	rows[0]["nouveau_statut"], rows[0]["nouveau_valide_par"] = "A_REVOIR", "Anne"
	write_csv(path, fields, rows)
	client.query.side_effect = RuntimeError("Entité modifiée depuis l’export")
	with pytest.raises(RuntimeError, match="modifiée"):
		import_review(client, path)


def test_rejects_dry_run_bigquery_client(tmp_path):
	client = Mock(spec=BigQueryClient)
	client.query.return_value = Mock(spec=QueryJob)
	with pytest.raises(ValueError, match="dry-run"):
		export_review(client, tmp_path / "review.csv", threshold=0.5)
