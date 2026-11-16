"""Tests for the LEGI XML parser."""

from datetime import date
from pathlib import Path

import pytest

from vil_pipeline.errors import ExtractionError
from vil_pipeline.models.corpus import Article, ArticleVersion
from vil_pipeline.parsers.legi import parse_legi_article

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures" / "legi"


@pytest.mark.parametrize(
	"filename, article_id, state, start, end",
	[
		(
			"article_vigueur.xml",
			"LEGIARTI000006901674",
			"VIGUEUR",
			date(2008, 5, 1),
			None,
		),
		(
			"article_modifie.xml",
			"LEGIARTI000006901793",
			"MODIFIE",
			date(2008, 5, 1),
			date(2021, 6, 1),
		),
		(
			"article_abroge.xml",
			"LEGIARTI000006583330",
			"ABROGE",
			date(1993, 7, 23),
			date(1995, 2, 2),
		),
	],
)
def test_parse_legi_article_extracts_models_and_version_metadata(
	filename,
	article_id,
	state,
	start,
	end,
):
	article, version = parse_legi_article(FIXTURES_DIR / filename)

	assert isinstance(article, Article)
	assert isinstance(version, ArticleVersion)
	assert article.article_id == article_id
	assert version.article_version_id == article_id
	assert version.article_id == article_id
	assert version.etat == state
	assert version.date_debut == start
	assert version.date_fin == end
	assert article.numero
	assert article.code_id.startswith("LEGITEXT")
	assert article.livre
	assert article.titre
	assert article.chapitre


def test_parse_legi_article_cleans_html_from_text():
	_, version = parse_legi_article(FIXTURES_DIR / "article_vigueur.xml")

	assert "La partie la plus diligente des organisations signataires" in version.texte
	assert "<br" not in version.texte
	assert "<p" not in version.texte


def test_parse_legi_article_uses_effective_historical_chapter():
	article, _ = parse_legi_article(FIXTURES_DIR / "article_abroge.xml")

	assert article.chapitre == "Chapitre III : Les instruments"
	assert article.chapitre_id == "LEGISCTA000006152227"
	assert article.titre_id == "LEGISCTA000006138327"
	assert article.livre_id == "LEGISCTA000006121420"


def test_parse_legi_article_reports_invalid_xml_with_file_path(tmp_path: Path):
	xml_path = tmp_path / "broken.xml"
	xml_path.write_text("<ARTICLE><META></ARTICLE>", encoding="utf-8")

	with pytest.raises(ExtractionError, match=str(xml_path)):
		parse_legi_article(xml_path)


@pytest.mark.parametrize(
	"old_value, new_value",
	[
		("LEGIARTI000006901674", "invalid-id"),
		("<ETAT>VIGUEUR</ETAT>", "<ETAT>ETRANGER</ETAT>"),
	],
)
def test_parse_legi_article_reports_invalid_identifiers_and_states(
	tmp_path: Path,
	old_value: str,
	new_value: str,
):
	fixture = (FIXTURES_DIR / "article_vigueur.xml").read_text(encoding="utf-8")
	xml_path = tmp_path / "invalid.xml"
	xml_path.write_text(fixture.replace(old_value, new_value, 1), encoding="utf-8")

	with pytest.raises(ExtractionError, match=str(xml_path)):
		parse_legi_article(xml_path)
