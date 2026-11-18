"""Synchronize a representative marts fixture against a real Neo4j instance."""

from datetime import date
from unittest.mock import Mock
from uuid import uuid4

import pytest
from google.cloud import bigquery
from graph.export import TABLE_MODELS, ExportBatch
from graph.sync import _LOOKUPS, _NODE_QUERIES, _RELATION_QUERIES, _write, sync_graph
from neo4j import Driver

from vil_pipeline.graph.apply_constraints import apply_constraints


def test_sync_twice_is_idempotent_and_updates_properties(
    neo4j_driver: Driver, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = "sync-" + uuid4().hex
    dataset = bigquery.DatasetReference("test-project", "marts")
    sources = {
        "dim_code": [dict(code_id=key, legifrance_id=key, libelle="Code", ordre=1)],
        "dim_livre": [
            dict(livre_id=key, code_id=key, legifrance_id=key, libelle="Livre", ordre=1)
        ],
        "dim_titre": [
            dict(
                titre_id=key, livre_id=key, legifrance_id=key, libelle="Titre", ordre=1
            )
        ],
        "dim_article": [
            dict(article_id=key, chapitre_id=key, numero="1"),
            dict(article_id=key + "-2", chapitre_id=None, numero="2"),
        ],
        "dim_notion": [
            dict(
                notion_id=key,
                libelle="Notion",
                definition_courte=None,
                score_confiance=0.8,
            )
        ],
        "dim_situation_vie": [dict(situation_id=key, libelle="Situation")],
        "dim_requete": [
            dict(
                requete_id=key,
                texte="Requête",
                pays_langue_id=key,
                intention_type="informationnelle",
            )
        ],
        "dim_intention": [{"type": "informationnelle"}],
        "fait_metrique_mensuelle": [
            dict(
                requete_id=key,
                pays_langue_id=key,
                mois=date(2025, 1, 1),
                volume=100,
                cpc=0.3,
                concurrence=0.2,
            )
        ],
        "fait_resultat_serp": [
            dict(
                requete_id=key,
                pays_langue_id=key,
                date_resultat=date(2025, 1, 2),
                position=1,
                domaine="example.org",
                url="https://example.org",
            )
        ],
        "fait_extraction": [
            dict(extraction_id=key, article_version_id=key, notion_id=key)
        ],
        "pont_notion_situation": [dict(notion_id=key, situation_id=key)],
        "fait_notion_requete": [
            dict(notion_id=key, requete_id=key, score_rattachement=0.9)
        ],
        "pont_article_renvoi": [
            dict(article_source_id=key, article_cible_id=key + "-2", type_relation=kind)
            for kind in ("RENVOIE_A", "MODIFIE", "ABROGE")
        ],
    }

    def batches(client, selected_dataset, table, *, batch_size):
        assert selected_dataset == dataset
        values = sources.get(table, [])
        for start in range(0, len(values), batch_size):
            yield ExportBatch(
                table=table,
                rows=[
                    TABLE_MODELS[table].model_validate(row)
                    for row in values[start : start + batch_size]
                ],
                next_page_token=None,
            )

    monkeypatch.setattr("graph.sync.iter_table_batches", batches)
    client = Mock(spec=bigquery.Client)
    logs = []

    def query(sql, *, job_config):
        parameters = {
            param.name: param.value if hasattr(param, "value") else param.values
            for param in job_config.query_parameters
        }
        if "`pipeline_runs`" in sql:
            assert job_config.default_dataset == bigquery.DatasetReference(
                "test-project", "ops"
            )
            if "UPDATE" in sql:
                logs.append(parameters)
            return Mock(result=Mock(return_value=[]))
        assert job_config.default_dataset == dataset
        ids = parameters["ids"]
        if sql == _LOOKUPS[("dim_article_version", "article_id")]:
            assert "today" in parameters
            values = [
                dict(
                    article_id=key,
                    article_version_id=key,
                    date_debut=date(2020, 1, 1),
                    date_fin=None,
                    etat="VIGUEUR",
                    texte_ref="bq-reference",
                )
            ]
        elif sql == _LOOKUPS[("dim_article_version", "article_version_id")]:
            values = [dict(article_version_id=key, article_id=key)]
        elif sql == _LOOKUPS[("dim_chapitre", "chapitre_id")]:
            values = [dict(chapitre_id=key, titre_id=key)]
        else:
            assert sql == _LOOKUPS[("dim_pays_langue", "pays_langue_id")]
            values = [dict(pays_langue_id=key, pays="FR", langue="fr")]
        return Mock(
            result=Mock(
                return_value=[
                    item
                    for item in values
                    if any(item.get(column) in ids for column in item)
                ]
            )
        )

    client.query.side_effect = query
    apply_constraints(neo4j_driver)
    with neo4j_driver.session() as session:
        intent_existed = (
            session.run(
                "MATCH (n:Intention {type: 'informationnelle'}) RETURN count(n) AS c"
            ).single(strict=True)["c"]
            > 0
        )

        def snapshot():
            return [
                (
                    sorted(record["nodes"], key=lambda row: row[0]),
                    sorted(record["edges"], key=lambda row: (row[0], row[1], row[2])),
                )
                for record in session.run(
                    """
MATCH (n)
WHERE n.code_id = $id OR n.livre_id = $id OR n.titre_id = $id
  OR n.article_id STARTS WITH $id OR n.notion_id = $id OR n.situation_id = $id
  OR n.requete_id = $id OR (n:Intention AND n.type = 'informationnelle')
WITH collect(n) AS nodes
UNWIND nodes AS n
OPTIONAL MATCH (n)-[r]->(m)
WHERE m IN nodes
RETURN collect(DISTINCT [elementId(n), labels(n), properties(n)]) AS nodes,
       collect(DISTINCT CASE WHEN r IS NOT NULL THEN
           [elementId(n), type(r), elementId(m), properties(r)] END) AS edges
""",
                    id=key,
                )
            ]

        try:
            first = sync_graph(neo4j_driver, client, dataset, batch_size=2)
            before = snapshot()
            second = sync_graph(neo4j_driver, client, dataset, batch_size=2)
            after = snapshot()
            assert first.status == second.status == "SUCCESS"
            assert before == after
            assert len(before[0][0]) == 11
            assert len(before[0][1]) == 12
            assert {edge[1] for edge in before[0][1]} == {
                "CONTIENT",
                "SE_FONDE_SUR",
                "APPARTIENT_A",
                "EST_EXPRIMEE_PAR",
                "A_POUR_INTENTION",
                "A_POUR_METRIQUE",
                "A_POUR_RESULTAT",
                "RENVOIE_A",
                "MODIFIE",
                "ABROGE",
            }
            article = session.run(
                "MATCH (a:Article {article_id: $id}) RETURN properties(a) AS props",
                id=key,
            ).single(strict=True)["props"]
            assert article["etat"] == "VIGUEUR"
            assert str(article["date_debut"]) == "2020-01-01"
            assert article["texte_ref"] == "bq-reference"
            assert [log["status"] for log in logs] == ["SUCCESS", "SUCCESS"]
            assert logs[0]["run_id"] != logs[1]["run_id"]

            sources["dim_notion"][0]["libelle"] = "Notion actualisée"
            sources["fait_notion_requete"][0]["score_rattachement"] = 0.4
            sources["pont_notion_situation"].clear()
            sync_graph(neo4j_driver, client, dataset, batch_size=2)
            record = session.run(
                """
MATCH (n:Notion {notion_id: $id})-[e:EST_EXPRIMEE_PAR]->(:Requete {requete_id: $id})
RETURN n.libelle AS libelle, e.score AS score
""",
                id=key,
            ).single(strict=True)
            assert record["libelle"] == "Notion actualisée"
            assert record["score"] == 0.4
            assert (
                session.run(
                    "MATCH (:Notion {notion_id: $id})-[r:APPARTIENT_A]->() "
                    "RETURN count(r) AS c",
                    id=key,
                ).single(strict=True)["c"]
                == 1
            )
        finally:
            session.run(
                """
MATCH (n)
WHERE n.code_id = $id OR n.livre_id = $id OR n.titre_id = $id
  OR n.article_id STARTS WITH $id OR n.notion_id = $id OR n.situation_id = $id
  OR n.requete_id = $id
DETACH DELETE n
""",
                id=key,
            ).consume()
            if not intent_existed:
                session.run(
                    "MATCH (n:Intention {type: 'informationnelle'}) DETACH DELETE n"
                ).consume()


def test_missing_endpoint_rolls_back_whole_batch(neo4j_driver: Driver) -> None:
    key = "rollback-" + uuid4().hex
    with neo4j_driver.session() as session:
        session.run(
            "CREATE (:Notion {notion_id: $id}), (:Requete {requete_id: $id})", id=key
        ).consume()
        try:
            rows = [
                dict(notion_id=key, requete_id=key, score_rattachement=0.9),
                dict(
                    notion_id=key, requete_id=key + "-missing", score_rattachement=0.8
                ),
            ]
            with pytest.raises(ValueError, match="endpoints"):
                session.execute_write(
                    _write, [(_RELATION_QUERIES["fait_notion_requete"], rows)]
                )
            count = session.run(
                "MATCH (:Notion {notion_id: $id})-[r]->() RETURN count(r) AS c", id=key
            ).single(strict=True)["c"]
            assert count == 0
        finally:
            session.run(
                "MATCH (n) WHERE n.notion_id = $id OR n.requete_id = $id "
                "DETACH DELETE n",
                id=key,
            ).consume()


def test_context_mismatch_does_not_create_metric(neo4j_driver: Driver) -> None:
    key = "context-" + uuid4().hex
    with neo4j_driver.session() as session:
        session.run(
            "CREATE (:Requete {requete_id: $id, pays_langue_id: 'fr'})", id=key
        ).consume()
        try:
            row = dict(
                requete_id=key,
                pays_langue_id="other",
                mois=date(2025, 1, 1),
                volume=1,
                cpc=0.1,
                concurrence=0.2,
            )
            with pytest.raises(ValueError, match="endpoints"):
                session.execute_write(
                    _write, [(_NODE_QUERIES["fait_metrique_mensuelle"], [row])]
                )
            assert (
                session.run(
                    "MATCH (n:Metrique {requete_id: $id}) RETURN count(n) AS c", id=key
                ).single(strict=True)["c"]
                == 0
            )
        finally:
            session.run(
                "MATCH (n:Requete {requete_id: $id}) DETACH DELETE n", id=key
            ).consume()


def test_duplicate_match_cannot_mask_missing_endpoint(neo4j_driver: Driver) -> None:
    key = "ambiguous-" + uuid4().hex
    with neo4j_driver.session() as session:
        session.run(
            "CREATE (:Titre {titre_id: $id}), (:Titre {titre_id: $id}), "
            "(:Article {article_id: $id})",
            id=key,
        ).consume()
        try:
            rows = [
                dict(titre_id=key, article_id=key),
                dict(titre_id=key, article_id=key + "-missing"),
            ]
            with pytest.raises(ValueError, match="endpoints"):
                session.execute_write(
                    _write, [(_RELATION_QUERIES["dim_article"], rows)]
                )
            assert (
                session.run(
                    "MATCH (:Titre {titre_id: $id})-[r]->() RETURN count(r) AS c",
                    id=key,
                ).single(strict=True)["c"]
                == 0
            )
        finally:
            session.run(
                "MATCH (n) WHERE n.titre_id = $id OR n.article_id = $id "
                "DETACH DELETE n",
                id=key,
            ).consume()
