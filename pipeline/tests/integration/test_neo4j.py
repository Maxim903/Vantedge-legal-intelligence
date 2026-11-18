"""Tests d'intégration sur une instance Neo4j dédiée."""

from uuid import uuid4

from neo4j import Driver


def test_neo4j_merge_is_idempotent(neo4j_driver: Driver) -> None:
    run_id = str(uuid4())
    with neo4j_driver.session(database="neo4j") as session:
        try:
            for score in (0.4, 0.8):
                session.run(
                    """
                        MERGE (n:IntegrationTest {run_id: $run_id, role: 'notion'})
                        MERGE (r:IntegrationTest {run_id: $run_id, role: 'requete'})
                        MERGE (n)-[l:TEST_EXPRIMEE_PAR]->(r)
                        SET l.score = $score
                        """,
                    run_id=run_id,
                    score=score,
                ).consume()

            record = session.run(
                "MATCH (n:IntegrationTest {run_id: $run_id, role: 'notion'})"
                "-[l:TEST_EXPRIMEE_PAR]->"
                "(r:IntegrationTest {run_id: $run_id, role: 'requete'}) "
                "RETURN count(l) AS nombre, max(l.score) AS score",
                run_id=run_id,
            ).single(strict=True)
            assert record["nombre"] == 1
            assert record["score"] == 0.8
        finally:
            session.run(
                "MATCH (n:IntegrationTest {run_id: $run_id}) DETACH DELETE n",
                run_id=run_id,
            ).consume()
