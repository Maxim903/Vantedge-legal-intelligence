"""Tests for parsing, schema validation, citation checking, and quarantine."""

import json

import pytest

from vil_pipeline.clients.llm import FakeLLMClient, LLMResponse
from vil_pipeline.errors import ExtractionError
from vil_pipeline.extraction.validate import (
	QuarantaineExtraction,
	extract_and_validate,
	validate_extraction,
)
from vil_pipeline.models.extraction import ResultatExtraction

ARTICLE_TEXT = "Tout salarié a droit chaque année à un congé payé."
VALID_RESULT = {
	"article_version_id": "LEGIARTI000006901674",
	"notions": [
		{
			"libelle": "Congés payés",
			"definition_courte": "Droit à un repos annuel rémunéré.",
			"situations_de_vie": ["Prendre ses congés"],
			"confiance": 0.9,
			"citation_article": "droit chaque année à un congé payé",
		}
	],
}


def response(payload: object, model: str = "fake-model") -> LLMResponse:
	return LLMResponse(json.dumps(payload), model, 10, 5)


def test_validate_extraction_parses_schema_and_article_citation() -> None:
	result = validate_extraction(json.dumps(VALID_RESULT), ARTICLE_TEXT)

	assert isinstance(result, ResultatExtraction)
	assert result.notions[0].citation_article in ARTICLE_TEXT


@pytest.mark.parametrize(
	("raw_json", "article_text", "reason"),
	[
		("{not-json", ARTICLE_TEXT, "JSON invalide"),
		(
			json.dumps({"article_version_id": "invalid", "notions": []}),
			ARTICLE_TEXT,
			"Résultat d'extraction invalide",
		),
		(
			json.dumps(
				{
					**VALID_RESULT,
					"notions": [
						{
							**VALID_RESULT["notions"][0],
							"citation_article": "citation inventée",
						}
					],
				}
			),
			ARTICLE_TEXT,
			"n'est pas présente",
		),
	],
)
def test_validate_extraction_rejects_invalid_output(
	raw_json: str, article_text: str, reason: str
) -> None:
	with pytest.raises(ExtractionError, match=reason):
		validate_extraction(raw_json, article_text)


def test_extract_and_validate_returns_valid_result() -> None:
	client = FakeLLMClient([response(VALID_RESULT)])

	result = extract_and_validate(client, ARTICLE_TEXT, "Prompt initial")

	assert isinstance(result, ResultatExtraction)
	assert len(client.calls) == 1
	assert client.calls[0][1] == "Prompt initial"


def test_extract_and_validate_retries_invalid_response_then_succeeds() -> None:
	invalid = {**VALID_RESULT, "notions": []}
	valid = response(VALID_RESULT)
	client = FakeLLMClient(
		[
			response(
				{
					**invalid,
					"notions": [
						{**VALID_RESULT["notions"][0], "citation_article": "absente"}
					],
				}
			),
			valid,
		]
	)

	result = extract_and_validate(client, ARTICLE_TEXT, "Prompt initial")

	assert isinstance(result, ResultatExtraction)
	assert len(client.calls) == 2
	assert "réponse précédente était invalide" in client.calls[1][1]


def test_extract_and_validate_quarantines_after_two_retries() -> None:
	invalid_response = response({"article_version_id": "invalid", "notions": []})
	client = FakeLLMClient([invalid_response, invalid_response, invalid_response])

	result = extract_and_validate(client, ARTICLE_TEXT, "Prompt initial")

	assert isinstance(result, QuarantaineExtraction)
	assert result.raw_json == invalid_response.raw_json
	assert "Résultat d'extraction invalide" in result.reason
	assert result.attempts == 3
	assert len(client.calls) == 3
