"""Vérifie les contraintes sur un serveur Neo4j de test."""

from pathlib import Path
from uuid import uuid4

import pytest
from neo4j import Driver
from neo4j.exceptions import ConstraintError

from vil_pipeline.graph.apply_constraints import apply_constraints

_CASES = (
    (
        "Article",
        "article_id",
        "CREATE (:Article {article_id: $value, _test_run: $run})",
    ),
    ("Notion", "notion_id", "CREATE (:Notion {notion_id: $value, _test_run: $run})"),
    (
        "SituationDeVie",
        "situation_id",
        "CREATE (:SituationDeVie {situation_id: $value, _test_run: $run})",
    ),
    (
        "Requete",
        "requete_id",
        "CREATE (:Requete {requete_id: $value, _test_run: $run})",
    ),
    ("Intention", "type", "CREATE (:Intention {type: $value, _test_run: $run})"),
)


def test_constraints_are_idempotent_and_enforced(neo4j_driver: Driver) -> None:
    expected = {(label, prop) for label, prop, _ in _CASES}
    run_id = str(uuid4())
    apply_constraints(neo4j_driver)
    with neo4j_driver.session(database="neo4j") as session:

        def schema() -> set[tuple[str, str]]:
            return {
                (record["labelsOrTypes"][0], record["properties"][0])
                for record in session.run(
                    "SHOW CONSTRAINTS YIELD type, entityType, "
                    "labelsOrTypes, properties "
                    "RETURN type, entityType, labelsOrTypes, properties"
                )
                if record["type"] in {"UNIQUENESS", "NODE_PROPERTY_UNIQUENESS"}
                and record["entityType"] == "NODE"
                and len(record["labelsOrTypes"]) == 1
                and len(record["properties"]) == 1
            } & expected

        before = schema()
        assert before == expected
        apply_constraints(neo4j_driver)
        assert schema() == before

        try:
            for _, _, query in _CASES:
                session.run(query, value=run_id, run=run_id).consume()
                with pytest.raises(ConstraintError):
                    session.run(query, value=run_id, run=run_id).consume()
        finally:
            session.run(
                "MATCH (n) WHERE n._test_run = $run DETACH DELETE n", run=run_id
            ).consume()


def test_constraint_name_conflict_is_reported(
    neo4j_driver: Driver, tmp_path: Path
) -> None:
    name = f"test_conflict_{uuid4().hex}"
    path = tmp_path / "conflict.cypher"
    path.write_text(
        f"CREATE CONSTRAINT {name} IF NOT EXISTS "
        "FOR (n:IntegrationConflict) REQUIRE n.expected IS UNIQUE;\n",
        encoding="utf-8",
    )
    with neo4j_driver.session(database="neo4j") as session:
        session.run(
            f"CREATE CONSTRAINT {name} FOR (n:IntegrationConflict) "
            "REQUIRE n.other IS UNIQUE"
        ).consume()
        try:
            with pytest.raises(RuntimeError, match=r"IntegrationConflict\.expected"):
                apply_constraints(neo4j_driver, path)
        finally:
            session.run(f"DROP CONSTRAINT {name}").consume()
