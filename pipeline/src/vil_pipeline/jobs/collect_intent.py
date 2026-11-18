"""Classify candidate search queries into their dominant intent."""

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

from google.cloud import bigquery
from google.cloud.bigquery import QueryJob
from google.cloud.bigquery.job import WriteDisposition

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.tracking import tracked_run

INTENT_INFORMATIONNELLE = "informationnelle"
INTENT_TRANSACTIONNELLE = "transactionnelle"
INTENT_COMMERCIALE = "commerciale"
INTENT_NAVIGATIONNELLE = "navigationnelle"

CANONICAL_INTENTS = (
	INTENT_INFORMATIONNELLE,
	INTENT_TRANSACTIONNELLE,
	INTENT_COMMERCIALE,
	INTENT_NAVIGATIONNELLE,
)

TAXONOMY_VERSION = "regles_lexicales_v1"

_CANDIDATES_SQL = """
SELECT DISTINCT requete
FROM `raw.requetes_candidates`
WHERE requete IS NOT NULL AND TRIM(requete) != ''
ORDER BY requete
"""
_INTENT_SCHEMA = [
	bigquery.SchemaField("requete", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("intention_type", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("score_confiance", "FLOAT64", mode="REQUIRED"),
	bigquery.SchemaField("methode", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("date_classification", "DATE", mode="REQUIRED"),
]

_TRANSACTIONAL_PATTERN = re.compile(
	r"\b("
	r"avocat|avocate|avocats|cabinet d? ?avocats?|cabinet juridique|juriste|"
	r"conseil juridique|saisir|saisine|recours|prudhommes?|cph|plainte|"
	r"assignation|action en justice|modele|modeles|formulaires?|cerfa|"
	r"telecharger|telechargement|lettre type|courrier type|attestation"
	r")\b"
)
_COMMERCIAL_PATTERN = re.compile(
	r"\b("
	r"comparatif|comparateur|comparer|meilleur|meilleurs|meilleure|meilleures|"
	r"top|prix|tarifs?|cout|couts|devis|payant|abonnement|logiciel|logiciels|"
	r"saas|solutions?|prestataire|prestataires|cabinet conseil|"
	r"formation payante|achat|acheter"
	r")\b"
)
_NAVIGATIONAL_PATTERN = re.compile(
	r"\b("
	r"legifrance|service public|urssaf|ameli|caf|pole emploi|"
	r"france travail|travail emploi|dila|cour de cassation|"
	r"conseil d etat|code du travail numerique|cdtn|site officiel|"
	r"connexion|login"
	r")\b"
)
_INFORMATIONAL_PATTERN = re.compile(
	r"\b("
	r"comment|pourquoi|quand|qui|quel|quelle|quels|quelles|qu est ce|"
	r"definition|signification|calcul|calculer|droits?|regles?|loi|article|"
	r"code|delais?|durees?|indemnites?|conges?|salaires?|preavis|demission|"
	r"licenciement|rupture conventionnelle"
	r")\b"
)


@dataclass(frozen=True)
class IntentClassification:
	"""Result of intent classification for one query."""

	requete: str
	intention_type: str
	score_confiance: float
	methode: str


@dataclass(frozen=True)
class IntentCollectionStats:
	"""Execution summary for the collect_intent job."""

	run_id: str
	status: str
	read: int
	classified: int
	distribution: dict[str, int]


def _strip_accents(text: str) -> str:
	normalized = unicodedata.normalize("NFKD", text.casefold())
	return "".join(char for char in normalized if not unicodedata.combining(char))


def classify_intent(query: str) -> IntentClassification:
	"""Classify a search query into its dominant intent using lexical rules."""
	stripped = _strip_accents(" ".join(query.split()))
	clean_query = " ".join(query.split())

	if _TRANSACTIONAL_PATTERN.search(stripped):
		return IntentClassification(
			requete=clean_query,
			intention_type=INTENT_TRANSACTIONNELLE,
			score_confiance=0.90,
			methode=TAXONOMY_VERSION,
		)
	if _COMMERCIAL_PATTERN.search(stripped):
		return IntentClassification(
			requete=clean_query,
			intention_type=INTENT_COMMERCIALE,
			score_confiance=0.85,
			methode=TAXONOMY_VERSION,
		)
	if _NAVIGATIONAL_PATTERN.search(stripped):
		return IntentClassification(
			requete=clean_query,
			intention_type=INTENT_NAVIGATIONNELLE,
			score_confiance=0.90,
			methode=TAXONOMY_VERSION,
		)
	if _INFORMATIONAL_PATTERN.search(stripped):
		return IntentClassification(
			requete=clean_query,
			intention_type=INTENT_INFORMATIONNELLE,
			score_confiance=0.85,
			methode=TAXONOMY_VERSION,
		)
	return IntentClassification(
		requete=clean_query,
		intention_type=INTENT_INFORMATIONNELLE,
		score_confiance=0.70,
		methode=TAXONOMY_VERSION,
	)


def classify_queries(queries: Iterable[str]) -> list[IntentClassification]:
	"""Deduplicate queries and assign their dominant intent."""
	seen: set[str] = set()
	results: list[IntentClassification] = []
	for raw_query in queries:
		cleaned = " ".join(raw_query.split())
		if not cleaned:
			continue
		key = cleaned.casefold()
		if key in seen:
			continue
		seen.add(key)
		results.append(classify_intent(cleaned))
	return results


def collect_intent(
	client: BigQueryClient,
	*,
	dry_run: bool = False,
	today: date | None = None,
) -> IntentCollectionStats:
	"""Classify candidate queries and persist results in raw.requetes_intentions."""
	current_date = today or datetime.now(UTC).date()
	read = 0
	classifications: list[IntentClassification] = []

	with tracked_run(client, "collect_intent") as run:
		run.estimated_cost = Decimal(0)
		try:
			query_result = client.query(_CANDIDATES_SQL)
			if isinstance(query_result, QueryJob):
				raise ValueError("Le client BigQuery ne doit pas être en mode dry-run")
			candidates = [
				row["requete"]
				for row in query_result
				if isinstance(row.get("requete"), str) and row["requete"].strip()
			]
			read = len(candidates)
			classifications = classify_queries(candidates)

			if not classifications:
				run.status = "NO_CANDIDATE_QUERIES"
			elif dry_run:
				run.status = "DRY_RUN"
			else:
				rows = [
					{
						"requete": item.requete,
						"intention_type": item.intention_type,
						"score_confiance": item.score_confiance,
						"methode": item.methode,
						"date_classification": current_date.isoformat(),
					}
					for item in classifications
				]
				client.insert(
					"raw.requetes_intentions",
					rows,
					schema=_INTENT_SCHEMA,
					write_disposition=cast(
						WriteDisposition, bigquery.WriteDisposition.WRITE_TRUNCATE
					),
				)
		except BaseException:
			run.status = "FAILED"
			raise
		finally:
			distribution = dict(
				Counter(item.intention_type for item in classifications)
			)
			run.counts = {
				"status": run.status,
				"read": read,
				"classified": len(classifications),
				"distribution": distribution,
			}
	stats = IntentCollectionStats(
		run_id=run.run_id, status=run.status, read=read,
		classified=len(classifications), distribution=distribution,
	)
	return stats
