"""Export and atomically import human review decisions for extracted entities."""

import csv
import json
import math
from pathlib import Path

from google.cloud.bigquery import QueryJob, ScalarQueryParameter

from vil_pipeline.clients.bigquery import BigQueryClient

_FIELDS = (
	"extraction_id", "article_version_id", "notion_libelle", "situation_de_vie",
	"score_confiance", "modele_llm", "version_prompt", "extrait_le",
	"statut_validation", "valide_par_initial_json", "nouveau_statut",
	"nouveau_valide_par",
)
_STATUSES = frozenset({"AUTO", "A_REVOIR", "VALIDE", "REJETE"})
_REVIEW_STATUSES = frozenset({"A_REVOIR", "VALIDE", "REJETE"})

_EXPORT_SQL = """
SELECT extraction_id, article_version_id, notion_libelle, situation_de_vie,
       score_confiance, modele_llm, version_prompt, extrait_le,
       statut_validation, valide_par
FROM `raw.entites_extraites`
WHERE statut_validation = 'A_REVOIR' OR score_confiance < @threshold
ORDER BY extraction_id
"""

_IMPORT_SQL = """
CREATE TEMP TABLE review AS
SELECT
  JSON_VALUE(item, '$.extraction_id') AS extraction_id,
  JSON_VALUE(item, '$.statut_initial') AS statut_initial,
  JSON_VALUE(item, '$.valide_par_initial') AS valide_par_initial,
  JSON_VALUE(item, '$.nouveau_statut') AS nouveau_statut,
  JSON_VALUE(item, '$.nouveau_valide_par') AS nouveau_valide_par
FROM UNNEST(JSON_QUERY_ARRAY(PARSE_JSON(@decisions))) AS item;

BEGIN TRANSACTION;
ASSERT NOT EXISTS (
  SELECT r.extraction_id
  FROM review AS r
  LEFT JOIN `raw.entites_extraites` AS e ON e.extraction_id = r.extraction_id
  GROUP BY r.extraction_id, r.statut_initial, r.valide_par_initial
  HAVING COUNT(e.extraction_id) != 1
      OR COUNTIF(
        e.statut_validation = r.statut_initial
        AND e.valide_par IS NOT DISTINCT FROM r.valide_par_initial
      ) != 1
) AS 'Entité absente, dupliquée ou modifiée depuis l’export';

UPDATE `raw.entites_extraites` AS e
SET statut_validation = r.nouveau_statut, valide_par = r.nouveau_valide_par
FROM review AS r
WHERE e.extraction_id = r.extraction_id;
ASSERT @@row_count = (SELECT COUNT(*) FROM review)
  AS 'Nombre de mises à jour inattendu';
COMMIT TRANSACTION;
"""


def export_review(
	client: BigQueryClient, output: Path, *, threshold: float
) -> int:
	"""Export selected entities, preserving their initial review state."""
	if not math.isfinite(threshold) or not 0 <= threshold <= 1:
		raise ValueError("Le seuil doit être un nombre fini entre 0 et 1")
	result = client.query(
		_EXPORT_SQL, [ScalarQueryParameter("threshold", "FLOAT64", threshold)]
	)
	if isinstance(result, QueryJob):
		raise ValueError("Le client BigQuery ne doit pas être en mode dry-run")
	rows = list(result)
	seen: set[str] = set()
	exported: list[dict[str, object]] = []
	for row in rows:
		extraction_id = row["extraction_id"]
		status = row["statut_validation"]
		reviewer = row["valide_par"]
		if not isinstance(extraction_id, str) or not extraction_id.strip():
			raise ValueError("Identifiant d'extraction vide ou invalide")
		if extraction_id in seen:
			raise ValueError(f"Identifiant d'extraction dupliqué : {extraction_id}")
		if status not in _STATUSES:
			raise ValueError(f"Statut de validation invalide pour {extraction_id}")
		if reviewer is not None and not isinstance(reviewer, str):
			raise ValueError(f"Validateur invalide pour {extraction_id}")
		seen.add(extraction_id)
		exported.append({
			"extraction_id": extraction_id,
			"article_version_id": row["article_version_id"],
			"notion_libelle": row["notion_libelle"],
			"situation_de_vie": row["situation_de_vie"],
			"score_confiance": row["score_confiance"],
			"modele_llm": row["modele_llm"],
			"version_prompt": row["version_prompt"],
			"extrait_le": row["extrait_le"],
			"statut_validation": status,
			"valide_par_initial_json": json.dumps(reviewer, ensure_ascii=False),
			"nouveau_statut": "",
			"nouveau_valide_par": "",
		})
	output.parent.mkdir(parents=True, exist_ok=True)
	with output.open("x", encoding="utf-8", newline="") as stream:
		writer = csv.DictWriter(stream, fieldnames=_FIELDS)
		writer.writeheader()
		writer.writerows(exported)
	return len(exported)


def import_review(client: BigQueryClient, source: Path) -> int:
	"""Validate the entire review CSV, then apply decisions in one transaction."""
	decisions: list[dict[str, str | None]] = []
	seen: set[str] = set()
	with source.open(encoding="utf-8-sig", newline="") as stream:
		reader = csv.DictReader(stream)
		if reader.fieldnames != list(_FIELDS):
			raise ValueError("Colonnes du CSV de revue invalides")
		for row in reader:
			if None in row or any(value is None for value in row.values()):
				raise ValueError(f"Ligne CSV invalide : {reader.line_num}")
			extraction_id = row["extraction_id"]
			if not extraction_id.strip() or extraction_id != extraction_id.strip():
				raise ValueError(f"Identifiant invalide à la ligne {reader.line_num}")
			if extraction_id in seen:
				raise ValueError(f"Identifiant d'extraction dupliqué : {extraction_id}")
			seen.add(extraction_id)
			initial_status = row["statut_validation"]
			if initial_status not in _STATUSES:
				raise ValueError(f"Statut initial invalide : {extraction_id}")
			try:
				initial_reviewer = json.loads(row["valide_par_initial_json"])
			except json.JSONDecodeError as error:
				raise ValueError(
					f"Validateur initial invalide : {extraction_id}"
				) from error
			if initial_reviewer is not None and not isinstance(initial_reviewer, str):
				raise ValueError(f"Validateur initial invalide : {extraction_id}")
			status = row["nouveau_statut"].strip()
			reviewer = row["nouveau_valide_par"].strip()
			if not status and not reviewer:
				continue
			if status not in _REVIEW_STATUSES or not reviewer:
				raise ValueError(
					f"Décision ou validateur invalide pour {extraction_id} : "
					"utiliser A_REVOIR, VALIDE ou REJETE et renseigner le validateur"
				)
			decisions.append({
				"extraction_id": extraction_id,
				"statut_initial": initial_status,
				"valide_par_initial": initial_reviewer,
				"nouveau_statut": status,
				"nouveau_valide_par": reviewer,
			})
	if decisions:
		result = client.query(
			_IMPORT_SQL,
			[ScalarQueryParameter(
				"decisions", "STRING", json.dumps(decisions, ensure_ascii=False)
			)],
		)
		if isinstance(result, QueryJob):
			raise ValueError("Le client BigQuery ne doit pas être en mode dry-run")
	return len(decisions)
