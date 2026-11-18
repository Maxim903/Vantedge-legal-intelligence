"""Compare marts and graph counts at the synchronization's relationship grain."""

from dataclasses import dataclass

from google.cloud import bigquery
from neo4j import Driver, ManagedTransaction

from vil_pipeline.tracking import tracked_run

_RELATIONS = {
    ("CONTIENT", "Code", "Livre"): "CONTIENT (Code->Livre)",
    ("CONTIENT", "Livre", "Titre"): "CONTIENT (Livre->Titre)",
    ("CONTIENT", "Titre", "Article"): "CONTIENT (Titre->Article)",
    ("SE_FONDE_SUR", "Notion", "Article"): "SE_FONDE_SUR",
    ("APPARTIENT_A", "Notion", "SituationDeVie"): "APPARTIENT_A",
    ("EST_EXPRIMEE_PAR", "Notion", "Requete"): "EST_EXPRIMEE_PAR",
    ("A_POUR_INTENTION", "Requete", "Intention"): "A_POUR_INTENTION",
    ("A_POUR_METRIQUE", "Requete", "Metrique"): "A_POUR_METRIQUE",
    ("A_POUR_RESULTAT", "Requete", "ResultatSERP"): "A_POUR_RESULTAT",
    ("RENVOIE_A", "Article", "Article"): "RENVOIE_A",
    ("MODIFIE", "Article", "Article"): "MODIFIE",
    ("ABROGE", "Article", "Article"): "ABROGE",
}
_CATEGORIES = ("Notion", "Article", "Requete", *_RELATIONS.values())
_INVALID = {
    "invalid_chapitre": "articles avec chapitre introuvable",
    "invalid_version": "extractions avec version d'article introuvable",
    "invalid_metrique_contexte": "métriques avec requête ou contexte invalide",
    "invalid_serp_contexte": "résultats SERP avec requête ou contexte invalide",
    "invalid_renvoi": "renvois avec type invalide",
}

# Every relationship is counted at MERGE grain, not at raw fact-row grain.
_MARTS_SQL = """
SELECT 'Notion' AS categorie, COUNT(*) AS total FROM `dim_notion`
UNION ALL SELECT 'Article', COUNT(*) FROM `dim_article`
UNION ALL SELECT 'Requete', COUNT(*) FROM `dim_requete`
UNION ALL SELECT 'CONTIENT (Code->Livre)', COUNT(*) FROM (
  SELECT DISTINCT code_id, livre_id FROM `dim_livre`
)
UNION ALL SELECT 'CONTIENT (Livre->Titre)', COUNT(*) FROM (
  SELECT DISTINCT livre_id, titre_id FROM `dim_titre`
)
UNION ALL SELECT 'CONTIENT (Titre->Article)', COUNT(*) FROM (
  SELECT DISTINCT c.titre_id, a.article_id
  FROM `dim_article` a LEFT JOIN `dim_chapitre` c USING (chapitre_id)
  WHERE a.chapitre_id IS NOT NULL
)
UNION ALL SELECT 'SE_FONDE_SUR', COUNT(*) FROM (
  SELECT DISTINCT e.notion_id, v.article_id
  FROM `fait_extraction` e LEFT JOIN `dim_article_version` v USING (article_version_id)
)
UNION ALL SELECT 'APPARTIENT_A', COUNT(*) FROM (
  SELECT DISTINCT notion_id, situation_id FROM `pont_notion_situation`
)
UNION ALL SELECT 'EST_EXPRIMEE_PAR', COUNT(*) FROM (
  SELECT DISTINCT notion_id, requete_id FROM `fait_notion_requete`
)
UNION ALL SELECT 'A_POUR_INTENTION', COUNT(*) FROM (
  SELECT DISTINCT requete_id, intention_type FROM `dim_requete`
  WHERE intention_type IS NOT NULL
)
UNION ALL SELECT 'A_POUR_METRIQUE', COUNT(*) FROM (
  SELECT DISTINCT requete_id, mois FROM `fait_metrique_mensuelle`
)
UNION ALL SELECT 'A_POUR_RESULTAT', COUNT(*) FROM (
  SELECT DISTINCT requete_id, date_resultat, position FROM `fait_resultat_serp`
)
UNION ALL SELECT 'RENVOIE_A', COUNT(*) FROM (
  SELECT DISTINCT article_source_id, article_cible_id FROM `pont_article_renvoi`
  WHERE type_relation = 'RENVOIE_A'
)
UNION ALL SELECT 'MODIFIE', COUNT(*) FROM (
  SELECT DISTINCT article_source_id, article_cible_id FROM `pont_article_renvoi`
  WHERE type_relation = 'MODIFIE'
)
UNION ALL SELECT 'ABROGE', COUNT(*) FROM (
  SELECT DISTINCT article_source_id, article_cible_id FROM `pont_article_renvoi`
  WHERE type_relation = 'ABROGE'
)
UNION ALL SELECT 'invalid_chapitre', COUNT(*)
FROM `dim_article` a LEFT JOIN `dim_chapitre` c USING (chapitre_id)
WHERE a.chapitre_id IS NOT NULL AND c.chapitre_id IS NULL
UNION ALL SELECT 'invalid_version', COUNT(*)
FROM `fait_extraction` e LEFT JOIN `dim_article_version` v USING (article_version_id)
WHERE v.article_version_id IS NULL
UNION ALL SELECT 'invalid_metrique_contexte', COUNT(*)
FROM `fait_metrique_mensuelle` f LEFT JOIN `dim_requete` r
  ON f.requete_id = r.requete_id AND f.pays_langue_id = r.pays_langue_id
WHERE r.requete_id IS NULL
UNION ALL SELECT 'invalid_serp_contexte', COUNT(*)
FROM `fait_resultat_serp` f LEFT JOIN `dim_requete` r
  ON f.requete_id = r.requete_id AND f.pays_langue_id = r.pays_langue_id
WHERE r.requete_id IS NULL
UNION ALL SELECT 'invalid_renvoi', COUNT(*) FROM `pont_article_renvoi`
WHERE type_relation IS NULL OR type_relation NOT IN ('RENVOIE_A', 'MODIFIE', 'ABROGE')
"""

_NODES_CYPHER = """
CALL { MATCH (n:Notion) RETURN count(n) AS notions }
CALL { MATCH (n:Article) RETURN count(n) AS articles }
CALL { MATCH (n:Requete) RETURN count(n) AS requetes }
RETURN notions, articles, requetes
"""
_RELATIONS_CYPHER = """
MATCH (a)-[r]->(b)
RETURN type(r) AS type, labels(a) AS source, labels(b) AS cible, count(r) AS total
"""


@dataclass(frozen=True)
class CountDifference:
    category: str
    marts: int
    neo4j: int


def _count(value: object, description: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Compte invalide pour {description} : {value!r}")
    return value


def _marts_counts(
    client: bigquery.Client, dataset: bigquery.DatasetReference
) -> dict[str, int]:
    result = client.query(
        _MARTS_SQL, job_config=bigquery.QueryJobConfig(default_dataset=dataset)
    ).result()
    counts: dict[str, int] = {}
    allowed = set(_CATEGORIES) | set(_INVALID)
    for row in result:
        category = row["categorie"]
        if (
            not isinstance(category, str)
            or category not in allowed
            or category in counts
        ):
            raise ValueError(
                f"Catégorie BigQuery inattendue ou dupliquée : {category!r}"
            )
        counts[category] = _count(row["total"], category)
    missing = allowed - counts.keys()
    if missing:
        raise ValueError(f"Comptes BigQuery manquants : {', '.join(sorted(missing))}")
    invalid = [
        f"{label} : {counts[key]}" for key, label in _INVALID.items() if counts[key]
    ]
    if invalid:
        raise ValueError("Références marts invalides : " + "; ".join(invalid))
    return {category: counts[category] for category in _CATEGORIES}


def _neo4j_counts(tx: ManagedTransaction) -> dict[str, int]:
    nodes = tx.run(_NODES_CYPHER).single(strict=True)
    counts = dict.fromkeys(_CATEGORIES, 0)
    for category, column in (
        ("Notion", "notions"),
        ("Article", "articles"),
        ("Requete", "requetes"),
    ):
        counts[category] = _count(nodes[column], category)
    for record in tx.run(_RELATIONS_CYPHER):
        relation_type = record["type"]
        source = record["source"]
        target = record["cible"]
        matches = [
            label
            for (kind, start, end), label in _RELATIONS.items()
            if kind == relation_type and start in source and end in target
        ]
        if len(matches) == 1:
            category = matches[0]
        else:
            category = (
                f"Relation inattendue {relation_type} "
                f"({':'.join(sorted(source)) or '?'}"
                f"->{':'.join(sorted(target)) or '?'})"
            )
        counts[category] = counts.get(category, 0) + _count(record["total"], category)
    return counts


def check_graph_consistency(
    client: bigquery.Client,
    driver: Driver,
    dataset: bigquery.DatasetReference,
    *,
    database: str | None = None,
) -> list[CountDifference]:
    """Return all count differences; propagate invalid data and service failures."""
    ops = bigquery.DatasetReference(dataset.project, "ops")
    with tracked_run(client, "check_graph_consistency", dataset=ops) as run:
        marts = _marts_counts(client, dataset)
        with driver.session(database=database) as session:
            graph = session.execute_read(_neo4j_counts)
        differences = [
            CountDifference(category, marts.get(category, 0), graph.get(category, 0))
            for category in sorted(marts.keys() | graph.keys())
            if marts.get(category, 0) != graph.get(category, 0)
        ]
        run.counts = {
            "categories": len(marts.keys() | graph.keys()),
            "differences": len(differences),
        }
        if differences:
            run.status = "INCONSISTENT"
            run.error = "Écarts entre les comptes marts et Neo4j."
        return differences
