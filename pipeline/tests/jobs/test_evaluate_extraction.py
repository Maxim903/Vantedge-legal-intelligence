"""Known examples for extraction evaluation, with an offline BigQuery double."""

import csv
import hashlib
import json
from unittest.mock import Mock

import pytest

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.errors import ExtractionError
from vil_pipeline.jobs.evaluate_extraction import (
	ArticleReference,
	Counts,
	evaluate_extraction,
	load_reference,
	normalize_notion,
	score,
)

ID1 = "LEGIARTI000000000001"
ID2 = "LEGIARTI000000000002"
ID3 = "LEGIARTI000000000003"


def _csv(path, fields, rows):
	with path.open("w", encoding="utf-8", newline="") as stream:
		writer = csv.DictWriter(stream, fieldnames=fields)
		writer.writeheader()
		writer.writerows(rows)


def _inputs(tmp_path, annotations):
	golden = tmp_path / "golden.csv"
	titles = tmp_path / "titles.csv"
	rows, mapping = [], []
	for key, title_id, title, labels in annotations:
		text = f"Texte {key}"
		rows.append({
			"article_version_id": key,
			"texte": text,
			"notions_attendues": labels,
		})
		mapping.append({
			"article_version_id": key,
			"titre_id": title_id,
			"titre": title,
			"texte_sha256": hashlib.sha256(text.encode()).hexdigest(),
		})
	_csv(golden, ["article_version_id", "texte", "notions_attendues"], rows)
	_csv(titles, ["article_version_id", "titre_id", "titre", "texte_sha256"], mapping)
	return golden, titles


def _result(key, labels, status="SUCCESS"):
	return {
		"article_version_id": key,
		"statut": status,
		"resultat_json": json.dumps({
			"article_version_id": key,
			"notions": [{
				"libelle": label,
				"definition_courte": "Définition",
				"situations_de_vie": [],
				"confiance": 0.9,
				"citation_article": "Texte",
			} for label in labels],
		}),
	}


@pytest.mark.parametrize(("value", "expected"), [
	("Congés PAYÉS", "conge paye"),
	("Droits des salariés", "droit des salarie"),
	("BUREAUX", "bureau"),
	("Statut du processus", "statut du processus"),
	("Délai", "delai"),
])
def test_normalization(value, expected):
	assert normalize_notion(value) == expected


def test_micro_scores_per_article_and_title():
	refs = [
		ArticleReference(ID1, "", "t1", "Titre A", frozenset({"a", "b"})),
		ArticleReference(ID2, "", "t2", "Titre B", frozenset({"c"})),
	]
	total, titles = score(refs, {
		ID1: frozenset({"a", "c"}),
		ID2: frozenset({"c"}),
	})
	assert total == Counts(tp=2, fp=1, fn=1)
	assert total.precision == total.recall == total.f1 == 2 / 3
	assert titles[("t1", "Titre A")] == (Counts(1, 1, 1), 1)
	assert titles[("t2", "Titre B")] == (Counts(1, 0, 0), 1)


def test_undefined_metrics_are_not_misreported_as_zero():
	assert Counts().precision is None
	assert Counts().recall is None
	assert Counts().f1 is None
	assert Counts(fp=1).precision == 0
	assert Counts(fp=1).recall is None
	assert Counts(fp=1).f1 == 0


def test_end_to_end_report_and_parameterized_query(tmp_path):
	golden, titles = _inputs(tmp_path, [
		(ID1, "t1", "Titre A", '["Congés payés", "Employeur"]'),
		(ID2, "t2", "Titre B", '["Salarié"]'),
		(ID3, "t2", "Titre B", ""),
	])
	client = Mock(spec=BigQueryClient)
	client.query.return_value = [
		_result(ID1, ["Congé payé", "Congés payés", "Salariés"]),
		_result(ID2, ["salarié"]),
	]
	path = evaluate_extraction(
		client, model="model", version_prompt="prompt-hash",
		golden_path=golden, titles_path=titles, output_path=tmp_path / "report.md",
	)
	report = path.read_text(encoding="utf-8")
	assert "| Global | 2 | 2 | 1 | 1 | 66.67% | 66.67% | 66.67% |" in report
	assert "| Titre A (t1) | 1 | 1 | 1 | 1 | 50.00% | 50.00% | 50.00% |" in report
	assert "| Titre B (t2) | 1 | 1 | 0 | 0 | 100.00% | 100.00% | 100.00% |" in report
	assert "Articles non annotés exclus : 1" in report
	sql, parameters = client.query.call_args_list[1].args
	assert "ops.extraction_results" in sql
	assert {p.name: p.value for p in parameters} == {
		"model": "model", "version_prompt": "prompt-hash",
		"article_ids": json.dumps([ID1, ID2]),
	}
	with pytest.raises(FileExistsError):
		evaluate_extraction(
			client, model="model", version_prompt="prompt-hash",
			golden_path=golden, titles_path=titles, output_path=path,
		)


def test_empty_annotation_differs_from_annotated_empty_list(tmp_path):
	golden, titles = _inputs(
		tmp_path, [(ID1, "t1", "Titre", ""), (ID2, "t1", "Titre", "[]")]
	)
	refs, total, skipped = load_reference(golden, titles)
	assert (len(refs), total, skipped) == (1, 2, 1)
	assert refs[0].notions == frozenset()
	client = Mock(spec=BigQueryClient)
	client.query.return_value = [_result(ID2, [])]
	report = evaluate_extraction(
		client, model="m", version_prompt="v", golden_path=golden, titles_path=titles,
		output_path=tmp_path / "empty.md",
	).read_text(encoding="utf-8")
	assert "| Global | 1 | 0 | 0 | 0 | N/D | N/D | N/D |" in report


@pytest.mark.parametrize("annotation", ["", "invalid json", "null", '[""]'])
def test_missing_or_invalid_annotations_fail_before_query(tmp_path, annotation):
	golden, titles = _inputs(tmp_path, [(ID1, "t1", "Titre", annotation)])
	client = Mock(spec=BigQueryClient)
	with pytest.raises(ValueError):
		evaluate_extraction(
			client, model="m", version_prompt="v", golden_path=golden,
			titles_path=titles, output_path=tmp_path / "report.md",
		)
	assert all(
		"ops.pipeline_runs" in call.args[0] for call in client.query.call_args_list
	)
	assert not (tmp_path / "report.md").exists()


@pytest.mark.parametrize("results", [
	[],
	[_result(ID1, [], status="QUARANTINE")],
	[_result(ID1, []), _result(ID1, [])],
])
def test_missing_quarantined_or_duplicate_results_are_errors(tmp_path, results):
	golden, titles = _inputs(tmp_path, [(ID1, "t1", "Titre", "[]")])
	client = Mock(spec=BigQueryClient)
	client.query.return_value = results
	with pytest.raises(ValueError):
		evaluate_extraction(
			client, model="m", version_prompt="v", golden_path=golden,
			titles_path=titles, output_path=tmp_path / "report.md",
		)
	assert not (tmp_path / "report.md").exists()


def test_wrong_id_in_model_response_is_rejected(tmp_path):
	golden, titles = _inputs(tmp_path, [(ID1, "t1", "Titre", "[]")])
	client = Mock(spec=BigQueryClient)
	row = _result(ID2, [])
	row["article_version_id"] = ID1
	client.query.return_value = [row]
	with pytest.raises(ExtractionError, match="article_version_id"):
		evaluate_extraction(
			client, model="m", version_prompt="v", golden_path=golden,
			titles_path=titles, output_path=tmp_path / "report.md",
		)


def test_changed_article_text_is_not_scored_against_stale_titles(tmp_path):
	golden, titles = _inputs(tmp_path, [(ID1, "t1", "Titre", "[]")])
	golden.write_text(golden.read_text().replace("Texte", "Modifié"), encoding="utf-8")
	with pytest.raises(ValueError, match="texte de référence"):
		load_reference(golden, titles)
