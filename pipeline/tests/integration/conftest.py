"""Connexion opt-in à l'instance Neo4j de test."""

import os
from collections.abc import Iterator

import pytest
from neo4j import Driver, GraphDatabase


@pytest.fixture
def neo4j_driver() -> Iterator[Driver]:
    uri = os.environ.get("NEO4J_TEST_URI")
    if uri is None:
        pytest.skip("NEO4J_TEST_URI n'est pas défini")
    if not uri.strip():
        pytest.fail("NEO4J_TEST_URI ne doit pas être vide")
    with GraphDatabase.driver(uri, auth=None, connection_timeout=5) as driver:
        driver.verify_connectivity()
        yield driver
