"""LLM client protocol and deterministic fake implementation."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResponse:
	"""Raw model output and usage metadata."""

	raw_json: str
	model: str
	input_tokens: int
	output_tokens: int


class LLMClient(Protocol):
	"""Interface for extracting structured data with a language model."""

	def extract(self, article_texte: str, prompt: str) -> LLMResponse:
		"""Return raw JSON and model/token usage metadata."""
		...


class FakeLLMClient:
	"""Return injected responses in order, without making network requests."""

	def __init__(self, responses: Sequence[LLMResponse]) -> None:
		self._responses = tuple(responses)
		self._next_response = 0
		self.calls: list[tuple[str, str]] = []

	def extract(self, article_texte: str, prompt: str) -> LLMResponse:
		"""Return the next predefined response or fail when none remain."""
		self.calls.append((article_texte, prompt))
		if self._next_response >= len(self._responses):
			raise RuntimeError("FakeLLMClient has no predefined responses remaining")

		response = self._responses[self._next_response]
		self._next_response += 1
		return response
