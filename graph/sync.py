"""Synchronize marts into Neo4j in bounded, idempotent transactions."""

from dataclasses import asdict, dataclass
from datetime import date

from google.cloud import bigquery
from neo4j import Driver, ManagedTransaction

from graph.export import ExportBatch, iter_table_batches
from vil_pipeline.tracking import tracked_run

_NODE_QUERIES = {
    "dim_code": """
UNWIND $rows AS r
MERGE (n:Code {legifrance_id: r.legifrance_id})
SET n.code_id = r.code_id, n.libelle = r.libelle, n.ordre = r.ordre
RETURN collect(r.__sync_index) AS processed
""",
    "dim_livre": """
UNWIND $rows AS r
MERGE (n:Livre {legifrance_id: r.legifrance_id})
SET n.livre_id = r.livre_id, n.libelle = r.libelle, n.ordre = r.ordre
RETURN collect(r.__sync_index) AS processed
""",
    "dim_titre": """
UNWIND $rows AS r
MERGE (n:Titre {legifrance_id: r.legifrance_id})
SET n.titre_id = r.titre_id, n.libelle = r.libelle, n.ordre = r.ordre
RETURN collect(r.__sync_index) AS processed
""",
    "dim_article": """
UNWIND $rows AS r
MERGE (n:Article {article_id: r.article_id})
SET n.numero = r.numero, n.etat = r.etat, n.date_debut = r.date_debut,
    n.date_fin = r.date_fin, n.texte_ref = r.texte_ref
RETURN collect(r.__sync_index) AS processed
""",
    "dim_notion": """
UNWIND $rows AS r
MERGE (n:Notion {notion_id: r.notion_id})
SET n.libelle = r.libelle, n.definition_courte = r.definition_courte,
    n.score_confiance = r.score_confiance
RETURN collect(r.__sync_index) AS processed
""",
    "dim_situation_vie": """
UNWIND $rows AS r
MERGE (n:SituationDeVie {situation_id: r.situation_id})
SET n.libelle = r.libelle
RETURN collect(r.__sync_index) AS processed
""",
    "dim_requete": """
UNWIND $rows AS r
MERGE (n:Requete {requete_id: r.requete_id})
SET n.texte = r.texte, n.pays = r.pays, n.langue = r.langue,
    n.pays_langue_id = r.pays_langue_id
RETURN collect(r.__sync_index) AS processed
""",
    "dim_intention": """
UNWIND $rows AS r
MERGE (n:Intention {type: r.type})
RETURN collect(r.__sync_index) AS processed
""",
    "fait_metrique_mensuelle": """
UNWIND $rows AS r
MATCH (:Requete {requete_id: r.requete_id, pays_langue_id: r.pays_langue_id})
MERGE (n:Metrique {requete_id: r.requete_id, mois: r.mois})
SET n.volume = r.volume, n.cpc = r.cpc, n.concurrence = r.concurrence
RETURN collect(r.__sync_index) AS processed
""",
    "fait_resultat_serp": """
UNWIND $rows AS r
MATCH (:Requete {requete_id: r.requete_id, pays_langue_id: r.pays_langue_id})
MERGE (n:ResultatSERP {
    requete_id: r.requete_id, date: r.date_resultat, position: r.position
})
SET n.domaine = r.domaine, n.url = r.url
RETURN collect(r.__sync_index) AS processed
""",
}

_RELATION_QUERIES = {
    "dim_livre": """
UNWIND $rows AS r
MATCH (a:Code {code_id: r.code_id}), (b:Livre {livre_id: r.livre_id})
MERGE (a)-[:CONTIENT]->(b)
RETURN collect(r.__sync_index) AS processed
""",
    "dim_titre": """
UNWIND $rows AS r
MATCH (a:Livre {livre_id: r.livre_id}), (b:Titre {titre_id: r.titre_id})
MERGE (a)-[:CONTIENT]->(b)
RETURN collect(r.__sync_index) AS processed
""",
    "dim_article": """
UNWIND $rows AS r
MATCH (a:Titre {titre_id: r.titre_id}), (b:Article {article_id: r.article_id})
MERGE (a)-[:CONTIENT]->(b)
RETURN collect(r.__sync_index) AS processed
""",
    "fait_extraction": """
UNWIND $rows AS r
MATCH (a:Notion {notion_id: r.notion_id}), (b:Article {article_id: r.article_id})
MERGE (a)-[:SE_FONDE_SUR]->(b)
RETURN collect(r.__sync_index) AS processed
""",
    "pont_notion_situation": """
UNWIND $rows AS r
MATCH (a:Notion {notion_id: r.notion_id}),
      (b:SituationDeVie {situation_id: r.situation_id})
MERGE (a)-[:APPARTIENT_A]->(b)
RETURN collect(r.__sync_index) AS processed
""",
    "fait_notion_requete": """
UNWIND $rows AS r
MATCH (a:Notion {notion_id: r.notion_id}), (b:Requete {requete_id: r.requete_id})
MERGE (a)-[e:EST_EXPRIMEE_PAR]->(b)
SET e.score = r.score_rattachement
RETURN collect(r.__sync_index) AS processed
""",
    "dim_requete": """
UNWIND $rows AS r
MATCH (a:Requete {requete_id: r.requete_id}), (b:Intention {type: r.intention_type})
MERGE (a)-[:A_POUR_INTENTION]->(b)
RETURN collect(r.__sync_index) AS processed
""",
    "fait_metrique_mensuelle": """
UNWIND $rows AS r
MATCH (a:Requete {requete_id: r.requete_id, pays_langue_id: r.pays_langue_id}),
      (b:Metrique {requete_id: r.requete_id, mois: r.mois})
MERGE (a)-[:A_POUR_METRIQUE]->(b)
RETURN collect(r.__sync_index) AS processed
""",
    "fait_resultat_serp": """
UNWIND $rows AS r
MATCH (a:Requete {requete_id: r.requete_id, pays_langue_id: r.pays_langue_id}),
      (b:ResultatSERP {
        requete_id: r.requete_id, date: r.date_resultat, position: r.position
      })
MERGE (a)-[:A_POUR_RESULTAT]->(b)
RETURN collect(r.__sync_index) AS processed
""",
    "RENVOIE_A": """
UNWIND $rows AS r
MATCH (a:Article {article_id: r.article_source_id}),
      (b:Article {article_id: r.article_cible_id})
MERGE (a)-[:RENVOIE_A]->(b)
RETURN collect(r.__sync_index) AS processed
""",
    "MODIFIE": """
UNWIND $rows AS r
MATCH (a:Article {article_id: r.article_source_id}),
      (b:Article {article_id: r.article_cible_id})
MERGE (a)-[:MODIFIE]->(b)
RETURN collect(r.__sync_index) AS processed
""",
    "ABROGE": """
UNWIND $rows AS r
MATCH (a:Article {article_id: r.article_source_id}),
      (b:Article {article_id: r.article_cible_id})
MERGE (a)-[:ABROGE]->(b)
RETURN collect(r.__sync_index) AS processed
""",
}

_RELATION_TABLES = (
    "dim_livre",
    "dim_titre",
    "dim_article",
    "fait_extraction",
    "pont_notion_situation",
    "fait_notion_requete",
    "dim_requete",
    "fait_metrique_mensuelle",
    "fait_resultat_serp",
    "pont_article_renvoi",
)

_LOOKUPS = {
    ("dim_article_version", "article_id"): """
SELECT article_id, article_version_id, date_debut, date_fin, etat, texte_ref
FROM `dim_article_version`
WHERE article_id IN UNNEST(@ids)
QUALIFY ROW_NUMBER() OVER (PARTITION BY article_id ORDER BY
  (etat = 'VIGUEUR' AND date_debut <= @today AND
   (date_fin IS NULL OR date_fin >= @today)) DESC,
  date_debut DESC, article_version_id DESC) = 1
""",
    ("dim_article_version", "article_version_id"): """
SELECT article_version_id, article_id FROM `dim_article_version`
WHERE article_version_id IN UNNEST(@ids)
""",
    ("dim_chapitre", "chapitre_id"): """
SELECT chapitre_id, titre_id FROM `dim_chapitre` WHERE chapitre_id IN UNNEST(@ids)
""",
    ("dim_pays_langue", "pays_langue_id"): """
SELECT pays_langue_id, pays, langue FROM `dim_pays_langue`
WHERE pays_langue_id IN UNNEST(@ids)
""",
}


@dataclass
class SyncStats:
    run_id: str
    status: str = "SUCCESS"
    node_rows: int = 0
    relation_rows: int = 0
    batches: int = 0


def _lookup(
    client: bigquery.Client,
    dataset: bigquery.DatasetReference,
    table: str,
    key: str,
    ids: list[str],
    *,
    today: date | None = None,
) -> dict[str, dict[str, object]]:
    if not ids:
        return {}
    sql = _LOOKUPS[(table, key)]
    parameters: list[bigquery.ArrayQueryParameter | bigquery.ScalarQueryParameter] = [
        bigquery.ArrayQueryParameter("ids", "STRING", list(set(ids)))
    ]
    if today is not None:
        parameters.append(bigquery.ScalarQueryParameter("today", "DATE", today))
    result = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=parameters, default_dataset=dataset
        ),
    ).result()
    values: dict[str, dict[str, object]] = {}
    for row in result:
        item = dict(row.items())
        identifier = item[key]
        if not isinstance(identifier, str) or identifier in values:
            raise ValueError(f"Invalid or duplicate {table}.{key}.")
        values[identifier] = item
    return values


def _required(
    mapping: dict[str, dict[str, object]], key: str, table: str
) -> dict[str, object]:
    if key not in mapping:
        raise ValueError(f"Missing {table} reference: {key}")
    return mapping[key]


def _write(
    tx: ManagedTransaction, operations: list[tuple[str, list[dict[str, object]]]]
) -> None:
    for query, rows in operations:
        if not rows:
            continue
        indexed = [{**row, "__sync_index": i} for i, row in enumerate(rows)]
        record = tx.run(query, rows=indexed).single(strict=True)
        if sorted(record["processed"]) != list(range(len(rows))):
            raise ValueError(
                "Missing or non-unique graph endpoints; batch rolled back."
            )


def _prepare_nodes(
    client: bigquery.Client,
    dataset: bigquery.DatasetReference,
    batch: ExportBatch,
    today: date,
) -> list[dict[str, object]]:
    rows = [row.model_dump() for row in batch.rows]
    if batch.table == "dim_article":
        ids = [row["article_id"] for row in rows]
        versions = _lookup(
            client,
            dataset,
            "dim_article_version",
            "article_id",
            ids,
            today=today,
        )
        for row in rows:
            version = versions.get(row["article_id"], {})
            row.update(
                {
                    name: version.get(name)
                    for name in ("etat", "date_debut", "date_fin", "texte_ref")
                }
            )
    elif batch.table == "dim_requete":
        ids = [row["pays_langue_id"] for row in rows]
        contexts = _lookup(
            client,
            dataset,
            "dim_pays_langue",
            "pays_langue_id",
            ids,
        )
        for row in rows:
            context = _required(contexts, row["pays_langue_id"], "dim_pays_langue")
            row.update(pays=context["pays"], langue=context["langue"])
    return rows


def _prepare_relations(
    client: bigquery.Client, dataset: bigquery.DatasetReference, batch: ExportBatch
) -> list[tuple[str, list[dict[str, object]]]]:
    rows = [row.model_dump() for row in batch.rows]
    if batch.table == "dim_article":
        rows = [row for row in rows if row["chapitre_id"] is not None]
        chapters = _lookup(
            client,
            dataset,
            "dim_chapitre",
            "chapitre_id",
            [row["chapitre_id"] for row in rows],
        )
        for row in rows:
            row["titre_id"] = _required(chapters, row["chapitre_id"], "dim_chapitre")[
                "titre_id"
            ]
    elif batch.table == "fait_extraction":
        versions = _lookup(
            client,
            dataset,
            "dim_article_version",
            "article_version_id",
            [row["article_version_id"] for row in rows],
        )
        for row in rows:
            row["article_id"] = _required(
                versions, row["article_version_id"], "dim_article_version"
            )["article_id"]
    elif batch.table == "dim_requete":
        rows = [row for row in rows if row["intention_type"] is not None]
    if batch.table == "pont_article_renvoi":
        return [
            (
                _RELATION_QUERIES[kind],
                [row for row in rows if row["type_relation"] == kind],
            )
            for kind in ("RENVOIE_A", "MODIFIE", "ABROGE")
        ]
    return [(_RELATION_QUERIES[batch.table], rows)]


def sync_graph(
    driver: Driver,
    client: bigquery.Client,
    dataset: bigquery.DatasetReference,
    *,
    ops_dataset: bigquery.DatasetReference | None = None,
    batch_size: int = 1000,
) -> SyncStats:
    """Upsert graph nodes, then relations, and journal the outcome in BigQuery."""
    ops = ops_dataset or bigquery.DatasetReference(dataset.project, "ops")
    with tracked_run(client, "graph_sync", dataset=ops) as run:
        stats = SyncStats(run_id=run.run_id)
        try:
            if batch_size <= 0:
                raise ValueError("batch_size must be positive.")
            with driver.session() as session:
                for table, query in _NODE_QUERIES.items():
                    for batch in iter_table_batches(
                        client, dataset, table, batch_size=batch_size
                    ):
                        rows = _prepare_nodes(
                            client, dataset, batch, run.started.date()
                        )
                        session.execute_write(_write, [(query, rows)])
                        stats.node_rows += len(rows)
                        stats.batches += 1
                for table in _RELATION_TABLES:
                    for batch in iter_table_batches(
                        client, dataset, table, batch_size=batch_size
                    ):
                        operations = _prepare_relations(client, dataset, batch)
                        session.execute_write(_write, operations)
                        stats.relation_rows += sum(len(rows) for _, rows in operations)
                        stats.batches += 1
        except BaseException:
            stats.status = "FAILED"
            raise
        finally:
            run.counts = asdict(stats)
        return stats
