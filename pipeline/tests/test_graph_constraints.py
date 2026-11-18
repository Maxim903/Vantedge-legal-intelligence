"""Tests de validation du fichier de contraintes."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from neo4j import Driver

from vil_pipeline.graph.apply_constraints import apply_constraints


def test_invalid_constraints_are_rejected_before_any_write(tmp_path: Path) -> None:
    path = tmp_path / "constraints.cypher"
    path.write_text(
        "CREATE CONSTRAINT n IF NOT EXISTS FOR (n:Notion) "
        "REQUIRE n.notion_id IS UNIQUE;\n"
        "MATCH (n) DETACH DELETE n;\n",
        encoding="utf-8",
    )
    driver = MagicMock(spec=Driver)
    with pytest.raises(ValueError, match="line 2"):
        apply_constraints(driver, path)
    driver.session.assert_not_called()


def test_conflicting_constraint_name_is_not_silently_accepted(tmp_path: Path) -> None:
    path = tmp_path / "constraints.cypher"
    path.write_text(
        "CREATE CONSTRAINT n IF NOT EXISTS FOR (n:Notion) "
        "REQUIRE n.notion_id IS UNIQUE;\n",
        encoding="utf-8",
    )
    driver = MagicMock(spec=Driver)
    session = driver.session.return_value.__enter__.return_value
    session.run.return_value.__iter__.return_value = iter(
        [
            {
                "type": "NODE_PROPERTY_UNIQUENESS",
                "entityType": "NODE",
                "labelsOrTypes": ["Article"],
                "properties": ["article_id"],
            }
        ]
    )
    with pytest.raises(RuntimeError, match=r"Notion\.notion_id"):
        apply_constraints(driver, path)
