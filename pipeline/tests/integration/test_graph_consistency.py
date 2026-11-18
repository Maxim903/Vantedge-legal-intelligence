"""Verify graph-side counts against a real Neo4j server."""

from uuid import uuid4

from neo4j import Driver

from vil_pipeline.jobs.check_graph_consistency import _neo4j_counts


def test_counts_nodes_valid_relations_and_wrong_endpoints(neo4j_driver: Driver) -> None:
    key = "consistency-" + uuid4().hex
    with neo4j_driver.session() as session:
        before = session.execute_read(_neo4j_counts)
        try:
            session.run(
                """
CREATE (n:Notion {notion_id: $id}), (a:Article {article_id: $id}),
       (q:Requete {requete_id: $id})
CREATE (n)-[:SE_FONDE_SUR]->(a), (q)-[:SE_FONDE_SUR]->(n)
""",
                id=key,
            ).consume()
            after = session.execute_read(_neo4j_counts)
            for category in ("Notion", "Article", "Requete", "SE_FONDE_SUR"):
                assert after[category] == before[category] + 1
            unexpected = "Relation inattendue SE_FONDE_SUR (Requete->Notion)"
            assert after[unexpected] == before.get(unexpected, 0) + 1
        finally:
            session.run(
                "MATCH (n) WHERE n.notion_id = $id OR n.article_id = $id "
                "OR n.requete_id = $id DETACH DELETE n",
                id=key,
            ).consume()
