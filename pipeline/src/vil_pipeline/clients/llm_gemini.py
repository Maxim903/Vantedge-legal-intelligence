"""Gemini implementation of the structured LLM client."""

from typing import Any
from urllib.parse import quote

import httpx
from pydantic import SecretStr
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from vil_pipeline.clients.llm import LLMResponse
from vil_pipeline.errors import ExtractionError

_RESPONSE_SCHEMA: dict[str, object] = {
	"type": "OBJECT",
	"properties": {
		"article_version_id": {"type": "STRING"},
		"notions": {
			"type": "ARRAY",
			"items": {
				"type": "OBJECT",
				"properties": {
					"libelle": {"type": "STRING"},
					"definition_courte": {"type": "STRING"},
					"situations_de_vie": {
						"type": "ARRAY",
						"items": {"type": "STRING"},
					},
					"confiance": {"type": "NUMBER"},
					"citation_article": {"type": "STRING"},
				},
				"required": [
					"libelle",
					"definition_courte",
					"situations_de_vie",
					"confiance",
					"citation_article",
				],
			},
		},
	},
	"required": ["article_version_id", "notions"],
}


def _is_retryable(error: BaseException) -> bool:
	if isinstance(error, httpx.TransportError):
		return True
	return isinstance(error, httpx.HTTPStatusError) and (
		error.response.status_code == 429 or error.response.status_code >= 500
	)


class GeminiLLMClient:
	"""Call Gemini's generateContent REST endpoint."""

	def __init__(
		self,
		api_key: SecretStr | str,
		model: str = "gemini-2.5-flash",
		timeout: float = 30.0,
		max_attempts: int = 3,
	) -> None:
		key = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
		if not key.strip():
			raise ValueError("Gemini API key must not be empty")
		if not model.strip():
			raise ValueError("Gemini model must not be empty")
		if timeout <= 0:
			raise ValueError("timeout must be greater than zero")
		if max_attempts < 1:
			raise ValueError("max_attempts must be at least one")

		self.timeout = timeout
		self.model = model
		self._url = (
			"https://generativelanguage.googleapis.com/v1beta/models/"
			f"{quote(model, safe='')}:generateContent"
		)
		self._client = httpx.Client(
			headers={"x-goog-api-key": key},
			timeout=timeout,
		)
		self._retry = Retrying(
			retry=retry_if_exception(_is_retryable),
			stop=stop_after_attempt(max_attempts),
			wait=wait_exponential(multiplier=1, min=1, max=8),
			reraise=True,
		)

	def extract(self, article_texte: str, prompt: str) -> LLMResponse:
		"""Return Gemini's JSON output with token-usage metadata."""
		payload: dict[str, object] = {
			"systemInstruction": {"parts": [{"text": prompt}]},
			"contents": [{"role": "user", "parts": [{"text": article_texte}]}],
			"generationConfig": {
				"responseMimeType": "application/json",
				"responseSchema": _RESPONSE_SCHEMA,
			},
		}
		response_body = self._retry(self._generate_content, payload)

		try:
			candidate = response_body["candidates"][0]
			raw_json = "".join(
				part["text"]
				for part in candidate["content"]["parts"]
				if "text" in part
			)
			usage = response_body.get("usageMetadata", {})
			input_tokens = usage.get("promptTokenCount", 0)
			output_tokens = usage.get("candidatesTokenCount", 0)
			if (
				not isinstance(raw_json, str)
				or not raw_json
				or not isinstance(input_tokens, int)
				or not isinstance(output_tokens, int)
			):
				raise TypeError("Unexpected Gemini response field types")
		except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
			raise ExtractionError(
				"Gemini returned an invalid generateContent response"
			) from error

		return LLMResponse(
			raw_json=raw_json,
			model=self.model,
			input_tokens=input_tokens,
			output_tokens=output_tokens,
		)

	def _generate_content(self, payload: dict[str, object]) -> dict[str, Any]:
		response = self._client.post(self._url, json=payload)
		response.raise_for_status()
		body = response.json()
		if not isinstance(body, dict):
			raise ExtractionError("Gemini returned an invalid generateContent response")
		return body

	def close(self) -> None:
		"""Close the underlying HTTP connection pool."""
		self._client.close()

	def __enter__(self) -> "GeminiLLMClient":
		return self

	def __exit__(self, *_: object) -> None:
		self.close()
