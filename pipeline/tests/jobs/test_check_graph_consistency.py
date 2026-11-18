"""Tests for the marts/Neo4j count comparison."""

import sqlite3
from unittest.mock import MagicMock, Mock

import pytest
from google.cloud import bigquery
from neo4j import Driver

from vil_pipeline.jobs.check_graph_consistency import (
    CountDifference,
    _marts_counts,
    check_graph_consistency,
)

DATASET = bigquery.DatasetReference("test-project", "marts")


@pytest.fixture
def sources():
    marts = {
        "Notion": 2,
        "Article": 1,
        "Requete": 1,
        "CONTIENT (Code->Livre)": 0,
        "CONTIENT (Livre->Titre)": 0,
        "CONTIENT (Titre->Article)": 0,
        "SE_FONDE_SUR": 1,
        "APPARTIENT_A": 0,
        "EST_EXPRIMEE_PAR": 1,
        "A_POUR_INTENTION": 0,
        "A_POUR_METRIQUE": 0,
        "A_POUR_RESULTAT": 0,
        "RENVOIE_A": 0,
        "MODIFIE": 0,
        "ABROGE": 0,
        "invalid_chapitre": 0,
        "invalid_version": 0,
        "invalid_metrique_contexte": 0,
        "invalid_serp_contexte": 0,
        "invalid_renvoi": 0,
    }
    nodes = {"notions": 2, "articles": 1, "requetes": 1}
    relations = [
        {
            "type": "SE_FONDE_SUR",
            "source": ["Notion"],
            "cible": ["Article"],
            "total": 1,
        },
        {
            "type": "EST_EXPRIMEE_PAR",
            "source": ["Notion"],
            "cible": ["Requete"],
            "total": 1,
        },
    ]
    client = Mock(spec=bigquery.Client)
    driver = MagicMock(spec=Driver)
    session = driver.session.return_value.__enter__.return_value

    def query(*args, **kwargs):
        return Mock(
            result=Mock(
                return_value=[
                    {"categorie": category, "total": count}
                    for category, count in marts.items()
                ]
            )
        )

    def read(callback):
        transaction = Mock()
        transaction.run.side_effect = [Mock(single=Mock(return_value=nodes)), relations]
        return callback(transaction)

    client.query.side_effect = query
    session.execute_read.side_effect = read
    return client, driver, marts, nodes, relations


def test_equal_counts_and_dataset_configuration(sources):
    client, driver, _, _, _ = sources
    assert check_graph_consistency(client, driver, DATASET, database="neo4j") == []
    assert (
        client.query.call_args_list[1].kwargs["job_config"].default_dataset == DATASET
    )
    driver.session.assert_called_once_with(database="neo4j")


def test_reports_all_differences_including_wrong_relation_endpoints(sources):
    client, driver, _, nodes, relations = sources
    nodes["notions"] = 3
    relations[0]["total"] = 2
    relations.append(
        {
            "type": "CONTIENT",
            "source": ["Article"],
            "cible": ["Titre"],
            "total": 1,
        }
    )
    differences = check_graph_consistency(client, driver, DATASET)
    assert differences == [
        CountDifference("Notion", 2, 3),
        CountDifference("Relation inattendue CONTIENT (Article->Titre)", 0, 1),
        CountDifference("SE_FONDE_SUR", 1, 2),
    ]


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("invalid_version", "version d'article introuvable"),
        ("invalid_chapitre", "chapitre introuvable"),
        ("invalid_metrique_contexte", "contexte invalide"),
        ("invalid_serp_contexte", "contexte invalide"),
        ("invalid_renvoi", "type invalide"),
    ],
)
def test_invalid_marts_are_reported_before_reading_the_graph(sources, name, message):
    client, driver, marts, _, _ = sources
    marts[name] = 1
    with pytest.raises(ValueError, match=message):
        check_graph_consistency(client, driver, DATASET)
    driver.session.assert_not_called()


def test_missing_or_invalid_counts_and_service_errors_are_not_silenced(sources):
    client, driver, marts, _, _ = sources
    del marts["Article"]
    with pytest.raises(ValueError, match="Article"):
        check_graph_consistency(client, driver, DATASET)
    marts["Article"] = None
    with pytest.raises(ValueError, match="Compte invalide"):
        check_graph_consistency(client, driver, DATASET)
    client.query.side_effect = RuntimeError("BigQuery indisponible")
    with pytest.raises(RuntimeError, match="BigQuery indisponible"):
        check_graph_consistency(client, driver, DATASET)


def test_marts_query_counts_relationship_grains_and_optional_links():
    with sqlite3.connect(":memory:") as db:
        db.row_factory = sqlite3.Row
        db.executescript("""
CREATE TABLE dim_notion (notion_id TEXT);
CREATE TABLE dim_article (article_id TEXT, chapitre_id TEXT);
CREATE TABLE dim_requete (requete_id TEXT, pays_langue_id TEXT, intention_type TEXT);
CREATE TABLE dim_livre (code_id TEXT, livre_id TEXT);
CREATE TABLE dim_titre (livre_id TEXT, titre_id TEXT);
CREATE TABLE dim_chapitre (chapitre_id TEXT, titre_id TEXT);
CREATE TABLE dim_article_version (article_version_id TEXT, article_id TEXT);
CREATE TABLE fait_extraction (notion_id TEXT, article_version_id TEXT);
CREATE TABLE pont_notion_situation (notion_id TEXT, situation_id TEXT);
CREATE TABLE fait_notion_requete (notion_id TEXT, requete_id TEXT);
CREATE TABLE fait_metrique_mensuelle (requete_id TEXT, pays_langue_id TEXT, mois TEXT);
CREATE TABLE fait_resultat_serp (
  requete_id TEXT, pays_langue_id TEXT, date_resultat TEXT, position INTEGER
);
CREATE TABLE pont_article_renvoi (
  article_source_id TEXT, article_cible_id TEXT, type_relation TEXT
);
INSERT INTO dim_notion VALUES ('n');
INSERT INTO dim_article VALUES ('a1', 'ch'), ('a2', NULL);
INSERT INTO dim_requete VALUES ('q1', 'fr', 'informationnelle'), ('q2', 'fr', NULL);
INSERT INTO dim_livre VALUES ('c', 'l');
INSERT INTO dim_titre VALUES ('l', 't');
INSERT INTO dim_chapitre VALUES ('ch', 't');
INSERT INTO dim_article_version VALUES ('v1', 'a1'), ('v2', 'a1');
INSERT INTO fait_extraction VALUES ('n', 'v1'), ('n', 'v1'), ('n', 'v2');
INSERT INTO pont_notion_situation VALUES ('n', 's'), ('n', 's');
INSERT INTO fait_notion_requete VALUES ('n', 'q1'), ('n', 'q1');
INSERT INTO fait_metrique_mensuelle VALUES
  ('q1', 'fr', '2025-01-01'), ('q1', 'fr', '2025-01-01'), ('q1', 'fr', '2025-02-01');
INSERT INTO fait_resultat_serp VALUES
  ('q1', 'fr', '2025-01-02', 1), ('q1', 'fr', '2025-01-02', 1);
INSERT INTO pont_article_renvoi VALUES
  ('a1', 'a2', 'RENVOIE_A'), ('a1', 'a2', 'RENVOIE_A'), ('a1', 'a2', 'ABROGE');
""")
        client = Mock(spec=bigquery.Client)
        client.query.side_effect = lambda sql, **kwargs: Mock(
            result=Mock(return_value=list(db.execute(sql)))
        )
        counts = _marts_counts(client, DATASET)
        assert counts == {
            "Notion": 1,
            "Article": 2,
            "Requete": 2,
            "CONTIENT (Code->Livre)": 1,
            "CONTIENT (Livre->Titre)": 1,
            "CONTIENT (Titre->Article)": 1,
            "SE_FONDE_SUR": 1,
            "APPARTIENT_A": 1,
            "EST_EXPRIMEE_PAR": 1,
            "A_POUR_INTENTION": 1,
            "A_POUR_METRIQUE": 2,
            "A_POUR_RESULTAT": 1,
            "RENVOIE_A": 1,
            "MODIFIE": 0,
            "ABROGE": 1,
        }

        db.execute("INSERT INTO fait_extraction VALUES ('n', 'missing-version')")
        with pytest.raises(ValueError, match="version d'article introuvable"):
            _marts_counts(client, DATASET)
