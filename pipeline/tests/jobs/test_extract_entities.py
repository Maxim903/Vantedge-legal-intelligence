"""Extraction job tests with local BigQuery and LLM doubles."""

import json
from decimal import Decimal
from unittest.mock import Mock

import pytest

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.clients.llm import FakeLLMClient, LLMResponse
from vil_pipeline.errors import ApiBudgetExceeded
from vil_pipeline.jobs.extract_entities import extract_entities

MODEL = "fake-model"
ID1 = "LEGIARTI000006901674"
ID2 = "LEGIARTI000006901793"
TEXT = "Tout salarié a droit à un congé payé."


def response(article_id=ID1, notions=None, model=MODEL):
	return LLMResponse(
		json.dumps({"article_version_id": article_id, "notions": notions or []}),
		model, 5, 6,
	)


def notion(situations=None):
	return {
		"libelle": "Congé payé",
		"definition_courte": "Un congé payé.",
		"situations_de_vie": situations or [],
		"confiance": 0.9,
		"citation_article": "congé payé",
	}


class FakeStore:
	def __init__(self, rows):
		self.rows = rows
		self.results = {}
		self.starts = []
		self.runs = []
		self.saved_entities = []

	def query(self, sql, parameters):
		values = {item.name: item.value for item in parameters}
		if "WITH versions AS" in sql:
			key = (values["version_prompt"], values["model"])
			return [
				row for row in self.rows
				if row["article_version_id"] > values["last_id"]
				and (row["article_version_id"], *key) not in self.results
			][:values["batch_size"]]
		if "BEGIN TRANSACTION" in sql:
			key = (values["article_id"], values["version_prompt"], values["model"])
			if key not in self.results:
				self.results[key] = values
				self.saved_entities.extend(json.loads(values["entities"]))
			return []
		if "INSERT INTO `ops.pipeline_runs`" in sql:
			self.starts.append(values)
			return []
		if "UPDATE `ops.pipeline_runs`" in sql:
			self.runs.append(values)
			return []
		raise AssertionError("Unexpected SQL")


def store(*ids):
	fake = FakeStore([{"article_version_id": id_, "texte": TEXT} for id_ in ids])
	bq = Mock(spec=BigQueryClient)
	bq.query.side_effect = fake.query
	return fake, bq


def run(bq, llm, **kwargs):
	options = {
		"prompt": "Extrait les notions",
		"version_prompt": "version-1",
		"model": MODEL,
		"max_cost": Decimal("1.00"),
		"cost_per_call": Decimal("0.10"),
		"batch_size": 1,
	}
	options.update(kwargs)
	return extract_entities(bq, llm, **options)


def test_extract_batches_saves_entities_empty_results_and_skips_on_rerun():
	fake, bq = store(ID1, ID2)
	llm = FakeLLMClient([
		response(ID1, [notion(["situation 1", "situation 2"]), notion()]),
		response(ID2),
	])
	stats = run(bq, llm)

	assert (stats.read, stats.processed, stats.entities, stats.calls) == (2, 2, 3, 2)
	assert stats.estimated_cost == Decimal("0.20")
	assert [row["situation_de_vie"] for row in fake.saved_entities] == [
		"situation 1", "situation 2", None,
	]
	assert len(fake.results) == 2
	assert fake.results[(ID2, "version-1", MODEL)]["status"] == "SUCCESS"
	assert ID1 in llm.calls[0][1]
	assert len(fake.starts) == len(fake.runs) == 1
	assert fake.starts[0]["run_id"] == fake.runs[0]["run_id"] == stats.run_id
	assert fake.runs[0]["status"] == "SUCCESS"
	assert json.loads(fake.runs[0]["counts"])["entities"] == 3
	assert run(bq, FakeLLMClient([])).read == 0
	assert len(fake.saved_entities) == 3


def test_new_prompt_and_model_are_independent_keys():
	fake, bq = store(ID1)
	run(bq, FakeLLMClient([response()]))
	run(bq, FakeLLMClient([response()]), version_prompt="version-2")
	run(bq, FakeLLMClient([response(model="other")]), model="other")
	assert len(fake.results) == 3


def test_budget_stops_before_next_article_and_logs_status():
	fake, bq = store(ID1, ID2)
	llm = FakeLLMClient([response(ID1), response(ID2)])
	stats = run(bq, llm, max_cost=Decimal("0.10"))
	assert stats.status == "BUDGET_EXHAUSTED"
	assert stats.estimated_cost == Decimal("0.10")
	assert len(llm.calls) == 1
	assert len(fake.results) == 1
	assert fake.runs[0]["status"] == "BUDGET_EXHAUSTED"
	assert fake.runs[0]["error"] == "ApiBudgetExceeded"
	assert json.loads(fake.runs[0]["counts"])["read"] == 2


def test_budget_applies_before_validation_retry():
	fake, bq = store(ID1)
	llm = FakeLLMClient([LLMResponse("broken", MODEL, 1, 1), response()])
	stats = run(bq, llm, max_cost=Decimal("0.10"))
	assert stats.status == "BUDGET_EXHAUSTED"
	assert len(llm.calls) == 1
	assert not fake.results


def test_budget_exception_does_not_log_its_message():
	fake, bq = store(ID1)

	def fail_on_read(sql, parameters):
		if "WITH versions AS" in sql:
			raise ApiBudgetExceeded("private@example.invalid")
		return fake.query(sql, parameters)

	bq.query.side_effect = fail_on_read
	stats = run(bq, FakeLLMClient([]))
	assert stats.status == "BUDGET_EXHAUSTED"
	assert fake.runs[0]["error"] == "ApiBudgetExceeded"


def test_invalid_wrong_id_and_citation_retry_then_quarantine():
	fake, bq = store(ID1)
	wrong_citation = {**notion(), "citation_article": "absent"}
	llm = FakeLLMClient([
		response(ID2), response(ID1, [wrong_citation]),
		LLMResponse("broken", MODEL, 1, 1),
	])
	stats = run(bq, llm)
	assert (stats.calls, stats.quarantined, stats.entities) == (3, 1, 0)
	saved = fake.results[(ID1, "version-1", MODEL)]
	assert saved["status"] == "QUARANTINE"
	assert saved["raw_json"] == "broken"
	assert "JSON invalide" in saved["reason"]
	assert run(bq, FakeLLMClient([])).read == 0


def test_invalid_then_valid_result_is_saved():
	fake, bq = store(ID1)
	llm = FakeLLMClient([response(ID2), response(ID1, [notion()])])
	stats = run(bq, llm)
	assert stats.calls == 2
	assert stats.processed == 1
	assert fake.results[(ID1, "version-1", MODEL)]["status"] == "SUCCESS"


def test_dry_run_counts_all_articles_without_llm_or_extraction_writes():
	fake, bq = store(ID1, ID2)
	llm = FakeLLMClient([])
	stats = run(bq, llm, dry_run=True, max_cost=Decimal("0.10"))
	assert stats.status == "DRY_RUN_OVER_BUDGET"
	assert (stats.read, stats.calls, stats.estimated_cost) == (2, 0, Decimal("0.20"))
	assert not llm.calls
	assert not fake.results
	assert len(fake.runs) == 1
	assert fake.runs[0]["cost"] == Decimal("0.20")


def test_failure_is_journaled_and_propagated():
	fake, bq = store(ID1)
	llm = FakeLLMClient([response(model="unexpected")])
	with pytest.raises(ValueError, match="modèle"):
		run(bq, llm)
	assert fake.runs[0]["status"] == "FAILED"
	assert "ValueError" in fake.runs[0]["error"]
	assert fake.runs[0]["cost"] == Decimal("0.10")
	assert json.loads(fake.runs[0]["counts"])["calls"] == 1
	assert not fake.results


def test_write_failure_is_journaled_and_propagated():
	fake, bq = store(ID1)

	def fail_on_save(sql, parameters):
		if "BEGIN TRANSACTION" in sql:
			raise RuntimeError("write failed")
		return fake.query(sql, parameters)

	bq.query.side_effect = fail_on_save
	with pytest.raises(RuntimeError, match="write failed"):
		run(bq, FakeLLMClient([response()]))
	assert fake.runs[0]["status"] == "FAILED"
	assert fake.runs[0]["error"] == "RuntimeError"
	assert json.loads(fake.runs[0]["counts"])["processed"] == 0


@pytest.mark.parametrize(
	"kwargs",
	[
		{"batch_size": 0},
		{"cost_per_call": Decimal("0")},
		{"cost_per_call": Decimal("NaN")},
		{"cost_per_call": Decimal("0.0000000001")},
		{"max_cost": Decimal("-1")},
		{"model": ""},
	],
)
def test_rejects_invalid_configuration(kwargs):
	fake, bq = store(ID1)
	with pytest.raises(ValueError):
		run(bq, FakeLLMClient([]), **kwargs)
	assert len(fake.starts) == len(fake.runs) == 1
	assert fake.runs[0]["status"] == "FAILED"
	assert "ValueError" in fake.runs[0]["error"]
	assert bq.query.call_count == 2


def test_selection_queries_active_versions_and_binds_key_and_paging():
	_, bq = store()
	run(bq, FakeLLMClient([]))
	sql, params = bq.query.call_args_list[1].args
	assert "v.etat = 'VIGUEUR'" in sql
	assert "v.date_debut <= CURRENT_DATE()" in sql
	assert "v.date_fin >= CURRENT_DATE()" in sql
	assert "done.version_prompt = @version_prompt" in sql
	assert "done.modele_llm = @model" in sql
	assert "FROM `raw.entites_extraites` AS extracted" in sql
	assert {p.name: p.value for p in params} == {
		"last_id": "", "version_prompt": "version-1", "model": MODEL, "batch_size": 1,
	}
