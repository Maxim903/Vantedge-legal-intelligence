"""Tests for legal corpus models."""

from datetime import date

import pytest
from pydantic import ValidationError

from vil_pipeline.models.corpus import Article, ArticleVersion


def test_article_accepts_legifrance_article_id_and_metadata():
	article = Article(
		article_id="LEGIARTI000006419311",
		numero="L. 1234-1",
		code_id="code-travail",
		livre="Livre Ier",
		titre="Titre II",
		chapitre="Chapitre III",
	)

	assert article.article_id == "LEGIARTI000006419311"


@pytest.mark.parametrize(
	"article_id",
	["", "LEGIARTI", "LEGIARTI123", "LEGITEXT000006419311", "LEGIARTI00000641931X"],
)
def test_article_rejects_invalid_article_id(article_id):
	with pytest.raises(ValidationError):
		Article(
			article_id=article_id,
			numero="L. 1234-1",
			code_id="code-travail",
			livre="Livre Ier",
			titre="Titre II",
			chapitre="Chapitre III",
		)


def test_article_version_accepts_valid_dates_and_state():
	version = ArticleVersion(
		article_version_id="LEGIARTI000006419311",
		article_id="LEGIARTI000006419311",
		texte="Texte de l'article.",
		etat="VIGUEUR",
		date_debut=date(2020, 1, 1),
		date_fin=date(2020, 1, 1),
	)

	assert version.date_debut == date(2020, 1, 1)
	assert version.date_fin == date(2020, 1, 1)


def test_article_version_allows_open_ended_validity():
	version = ArticleVersion(
		article_version_id="LEGIARTI000006419311",
		article_id="LEGIARTI000006419311",
		texte="Texte de l'article.",
		etat="MODIFIE",
		date_debut=date(2020, 1, 1),
	)

	assert version.date_fin is None


@pytest.mark.parametrize(
	"field",
	["article_version_id", "article_id"],
)
def test_article_version_rejects_invalid_identifiers(field):
	values = {
		"article_version_id": "LEGIARTI000006419311",
		"article_id": "LEGIARTI000006419311",
		"texte": "Texte de l'article.",
		"etat": "ABROGE",
		"date_debut": date(2020, 1, 1),
	}
	values[field] = "invalid-id"

	with pytest.raises(ValidationError):
		ArticleVersion(**values)


def test_article_version_rejects_end_date_before_start_date():
	with pytest.raises(ValidationError, match="date_fin"):
		ArticleVersion(
			article_version_id="LEGIARTI000006419311",
			article_id="LEGIARTI000006419311",
			texte="Texte de l'article.",
			etat="ABROGE",
			date_debut=date(2020, 1, 2),
			date_fin=date(2020, 1, 1),
		)


def test_article_version_rejects_unknown_state():
	with pytest.raises(ValidationError):
		ArticleVersion(
			article_version_id="LEGIARTI000006419311",
			article_id="LEGIARTI000006419311",
			texte="Texte de l'article.",
			etat="EN_VIGUEUR",
			date_debut=date(2020, 1, 1),
		)
