"""Build deterministic candidate search queries from validated notions."""

import hashlib
import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import cast

from google.cloud import bigquery
from google.cloud.bigquery import QueryJob
from google.cloud.bigquery.job import WriteDisposition

from vil_pipeline.clients.bigquery import BigQueryClient

_VALIDATED_NOTIONS_SQL = """
SELECT DISTINCT notion_libelle, situation_de_vie
FROM `raw.entites_extraites`
WHERE statut_validation = 'VALIDE'
  AND notion_libelle IS NOT NULL
ORDER BY notion_libelle, situation_de_vie
"""
_SEED_SCHEMA = [
	bigquery.SchemaField("notion_id", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("requete", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("score_rattachement", "FLOAT64", mode="REQUIRED"),
]
_SCORES = {
	"label": 1.0,
	"singular": 0.7,
	"situation": 0.8,
}


def _normalize_query(value: str) -> str:
	return " ".join(value.casefold().split())


def _singularize(value: str) -> str:
	def singular(match: re.Match[str]) -> str:
		word = match.group()
		if len(word) > 4 and word.endswith("eaux"):
			return word[:-1]
		if (
			len(word) > 3
			and word.endswith("s")
			and not word.endswith(("ss", "us", "is"))
		):
			return word[:-1]
		return word

	return re.sub(r"[^\W\d_]+", singular, value, flags=re.UNICODE)


def _notion_id(label: str) -> str:
	canonical = unicodedata.normalize("NFKD", _singularize(_normalize_query(label)))
	canonical = "".join(
		character
		for character in canonical
		if not unicodedata.combining(character)
	)
	return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def generate_seed_queries(
	rows: Iterable[Mapping[str, object]],
) -> list[dict[str, str | float]]:
	"""Generate and deduplicate label, singular and life-situation queries."""
	unique: dict[tuple[str, str], float] = {}
	for row in rows:
		label_value = row.get("notion_libelle")
		if not isinstance(label_value, str) or not label_value.strip():
			continue
		label = _normalize_query(label_value)
		situation_value = row.get("situation_de_vie")
		situation = (
			_normalize_query(situation_value)
			if isinstance(situation_value, str) and situation_value.strip()
			else ""
		)
		notion_id = _notion_id(label)
		candidates = [
			(label, _SCORES["label"]),
			(_normalize_query(_singularize(label)), _SCORES["singular"]),
		]
		if situation:
			candidates.append((f"{label} {situation}", _SCORES["situation"]))

		for query, score in candidates:
			if not query:
				continue
			key = (notion_id, query)
			unique[key] = max(score, unique.get(key, 0.0))

	return [
		{
			"notion_id": notion_id,
			"requete": query,
			"score_rattachement": score,
		}
		for (notion_id, query), score in unique.items()
	]


def build_seed_queries(client: BigQueryClient) -> int:
	"""Rebuild raw.requetes_candidates from validated extracted notions."""
	result = client.query(_VALIDATED_NOTIONS_SQL)
	if isinstance(result, QueryJob):
		raise ValueError("Le client BigQuery ne doit pas être en mode dry-run")
	rows = generate_seed_queries(result)
	if not rows:
		return 0
	client.insert(
		"raw.requetes_candidates",
		rows,
		schema=_SEED_SCHEMA,
		write_disposition=cast(
			WriteDisposition, bigquery.WriteDisposition.WRITE_TRUNCATE
		),
	)
	return len(rows)