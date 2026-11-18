"""Intent collection and classification tests with BigQuery doubles."""

import json
from unittest.mock import Mock

import pytest
from google.cloud import bigquery
from google.cloud.bigquery import QueryJob

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.jobs.collect_intent import (
	INTENT_COMMERCIALE,
	INTENT_INFORMATIONNELLE,
	INTENT_NAVIGATIONNELLE,
	INTENT_TRANSACTIONNELLE,
	classify_intent,
	classify_queries,
	collect_intent,
)


@pytest.mark.parametrize(
	("query", "expected_intent"),
	[
		("avocat droit du travail", INTENT_TRANSACTIONNELLE),
		("cabinet juriste licenciement", INTENT_TRANSACTIONNELLE),
		("modèle lettre de démission", INTENT_TRANSACTIONNELLE),
		("formulaire cerfa prud'hommes", INTENT_TRANSACTIONNELLE),
		("saisir le cph", INTENT_TRANSACTIONNELLE),
		("comparatif logiciel de paie", INTENT_COMMERCIALE),
		("meilleure solution rh", INTENT_COMMERCIALE),
		("tarif cabinet conseil", INTENT_COMMERCIALE),
		("prix abonnement juridique", INTENT_COMMERCIALE),
		("legifrance code du travail", INTENT_NAVIGATIONNELLE),
		("connexion service public", INTENT_NAVIGATIONNELLE),
		("site officiel urssaf", INTENT_NAVIGATIONNELLE),
		("comment calculer préavis démission", INTENT_INFORMATIONNELLE),
		("définition faute grave", INTENT_INFORMATIONNELLE),
		("durée période d'essai", INTENT_INFORMATIONNELLE),
		("congés payés", INTENT_INFORMATIONNELLE),
		("forfait jours cadre", INTENT_INFORMATIONNELLE),
	],
)
def test_classify_intent_assigns_canonical_intent(query, expected_intent):
	result = classify_intent(query)
	assert result.intention_type == expected_intent
	assert result.requete == query
	assert 0 < result.score_confiance <= 1.0


def test_classify_intent_precedence_transactional_over_informational():
	# Query contains "comment calculer" (info) and "avocat" (transac)
	result = classify_intent("comment trouver un avocat pour calculer mon préavis")
	assert result.intention_type == INTENT_TRANSACTIONNELLE


def test_classify_queries_deduplicates_case_and_accents():
	queries = [
		"Avocat Droit Du Travail",
		"  avocat droit du travail  ",
		"durée du travail",
	]
	results = classify_queries(queries)
	assert len(results) == 2
	assert [r.requete for r in results] == [
		"Avocat Droit Du Travail",
		"durée du travail",
	]


def test_collect_intent_writes_classified_rows_and_journals_run():
	bq = Mock(spec=BigQueryClient)
	bq.query.side_effect = [
		[],
		[
			{"requete": "avocat prud'hommes"},
			{"requete": "comparatif logiciel rh"},
			{"requete": "congés payés"},
		],
		[],
	]

	stats = collect_intent(bq)

	assert stats.status == "SUCCESS"
	assert stats.read == 3
	assert stats.classified == 3
	assert stats.distribution == {
		INTENT_TRANSACTIONNELLE: 1,
		INTENT_COMMERCIALE: 1,
		INTENT_INFORMATIONNELLE: 1,
	}

	bq.insert.assert_called_once()
	table_id, rows = bq.insert.call_args.args[:2]
	assert table_id == "raw.requetes_intentions"
	assert len(rows) == 3
	assert rows[0]["intention_type"] == INTENT_TRANSACTIONNELLE
	assert bq.insert.call_args.kwargs["write_disposition"] == (
		bigquery.WriteDisposition.WRITE_TRUNCATE
	)

	run_sql = bq.query.call_args_list[-1].args[0]
	assert "UPDATE `ops.pipeline_runs`" in run_sql
	start = bq.query.call_args_list[0]
	assert "INSERT INTO `ops.pipeline_runs`" in start.args[0]
	assert {p.name: p.value for p in start.args[1]}["job"] == "collect_intent"
	assert bq.query.call_count == 3
	run_params = bq.query.call_args_list[-1].args[1]
	counts_param = next(p for p in run_params if p.name == "counts")
	counts = json.loads(counts_param.value)
	assert counts["classified"] == 3
	assert counts["distribution"][INTENT_TRANSACTIONNELLE] == 1
	assert {p.name: p.value for p in start.args[1]}["run_id"] == stats.run_id
	assert {p.name: p.value for p in run_params}["run_id"] == stats.run_id


def test_collect_intent_dry_run_computes_distribution_without_insert():
	bq = Mock(spec=BigQueryClient)
	bq.query.side_effect = [
		[],
		[{"requete": "avocat"}, {"requete": "durée du travail"}],
		[],
	]

	stats = collect_intent(bq, dry_run=True)

	assert stats.status == "DRY_RUN"
	assert stats.classified == 2
	bq.insert.assert_not_called()
	assert "ops.pipeline_runs" in bq.query.call_args_list[-1].args[0]


def test_collect_intent_handles_empty_candidates():
	bq = Mock(spec=BigQueryClient)
	bq.query.side_effect = [[], [], []]

	stats = collect_intent(bq)

	assert stats.status == "NO_CANDIDATE_QUERIES"
	assert stats.read == 0
	assert stats.classified == 0
	bq.insert.assert_not_called()
	assert "ops.pipeline_runs" in bq.query.call_args_list[-1].args[0]


def test_collect_intent_rejects_dry_run_bigquery_client():
	bq = Mock(spec=BigQueryClient)
	bq.query.side_effect = [[], Mock(spec=QueryJob), []]

	with pytest.raises(ValueError, match="dry-run"):
		collect_intent(bq)


def test_failed_write_preserves_counts_and_error():
	bq = Mock(spec=BigQueryClient)
	bq.query.side_effect = [[], [{"requete": "avocat"}], []]
	bq.insert.side_effect = RuntimeError("write failed")

	with pytest.raises(RuntimeError, match="write failed"):
		collect_intent(bq)

	assert bq.query.call_count == 3
	params = {p.name: p.value for p in bq.query.call_args_list[-1].args[1]}
	assert params["status"] == "FAILED"
	assert params["error"] == "RuntimeError: write failed"
	assert json.loads(params["counts"])["classified"] == 1


def test_job_and_final_tracking_failures_are_both_preserved():
	bq = Mock(spec=BigQueryClient)
	bq.query.side_effect = [[], [{"requete": "avocat"}], RuntimeError("log failed")]
	bq.insert.side_effect = ValueError("write failed")

	with pytest.raises(ExceptionGroup) as raised:
		collect_intent(bq)
	assert [str(e) for e in raised.value.exceptions] == ["write failed", "log failed"]
