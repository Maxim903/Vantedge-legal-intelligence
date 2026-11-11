"""Tests for extraction models and their JSON Schema."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from vil_pipeline.models.extraction import NotionExtraite, ResultatExtraction

VALID_NOTION = {
	"libelle": "Congés payés",
	"definition_courte": "Droit à un repos annuel rémunéré.",
	"situations_de_vie": ["Prendre ses congés"],
	"confiance": 0.9,
	"citation_article": "Tout salarié a droit chaque année à un congé payé.",
}


def test_notion_extraite_accepts_valid_data():
	notion = NotionExtraite(**VALID_NOTION)

	assert notion.confiance == 0.9
	assert notion.situations_de_vie == ["Prendre ses congés"]


@pytest.mark.parametrize("confiance", [-0.01, 1.01])
def test_notion_extraite_rejects_confidence_outside_zero_to_one(confiance):
	with pytest.raises(ValidationError):
		NotionExtraite(**{**VALID_NOTION, "confiance": confiance})


@pytest.mark.parametrize("confiance", [0.0, 1.0])
def test_notion_extraite_accepts_confidence_bounds(confiance):
	notion = NotionExtraite(**{**VALID_NOTION, "confiance": confiance})

	assert notion.confiance == confiance


def test_notion_extraite_rejects_non_numeric_confidence():
	with pytest.raises(ValidationError):
		NotionExtraite(**{**VALID_NOTION, "confiance": "forte"})


def test_resultat_extraction_contains_notion_models_and_serializes_to_json():
	result = ResultatExtraction(
		article_version_id="LEGIARTI000006901674",
		notions=[VALID_NOTION],
	)

	assert isinstance(result.notions[0], NotionExtraite)
	serialized = json.loads(result.model_dump_json())
	assert serialized["article_version_id"] == "LEGIARTI000006901674"
	assert serialized["notions"][0]["libelle"] == "Congés payés"


def test_resultat_extraction_rejects_invalid_article_version_id():
	with pytest.raises(ValidationError):
		ResultatExtraction(article_version_id="invalid", notions=[])


def test_resultat_extraction_allows_no_extracted_notions():
	result = ResultatExtraction(
		article_version_id="LEGIARTI000006901674",
		notions=[],
	)

	assert result.notions == []


def test_exported_json_schema_matches_pydantic_models():
	schema_path = Path(__file__).parents[2] / "schemas" / "extraction.schema.json"
	exported_schema = json.loads(schema_path.read_text(encoding="utf-8"))

	assert exported_schema == ResultatExtraction.model_json_schema()
