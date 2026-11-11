"""Parse and validate structured LLM extraction results."""

import json
from dataclasses import dataclass

from pydantic import ValidationError

from vil_pipeline.clients.llm import LLMClient
from vil_pipeline.errors import ExtractionError
from vil_pipeline.models.extraction import ResultatExtraction

MAX_RETRIES = 2


@dataclass(frozen=True)
class QuarantaineExtraction:
	"""An extraction that remained invalid after validation retries."""

	raw_json: str
	reason: str
	attempts: int


type ValidatedExtraction = ResultatExtraction | QuarantaineExtraction


def validate_extraction(
	raw_json: str, article_texte: str, *, article_version_id: str | None = None
) -> ResultatExtraction:
	"""Parse an LLM JSON response and validate its schema and article citations."""
	try:
		payload = json.loads(raw_json)
	except json.JSONDecodeError as error:
		raise ExtractionError(f"JSON invalide : {error.msg}") from error

	try:
		result = ResultatExtraction.model_validate(payload)
	except ValidationError as error:
		raise ExtractionError(f"Résultat d'extraction invalide : {error}") from error

	if (
		article_version_id is not None
		and result.article_version_id != article_version_id
	):
		raise ExtractionError(
			"article_version_id ne correspond pas à l'article demandé"
		)

	for index, notion in enumerate(result.notions):
		if notion.citation_article not in article_texte:
			raise ExtractionError(
				f"La citation_article de la notion {index} n'est pas présente "
				"dans le texte de l'article"
			)

	return result


def extract_and_validate(
	client: LLMClient,
	article_texte: str,
	prompt: str,
	*,
	article_version_id: str | None = None,
) -> ValidatedExtraction:
	"""Request and validate up to three responses; quarantine the last invalid one."""
	current_prompt = prompt
	last_raw_json = ""
	last_reason = "Aucune réponse reçue"

	for attempt in range(1, MAX_RETRIES + 2):
		response = client.extract(article_texte, current_prompt)
		last_raw_json = response.raw_json
		try:
			return validate_extraction(
				last_raw_json, article_texte, article_version_id=article_version_id
			)
		except ExtractionError as error:
			last_reason = str(error)
			if attempt <= MAX_RETRIES:
				current_prompt = (
					f"{prompt}\n\nLa réponse précédente était invalide : "
					f"{last_reason}. "
					"Corrige-la et renvoie uniquement un JSON conforme au schéma."
				)

	return QuarantaineExtraction(
		raw_json=last_raw_json,
		reason=last_reason,
		attempts=MAX_RETRIES + 1,
	)
