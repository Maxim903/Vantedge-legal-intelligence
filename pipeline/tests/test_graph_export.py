"""Tests for the BigQuery graph export."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.cloud import bigquery
from google.cloud.bigquery.table import RowIterator
from graph.export import (
    TABLE_MODELS,
    ArticleVersion,
    ExportBatch,
    iter_batches,
    iter_table_batches,
)
from pydantic import ValidationError

DATASET = bigquery.DatasetReference("test-project", "marts")


def test_all_graph_sources_are_exported_with_only_required_fields():
    samples = {
        "dim_code": dict(code_id="c", legifrance_id="lc", libelle="Code", ordre=1),
        "dim_livre": dict(
            livre_id="l", code_id="c", legifrance_id="ll", libelle="Livre", ordre=1
        ),
        "dim_titre": dict(
            titre_id="t", livre_id="l", legifrance_id="lt", libelle="Titre", ordre=1
        ),
        "dim_chapitre": dict(chapitre_id="ch", titre_id="t"),
        "dim_article": dict(article_id="a", chapitre_id="ch", numero="1"),
        "dim_article_version": dict(
            article_version_id="v",
            article_id="a",
            date_debut=date(2020, 1, 1),
            date_fin=None,
            etat="VIGUEUR",
            texte_ref="bq-reference",
        ),
        "dim_notion": dict(
            notion_id="n", libelle="Notion", definition_courte=None, score_confiance=0.9
        ),
        "dim_situation_vie": dict(situation_id="s", libelle="Situation"),
        "dim_requete": dict(
            requete_id="q", texte="Requête", pays_langue_id="pl", intention_type=None
        ),
        "dim_intention": {"type": "informationnelle"},
        "dim_pays_langue": dict(pays_langue_id="pl", pays="FR", langue="fr"),
        "fait_extraction": dict(
            extraction_id="e", article_version_id="v", notion_id="n"
        ),
        "fait_notion_requete": dict(
            notion_id="n", requete_id="q", score_rattachement=0.7
        ),
        "fait_metrique_mensuelle": dict(
            requete_id="q",
            pays_langue_id="pl",
            mois=date(2025, 1, 1),
            volume=10,
            cpc=None,
            concurrence=0.1,
        ),
        "fait_resultat_serp": dict(
            requete_id="q",
            pays_langue_id="pl",
            date_resultat=date(2025, 1, 2),
            position=1,
            domaine="example.org",
            url="https://example.org",
        ),
        "pont_article_renvoi": dict(
            article_source_id="a", type_relation="RENVOIE_A", article_cible_id="b"
        ),
        "pont_notion_situation": dict(notion_id="n", situation_id="s"),
    }
    client = Mock(spec=bigquery.Client)

    def get_table(reference):
        names = samples[reference.table_id]
        schema = [bigquery.SchemaField(name, "STRING") for name in names]
        schema.append(bigquery.SchemaField("unused", "STRING"))
        return SimpleNamespace(name=reference.table_id, schema=schema)

    def list_rows(table, *, selected_fields, page_size, page_token):
        assert page_size == 5
        assert page_token is None
        assert [field.name for field in selected_fields] == list(samples[table.name])
        return SimpleNamespace(
            pages=iter([[samples[table.name]]]), next_page_token=None
        )

    client.get_table.side_effect = get_table
    client.list_rows.side_effect = list_rows
    batches = list(iter_batches(client, DATASET, batch_size=5))

    assert {batch.table for batch in batches} == set(samples) == set(TABLE_MODELS)
    for batch in batches:
        assert isinstance(batch, ExportBatch)
        assert isinstance(batch.rows[0], TABLE_MODELS[batch.table])
        assert batch.model_dump()["rows"] == [samples[batch.table]]


def test_native_cursor_paginates_and_can_resume():
    continuation = "page-2"
    schema = [
        bigquery.SchemaField("article_version_id", "STRING"),
        bigquery.SchemaField("article_id", "STRING"),
        bigquery.SchemaField("date_debut", "DATE"),
        bigquery.SchemaField("date_fin", "DATE"),
        bigquery.SchemaField("etat", "STRING"),
        bigquery.SchemaField("texte_ref", "STRING"),
    ]
    client = Mock(spec=bigquery.Client)
    client.get_table.return_value = SimpleNamespace(schema=schema)
    requests = []

    def api_request(**kwargs):
        params = kwargs["query_params"]
        requests.append(params.copy())
        token = params.get("pageToken")
        versions = ["v1", "v2"] if token is None else ["v3"]
        result = {
            "rows": [
                {
                    "f": [
                        {"v": value}
                        for value in (v, "a", "2020-01-01", None, "VIGUEUR", None)
                    ]
                }
                for v in versions
            ],
            "totalRows": "3",
        }
        if token is None:
            result["pageToken"] = continuation
        return result

    def list_rows(table, *, selected_fields, page_size, page_token):
        return RowIterator(
            client=client,
            api_request=api_request,
            path="/test",
            schema=selected_fields,
            page_size=page_size,
            page_token=page_token,
        )

    client.list_rows.side_effect = list_rows
    batches = list(
        iter_table_batches(client, DATASET, "dim_article_version", batch_size=2)
    )
    assert [len(batch.rows) for batch in batches] == [2, 1]
    assert [batch.next_page_token for batch in batches] == [continuation, None]
    assert [
        row.article_version_id
        for batch in batches
        for row in batch.rows
        if isinstance(row, ArticleVersion)
    ] == ["v1", "v2", "v3"]
    assert batches[0].rows[0].model_dump()["date_debut"] == date(2020, 1, 1)
    assert requests[0]["maxResults"] == 2
    assert requests[1]["pageToken"] == continuation

    resumed = list(
        iter_table_batches(
            client,
            DATASET,
            "dim_article_version",
            batch_size=2,
            page_token=continuation,
        )
    )
    assert resumed[0].rows[0].model_dump()["article_version_id"] == "v3"
    assert client.list_rows.call_args.kwargs["page_token"] == continuation


def test_errors_are_not_silenced():
    client = Mock(spec=bigquery.Client)
    with pytest.raises(ValueError, match="batch_size"):
        list(iter_batches(client, DATASET, batch_size=0))
    with pytest.raises(ValueError, match="Unsupported"):
        list(iter_table_batches(client, DATASET, "autre"))
    with pytest.raises(ValueError, match="page_token"):
        list(iter_table_batches(client, DATASET, "dim_article", page_token=""))
    client.get_table.return_value = SimpleNamespace(schema=[])
    with pytest.raises(ValueError, match="Missing columns"):
        list(iter_table_batches(client, DATASET, "dim_article"))
    client.list_rows.assert_not_called()

    client.get_table.side_effect = RuntimeError("BigQuery unavailable")
    with pytest.raises(RuntimeError, match="BigQuery unavailable"):
        list(iter_table_batches(client, DATASET, "dim_article"))


def test_invalid_row_fails_instead_of_emitting_a_partial_batch():
    client = Mock(spec=bigquery.Client)
    client.get_table.return_value = SimpleNamespace(
        schema=[
            bigquery.SchemaField(name, "STRING")
            for name in TABLE_MODELS["dim_article"].model_fields
        ]
    )
    client.list_rows.return_value = SimpleNamespace(
        pages=iter(
            [
                [
                    {"article_id": "a", "chapitre_id": None, "numero": "1"},
                    {"article_id": "b", "chapitre_id": None, "numero": None},
                ]
            ]
        ),
        next_page_token=None,
    )
    batches = iter_table_batches(client, DATASET, "dim_article")
    with pytest.raises(ValidationError):
        next(batches)


def test_empty_table_emits_no_batch():
    client = Mock(spec=bigquery.Client)
    client.get_table.return_value = SimpleNamespace(
        schema=[
            bigquery.SchemaField(name, "STRING")
            for name in TABLE_MODELS["dim_article"].model_fields
        ]
    )
    client.list_rows.return_value = SimpleNamespace(
        pages=iter([[]]), next_page_token=None
    )
    assert list(iter_table_batches(client, DATASET, "dim_article")) == []
