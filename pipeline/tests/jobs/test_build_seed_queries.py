"""Tests for deterministic seed-query generation from validated notions."""

from unittest.mock import Mock

from google.cloud import bigquery

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.jobs.build_seed_queries import (
	build_seed_queries,
	generate_seed_queries,
)


def test_generate_queries_normalizes_and_deduplicates_by_notion_and_query():
	rows = [
		{
			"notion_libelle": "Congés payés",
			"situation_de_vie": "Prendre un congé",
		},
		{
			"notion_libelle": " CONGÉS   PAYÉS ",
			"situation_de_vie": "Prendre un congé",
		},
	]

	queries = generate_seed_queries(rows)

	assert len(queries) == 3
	assert [query["requete"] for query in queries] == [
		"congés payés",
		"congé payé",
		"congés payés prendre un congé",
	]
	assert [query["score_rattachement"] for query in queries] == [1.0, 0.7, 0.8]
	assert len({query["notion_id"] for query in queries}) == 1


def test_build_seed_queries_reads_only_validated_entities_and_writes_rows():
	client = Mock(spec=BigQueryClient)
	client.query.return_value = [
		{"notion_libelle": "Droits du salarié", "situation_de_vie": None}
	]

	count = build_seed_queries(client)

	assert count == 2
	sql = client.query.call_args.args[0]
	assert "FROM `raw.entites_extraites`" in sql
	assert "statut_validation = 'VALIDE'" in sql
	client.insert.assert_called_once()
	args, kwargs = client.insert.call_args
	assert args[0] == "raw.requetes_candidates"
	assert len(args[1]) == 2
	assert kwargs["write_disposition"] == bigquery.WriteDisposition.WRITE_TRUNCATE
	assert {row["requete"] for row in args[1]} == {
		"droits du salarié",
		"droit du salarié",
	}


def test_empty_validated_notion_set_does_not_load_table():
	client = Mock(spec=BigQueryClient)
	client.query.return_value = []

	assert build_seed_queries(client) == 0
	client.insert.assert_not_called()