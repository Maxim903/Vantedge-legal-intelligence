"""Batch extraction of legal entities with a per-call estimated budget."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from google.cloud.bigquery import QueryJob, ScalarQueryParameter

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.clients.llm import LLMClient, LLMResponse
from vil_pipeline.errors import ApiBudgetExceeded
from vil_pipeline.extraction.validate import QuarantaineExtraction, extract_and_validate
from vil_pipeline.models.extraction import ResultatExtraction
from vil_pipeline.tracking import tracked_run

_SELECT = """
WITH versions AS (
  SELECT article_version_id, texte, etat, date_debut, date_fin,
    ROW_NUMBER() OVER (
      PARTITION BY article_version_id ORDER BY date_chargement DESC
    ) AS position
  FROM `raw.article_versions`
)
SELECT v.article_version_id, v.texte
FROM versions AS v
WHERE v.position = 1 AND v.etat = 'VIGUEUR'
  AND v.date_debut <= CURRENT_DATE()
  AND (v.date_fin IS NULL OR v.date_fin >= CURRENT_DATE())
  AND v.article_version_id > @last_id
  AND NOT EXISTS (
    SELECT 1 FROM `ops.extraction_results` AS done
    WHERE done.article_version_id = v.article_version_id
      AND done.version_prompt = @version_prompt AND done.modele_llm = @model
  )
  AND NOT EXISTS (
    SELECT 1 FROM `raw.entites_extraites` AS extracted
    WHERE extracted.article_version_id = v.article_version_id
      AND extracted.version_prompt = @version_prompt AND extracted.modele_llm = @model
  )
ORDER BY v.article_version_id
LIMIT @batch_size
"""

_SAVE = """
BEGIN TRANSACTION;
IF NOT EXISTS (
  SELECT 1 FROM `ops.extraction_results`
  WHERE article_version_id = @article_id
    AND version_prompt = @version_prompt AND modele_llm = @model
) AND NOT EXISTS (
  SELECT 1 FROM `raw.entites_extraites`
  WHERE article_version_id = @article_id
    AND version_prompt = @version_prompt AND modele_llm = @model
) THEN
  INSERT INTO `raw.entites_extraites`
    (extraction_id, article_version_id, notion_libelle, situation_de_vie,
     score_confiance, modele_llm, version_prompt, extrait_le, statut_validation)
  SELECT JSON_VALUE(item, '$.extraction_id'), @article_id,
    JSON_VALUE(item, '$.notion_libelle'), JSON_VALUE(item, '$.situation_de_vie'),
    FLOAT64(JSON_QUERY(item, '$.score_confiance')), @model, @version_prompt,
    @extrait_le, 'AUTO'
  FROM UNNEST(JSON_QUERY_ARRAY(PARSE_JSON(@entities))) AS item;
  INSERT INTO `ops.extraction_results`
    (article_version_id, version_prompt, modele_llm, statut, resultat_json,
     raison, extrait_le, run_id)
  VALUES (@article_id, @version_prompt, @model, @status, @raw_json,
          @reason, @extrait_le, @run_id);
END IF;
COMMIT TRANSACTION;
"""




@dataclass
class ExtractionStats:
	"""Summary of an extraction run."""

	run_id: str
	status: str = "SUCCESS"
	read: int = 0
	processed: int = 0
	quarantined: int = 0
	entities: int = 0
	calls: int = 0
	estimated_cost: Decimal = Decimal(0)
	dry_run: bool = False


class _BudgetedClient:
	def __init__(
		self, client: LLMClient, model: str, max_cost: Decimal,
		cost_per_call: Decimal, stats: ExtractionStats,
	) -> None:
		self.client = client
		self.model = model
		self.max_cost = max_cost
		self.cost_per_call = cost_per_call
		self.stats = stats
		self.last_response: LLMResponse | None = None

	def extract(self, article_texte: str, prompt: str) -> LLMResponse:
		if self.stats.estimated_cost + self.cost_per_call > self.max_cost:
			raise ApiBudgetExceeded("Le budget estimé ne permet pas un nouvel appel")
		self.stats.calls += 1
		self.stats.estimated_cost += self.cost_per_call
		response = self.client.extract(article_texte, prompt)
		if response.model != self.model:
			raise ValueError("Le modèle de la réponse diffère du modèle configuré")
		self.last_response = response
		return response


def _param(
	name: str, type_: str, value: str | int | Decimal | datetime | None
) -> ScalarQueryParameter:
	return ScalarQueryParameter(name, type_, value)


def _situations(values: list[str]) -> list[str | None]:
	return list(values) if values else [None]


def _entities(result: ResultatExtraction) -> list[dict[str, object]]:
	return [
		{
			"extraction_id": str(uuid4()),
			"notion_libelle": notion.libelle,
			"situation_de_vie": situation,
			"score_confiance": notion.confiance,
		}
		for notion in result.notions
		for situation in _situations(notion.situations_de_vie)
	]


def extract_entities(
	bq: BigQueryClient,
	llm: LLMClient | None,
	*,
	prompt: str,
	version_prompt: str,
	model: str,
	max_cost: Decimal,
	cost_per_call: Decimal,
	batch_size: int = 100,
	dry_run: bool = False,
) -> ExtractionStats:
	"""Extract in pages; journal every completed, budget-stopped or failed run.

	Cost is an estimate per LLMClient.extract invocation, not a billing guarantee.
	"""
	with tracked_run(bq, "extract_entities") as run:
		stats = ExtractionStats(run_id=run.run_id, dry_run=dry_run)
		try:
			for name, value in (
				("max_cost", max_cost), ("cost_per_call", cost_per_call)
			):
				exponent = value.as_tuple().exponent
				if (
					not value.is_finite()
					or value < 0
					or not isinstance(exponent, int)
					or exponent < -9
				):
					raise ValueError(
						f"{name} must be finite, non-negative and have <= 9 decimals"
					)
			if cost_per_call == 0:
				raise ValueError("cost_per_call must be greater than zero")
			if batch_size < 1:
				raise ValueError("batch_size must be greater than zero")
			if not prompt.strip() or not version_prompt.strip() or not model.strip():
				raise ValueError("prompt, version_prompt and model must not be empty")
			if not dry_run and llm is None:
				raise ValueError("llm is required unless dry_run is enabled")

			budgeted = (
				_BudgetedClient(llm, model, max_cost, cost_per_call, stats)
				if llm is not None else None
			)
			last_id = ""

			while True:
				query_result = bq.query(_SELECT, [
					_param("last_id", "STRING", last_id),
					_param("version_prompt", "STRING", version_prompt),
					_param("model", "STRING", model),
					_param("batch_size", "INT64", batch_size),
				])
				if isinstance(query_result, QueryJob):
					raise ValueError(
						"Le client BigQuery ne doit pas être en mode dry-run"
					)
				rows = list(query_result)
				for row in rows:
					article_id = row["article_version_id"]
					text = row["texte"]
					if (
						not isinstance(article_id, str)
						or not isinstance(text, str)
						or not text
					):
						raise ValueError(
							"La version d'article doit contenir "
							"un identifiant et un texte"
						)
					last_id = article_id
					stats.read += 1
					if dry_run:
						stats.estimated_cost += cost_per_call
						continue
					if budgeted is None:
						raise RuntimeError("Client LLM manquant")
					article_prompt = (
						f"{prompt}\n\nIdentifiant de la version de cet article : "
						f"{article_id}. "
						"Utilise exactement cet identifiant dans article_version_id."
					)
					result = extract_and_validate(
						budgeted, text, article_prompt, article_version_id=article_id
					)
					response = budgeted.last_response
					if response is None:
						raise RuntimeError("Réponse LLM manquante")
					if isinstance(result, QuarantaineExtraction):
						status = "QUARANTINE"
						reason = result.reason
						entities: list[dict[str, object]] = []
					else:
						status = "SUCCESS"
						reason = None
						entities = _entities(result)
					bq.query(_SAVE, [
						_param("article_id", "STRING", article_id),
						_param("version_prompt", "STRING", version_prompt),
						_param("model", "STRING", model),
						_param("status", "STRING", status),
						_param("raw_json", "STRING", response.raw_json),
						_param("reason", "STRING", reason),
						_param(
							"entities", "STRING",
							json.dumps(entities, ensure_ascii=False),
						),
						_param("extrait_le", "TIMESTAMP", datetime.now(UTC)),
						_param("run_id", "STRING", stats.run_id),
					])
					stats.processed += 1
					stats.entities += len(entities)
					stats.quarantined += int(status == "QUARANTINE")
				if not rows or len(rows) < batch_size:
					break
			if dry_run and stats.estimated_cost > max_cost:
				stats.status = "DRY_RUN_OVER_BUDGET"
		except ApiBudgetExceeded:
			stats.status = "BUDGET_EXHAUSTED"
			run.error = "ApiBudgetExceeded"
		except BaseException:
			stats.status = "FAILED"
			raise
		finally:
			run.status = stats.status
			counts = asdict(stats)
			counts.pop("estimated_cost")
			run.counts = counts
			run.estimated_cost = stats.estimated_cost
	return stats
