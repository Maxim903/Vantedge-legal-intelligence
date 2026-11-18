"""Tests for the Gemini HTTP client; all requests are intercepted by respx."""

import httpx
import pytest
import respx
from pydantic import SecretStr

from vil_pipeline.clients.llm_gemini import GeminiLLMClient
from vil_pipeline.errors import ExtractionError

URL = (
	"https://generativelanguage.googleapis.com/v1beta/models/"
	"gemini-2.5-flash:generateContent"
)
GEMINI_RESULT = {
	"candidates": [
		{
			"content": {
				"parts": [
					{
						"text": (
							'{"article_version_id":"LEGIARTI000006901674",'
							'"notions":[]}'
						)
					}
				]
			}
		}
	],
	"usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 18},
}


@respx.mock
def test_gemini_sends_json_schema_and_returns_usage_metadata() -> None:
	route = respx.post(URL).mock(return_value=httpx.Response(200, json=GEMINI_RESULT))

	with GeminiLLMClient(SecretStr("test-api-key"), timeout=12.5) as client:
		result = client.extract("Texte de l'article", "Prompt d'extraction")

	request = route.calls[0].request
	body = request.read()
	assert request.headers["x-goog-api-key"] == "test-api-key"
	assert "test-api-key" not in str(request.url)
	assert b"Prompt d'extraction" in body
	assert b"Texte de l'article" in body
	assert b"responseMimeType" in body
	assert b"responseSchema" in body
	assert client.timeout == 12.5
	expected_json = GEMINI_RESULT["candidates"][0]["content"]["parts"][0]["text"]
	assert result.raw_json == expected_json
	assert result.model == "gemini-2.5-flash"
	assert result.input_tokens == 120
	assert result.output_tokens == 18


@respx.mock
def test_gemini_retries_rate_limits() -> None:
	route = respx.post(URL).mock(
		side_effect=[
			httpx.Response(429, json={"error": {"message": "rate limited"}}),
			httpx.Response(200, json=GEMINI_RESULT),
		]
	)

	with GeminiLLMClient("test-api-key", max_attempts=2) as client:
		result = client.extract("Article", "Prompt")

	assert route.call_count == 2
	assert result.input_tokens == 120


@respx.mock
def test_gemini_retries_network_errors() -> None:
	route = respx.post(URL).mock(
		side_effect=[
			httpx.ConnectError("network unavailable"),
			httpx.Response(200, json=GEMINI_RESULT),
		]
	)

	with GeminiLLMClient("test-api-key", max_attempts=2) as client:
		result = client.extract("Article", "Prompt")

	assert route.call_count == 2
	assert result.output_tokens == 18


@respx.mock
def test_gemini_does_not_retry_other_client_errors_or_expose_key() -> None:
	route = respx.post(URL).mock(
		return_value=httpx.Response(400, json={"error": {"message": "bad request"}})
	)
	api_key = "private-test-api-key"

	with GeminiLLMClient(api_key, max_attempts=3) as client:
		with pytest.raises(httpx.HTTPStatusError) as error:
			client.extract("Article", "Prompt")

	assert route.call_count == 1
	assert api_key not in str(error.value)


@respx.mock
def test_gemini_rejects_malformed_response() -> None:
	respx.post(URL).mock(return_value=httpx.Response(200, json={"candidates": []}))

	with GeminiLLMClient("test-api-key") as client:
		with pytest.raises(ExtractionError, match="invalid generateContent response"):
			client.extract("Article", "Prompt")
