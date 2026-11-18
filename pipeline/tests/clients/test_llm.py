"""Tests for the LLM client protocol and fake."""

import pytest

from vil_pipeline.clients.llm import FakeLLMClient, LLMClient, LLMResponse


def test_fake_llm_returns_predefined_raw_json_and_metadata() -> None:
	response = LLMResponse(
		raw_json='{"article_version_id":"LEGIARTI000006901674","notions":[]}',
		model="fake-model-v1",
		input_tokens=120,
		output_tokens=18,
	)
	client: LLMClient = FakeLLMClient([response])

	result = client.extract("Texte de l'article", "Prompt d'extraction")

	assert result is response
	assert result.raw_json == response.raw_json
	assert result.model == "fake-model-v1"
	assert result.input_tokens == 120
	assert result.output_tokens == 18
	assert client.calls == [("Texte de l'article", "Prompt d'extraction")]


def test_fake_llm_returns_predefined_responses_in_order() -> None:
	first = LLMResponse("{}", "fake-1", 1, 2)
	second = LLMResponse('{"notions":[]}', "fake-2", 3, 4)
	client = FakeLLMClient([first, second])

	assert client.extract("article 1", "prompt") is first
	assert client.extract("article 2", "prompt") is second


def test_fake_llm_fails_explicitly_when_responses_are_exhausted() -> None:
	client = FakeLLMClient([])

	with pytest.raises(RuntimeError, match="no predefined responses"):
		client.extract("Texte", "Prompt")
