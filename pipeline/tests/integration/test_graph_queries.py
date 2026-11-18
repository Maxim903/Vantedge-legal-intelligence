"""Execute the graph queries against a small isolated Neo4j subgraph."""

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from neo4j import Driver, Session

QUERY_DIR = Path(__file__).resolve().parents[3] / "graph" / "queries"


@pytest.fixture
def mini_graph(neo4j_driver: Driver) -> Iterator[tuple[Session, str]]:
    prefix = "queries-" + uuid4().hex + "-"
    with neo4j_driver.session() as session:
        try:
            session.run(
                """
CREATE (n1:Notion {notion_id: $p + 'n1', libelle: 'Notion 1', _test_run: $p}),
       (n2:Notion {notion_id: $p + 'n2', libelle: 'Notion 2', _test_run: $p}),
       (n3:Notion {notion_id: $p + 'n3', libelle: 'Notion 3', _test_run: $p}),
       (n4:Notion {notion_id: $p + 'n4', libelle: 'Isolée', _test_run: $p}),
       (a1:Article {article_id: $p + 'a1', numero: '1', _test_run: $p}),
       (a2:Article {article_id: $p + 'a2', numero: '2', _test_run: $p}),
       (a3:Article {article_id: $p + 'a3', numero: '3', _test_run: $p}),
       (a4:Article {article_id: $p + 'a4', numero: '4', _test_run: $p}),
       (a5:Article {article_id: $p + 'a5', numero: '5', _test_run: $p}),
       (a6:Article {article_id: $p + 'a6', numero: '6', _test_run: $p}),
       (s1:SituationDeVie {situation_id: $p + 's1',
                           libelle: 'Situation 1', _test_run: $p}),
       (s2:SituationDeVie {situation_id: $p + 's2',
                           libelle: 'Situation 2', _test_run: $p}),
       (s3:SituationDeVie {situation_id: $p + 's3', libelle: 'Vide', _test_run: $p}),
       (q:Requete {requete_id: $p + 'q', _test_run: $p}),
       (x:TestNode {_test_run: $p})
CREATE (n1)-[:SE_FONDE_SUR]->(a1), (n1)-[:SE_FONDE_SUR]->(a2),
       (n2)-[:SE_FONDE_SUR]->(a1), (n2)-[:SE_FONDE_SUR]->(a1),
       (n2)-[:SE_FONDE_SUR]->(a2), (n3)-[:SE_FONDE_SUR]->(a1),
       (n1)-[:APPARTIENT_A]->(s1), (n1)-[:APPARTIENT_A]->(s2),
       (n2)-[:APPARTIENT_A]->(s1), (n3)-[:APPARTIENT_A]->(s2),
       (n3)-[:APPARTIENT_A]->(s2),
       (n2)-[:EST_EXPRIMEE_PAR]->(q), (x)-[:LIEN_TEST]->(n3),
       (n3)-[:BOUCLE_TEST]->(n3),
       (a1)-[:RENVOIE_A]->(a3), (a3)-[:MODIFIE]->(a4),
       (a3)-[:ABROGE]->(a2), (a4)-[:ABROGE]->(a1),
       (a4)-[:RENVOIE_A]->(a5), (a5)-[:RENVOIE_A]->(a6),
       (a3)-[:RENVOIE_A]->(x), (x)-[:RENVOIE_A]->(a5)
""",
                p=prefix,
            ).consume()
            yield session, prefix
        finally:
            session.run(
                "MATCH (n) WHERE n._test_run = $p DETACH DELETE n", p=prefix
            ).consume()


def _query(name: str) -> str:
    return (QUERY_DIR / name).read_text(encoding="utf-8")


def test_notions_voisines_by_distinct_common_articles(mini_graph):
    session, prefix = mini_graph
    sql = _query("notions_voisines.cypher")
    rows = [record.data() for record in session.run(sql, notion_id=prefix + "n1")]
    assert [(row["notion_id"], row["nombre_articles_communs"]) for row in rows] == [
        (prefix + "n2", 2),
        (prefix + "n3", 1),
    ]
    assert rows[0]["articles_communs"] == [
        {"article_id": prefix + "a1", "numero": "1"},
        {"article_id": prefix + "a2", "numero": "2"},
    ]
    assert list(session.run(sql, notion_id=prefix + "n4")) == []
    assert list(session.run(sql, notion_id=prefix + "inconnue")) == []


def test_notions_connectees_count_all_incident_relations(mini_graph):
    session, prefix = mini_graph
    sql = _query("notions_connectees.cypher")
    rows = [record.data() for record in session.run(sql, limite=1000000)]
    local = [row for row in rows if row["notion_id"].startswith(prefix)]
    assert [(row["notion_id"], row["degre"]) for row in local] == [
        (prefix + "n2", 5),
        (prefix + "n3", 5),
        (prefix + "n1", 4),
        (prefix + "n4", 0),
    ]
    assert [record.data() for record in session.run(sql, limite=1)] == rows[:1]
    assert list(session.run(sql, limite=0)) == []


def test_chemins_include_all_simple_paths_up_to_three_links(mini_graph):
    session, prefix = mini_graph
    sql = _query("chemins_notion_articles.cypher")
    rows = list(session.run(sql, notion_id=prefix + "n1"))
    assert [(row["article_id"], row["nombre_liens_normatifs"]) for row in rows] == [
        (prefix + "a1", 0),
        (prefix + "a2", 0),
        (prefix + "a3", 1),
        (prefix + "a2", 2),
        (prefix + "a4", 2),
        (prefix + "a5", 3),
    ]
    path = rows[-1]["chemin"]
    assert [relation.type for relation in path.relationships] == [
        "SE_FONDE_SUR",
        "RENVOIE_A",
        "MODIFIE",
        "RENVOIE_A",
    ]
    assert [node.get("article_id") for node in path.nodes[1:]] == [
        prefix + "a1",
        prefix + "a3",
        prefix + "a4",
        prefix + "a5",
    ]
    for row in rows:
        node_ids = [node.element_id for node in row["chemin"].nodes]
        assert len(node_ids) == len(set(node_ids))
    assert list(session.run(sql, notion_id=prefix + "n4")) == []


def test_clusters_group_notions_by_situation(mini_graph):
    session, prefix = mini_graph
    sql = _query("clusters_situations.cypher")
    rows = [
        record.data()
        for record in session.run(sql)
        if record["situation_id"].startswith(prefix)
    ]
    assert [(row["situation_id"], row["nombre_notions"]) for row in rows] == [
        (prefix + "s1", 2),
        (prefix + "s2", 2),
    ]
    assert [notion["notion_id"] for notion in rows[0]["notions"]] == [
        prefix + "n1",
        prefix + "n2",
    ]
    assert [notion["notion_id"] for notion in rows[1]["notions"]] == [
        prefix + "n1",
        prefix + "n3",
    ]
