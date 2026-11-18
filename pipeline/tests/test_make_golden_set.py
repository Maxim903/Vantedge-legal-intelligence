"""Tests for the stratified golden-set generator; no network access."""

import csv
import importlib.util
import json
import sys
import tarfile
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
	"make_golden_set", ROOT / "scripts" / "make_golden_set.py"
)
assert spec is not None and spec.loader is not None
golden = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = golden
spec.loader.exec_module(golden)


def _article(index, title):
	return golden.Candidate(f"LEGIARTI{index:012d}", f"Texte {index}", title, title)


def test_stratified_sample_exact_size_seed_and_proportions():
	articles = [_article(i, "titre A") for i in range(150)] + [
		_article(i, "titre B") for i in range(150, 200)
	]
	sample = golden.stratified_sample(articles)
	assert len(sample) == 100
	assert len({a.article_version_id for a in sample}) == 100
	assert sum(a.titre == "titre A" for a in sample) == 75
	assert sum(a.titre == "titre B" for a in sample) == 25
	assert sample == golden.stratified_sample(list(reversed(articles)))
	assert sample != golden.stratified_sample(articles, seed=43)


def test_small_strata_are_represented_and_same_labels_have_distinct_ids():
	articles = [golden.Candidate(f"id-{i}", "texte", "Titre I", "a") for i in range(99)]
	articles += [golden.Candidate("rare", "texte", "Titre I", "b")]
	sample = golden.stratified_sample(articles, size=10)
	assert sum(a.strate == "b" for a in sample) == 1
	assert len(sample) == 10


def test_not_enough_unique_articles_or_too_many_strata():
	with pytest.raises(ValueError, match="Seulement 1"):
		golden.stratified_sample([_article(1, "A"), _article(1, "A")], size=2)
	with pytest.raises(ValueError, match="titres dépassent"):
		golden.stratified_sample([_article(1, "A"), _article(2, "B")], size=1)
	with pytest.raises(ValueError, match="positive"):
		golden.stratified_sample([], size=0)


def test_duplicate_ids_with_different_content_fail():
	with pytest.raises(ValueError, match="Identifiant contradictoire"):
		golden.stratified_sample(
			[_article(1, "A"), _article(1, "B")], size=1
		)


def test_csv_columns_quotes_blanks_and_no_overwrite(tmp_path):
	path = tmp_path / "golden.csv"
	article = golden.Candidate("id", 'Texte "cité",\nligne', "Titre", "id-titre")
	golden.write_csv(path, [article])
	with path.open(encoding="utf-8", newline="") as stream:
		rows = list(csv.DictReader(stream))
	assert rows == [{
		"article_version_id": "id",
		"texte": 'Texte "cité",\nligne',
		"notions_attendues": "",
		"annotateur": "",
		"date": "",
	}]
	with pytest.raises(FileExistsError):
		golden.write_csv(path, [])
	assert path.read_text(encoding="utf-8").count("id-titre") == 0


def test_title_mapping_covers_committed_golden_set():
	import hashlib

	base = ROOT / "docs" / "05-ia"
	with (base / "golden-set.csv").open(encoding="utf-8", newline="") as stream:
		articles = {row["article_version_id"]: row for row in csv.DictReader(stream)}
	with (base / "golden-set-titres.csv").open(encoding="utf-8", newline="") as stream:
		titles = list(csv.DictReader(stream))
	assert len(titles) == len(articles)
	assert {row["article_version_id"] for row in titles} == set(articles)
	for row in titles:
		assert row["titre_id"] and row["titre"]
		text = articles[row["article_version_id"]]["texte"]
		assert row["texte_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_write_titles_preserves_id_title_hash_and_refuses_overwrite(tmp_path):
	path = tmp_path / "titres.csv"
	article = golden.Candidate("id", "texte", "Titre", "titre-id")
	golden.write_titles(path, [article])
	with path.open(encoding="utf-8", newline="") as stream:
		rows = list(csv.DictReader(stream))
	assert rows[0]["article_version_id"] == "id"
	assert rows[0]["titre_id"] == "titre-id"
	assert rows[0]["titre"] == "Titre"
	with pytest.raises(FileExistsError):
		golden.write_titles(path, [])


def test_xml_source_uses_real_fixture_and_excludes_expired_versions():
	fixture = ROOT / "pipeline/tests/fixtures/legi/article_vigueur.xml"
	articles = golden.candidates(fixture, "II", date(2008, 5, 1))
	assert len(articles) == 1
	assert articles[0].article_version_id == "LEGIARTI000006901674"
	assert articles[0].titre.startswith("Titre III")
	assert articles[0].strate.startswith("LEGISCTA")
	assert golden.candidates(fixture, "I", date(2008, 5, 1)) == []
	assert golden.candidates(fixture, "II", date(2008, 4, 30)) == []


def test_archive_ignores_non_article_xml(tmp_path):
	fixture = ROOT / "pipeline/tests/fixtures/legi/article_vigueur.xml"
	archive = tmp_path / "corpus.tar.gz"
	with tarfile.open(archive, "w:gz") as tar:
		tar.add(fixture, arcname="data/article/LEGI/ARTI/article.xml")
		tar.add(fixture, arcname="data/texte/version/other.xml")
	articles = golden.candidates(archive, "II", date(2008, 5, 1))
	assert len(articles) == 1


def test_json_snapshot_fails_outside_snapshot_validity(tmp_path):
	path = tmp_path / "snapshot.json"
	path.write_text(json.dumps({
		"type": "code",
		"data": {
			"cid": "LEGITEXT000006072050",
			"dateDebutVersion": "2026-01-01",
			"dateFinVersion": "2027-01-01",
		},
		"children": [],
	}), encoding="utf-8")
	assert golden.candidates(path, "I", date(2026, 6, 1)) == []
	with pytest.raises(ValueError, match="hors de la période"):
		golden.candidates(path, "I", date(2027, 1, 1))


def test_json_snapshot_selects_valid_book_title_and_article_versions(tmp_path):
	path = tmp_path / "snapshot.json"

	def article(id_, state="VIGUEUR", end=1893456000000):
		return {
			"type": "article",
			"data": {
				"id": id_, "etat": state, "dateDebut": 1735689600000,
				"dateFin": end, "texte": "Texte  d'article",
			},
		}

	def section(id_, title, children):
		return {
			"type": "section", "data": {"id": id_, "title": title},
			"children": children,
		}

	document = {
		"type": "code",
		"data": {
			"cid": "LEGITEXT000006072050",
			"dateDebutVersion": "2026-01-01",
			"dateFinVersion": "2027-01-01",
		},
		"children": [
			section("book-i", "Livre Ier", [
				section("title-i", "Titre Ier : Règles", [
					article("LEGIARTI000000000001"),
					article("LEGIARTI000000000002", "MODIFIE"),
					article("LEGIARTI000000000003", end=1767225600000),
				]),
			]),
			section("book-ii", "Livre II", [
				section("other", "Titre Ier", [article("LEGIARTI000000000004")]),
			]),
		],
	}
	path.write_text(json.dumps(document), encoding="utf-8")
	assert golden.candidates(path, "I", date(2026, 6, 1)) == [
		golden.Candidate(
			"LEGIARTI000000000001", "Texte d'article", "Titre Ier : Règles", "title-i"
		)
	]


def test_committed_sample_has_required_shape_and_unique_nonempty_articles():
	path = ROOT / "docs" / "05-ia" / "golden-set.csv"
	with path.open(encoding="utf-8", newline="") as stream:
		reader = csv.DictReader(stream)
		assert tuple(reader.fieldnames) == golden.FIELDS
		rows = list(reader)
	assert len(rows) == 100
	assert len({row["article_version_id"] for row in rows}) == 100
	assert all(row["article_version_id"] and row["texte"] for row in rows)
