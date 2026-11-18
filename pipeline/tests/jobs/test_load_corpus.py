"""Tests for corpus loading filters."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.jobs.load_corpus import (
	DEFAULT_CODE_ID,
	is_in_scope,
	iter_corpus,
	load_corpus,
	main,
)
from vil_pipeline.models.corpus import Article

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures" / "legi"


def _article(*, code_id: str = DEFAULT_CODE_ID, livre: str = "Livre Ier : Généralités"):
	return Article(
		article_id="LEGIARTI000006901674",
		numero="L. 1",
		code_id=code_id,
		livre=livre,
		titre="Titre I",
		chapitre="Chapitre I",
	)


def test_filter_keeps_only_configured_code_and_livre():
	assert is_in_scope(_article(), livre="I") is True
	assert is_in_scope(_article(livre="Livre II : Contrat"), livre="I") is False
	assert is_in_scope(_article(code_id="LEGITEXT000006071367"), livre="I") is False


def test_filter_accepts_livre_ordinal_and_full_label():
	assert is_in_scope(_article(), livre="Livre Ier") is True
	assert is_in_scope(_article(), livre="I") is True


def test_iter_corpus_filters_fixture_files_by_configured_livre():
	results = list(iter_corpus(FIXTURES_DIR, livre="II"))

	assert [article.article_id for article, _ in results] == [
		"LEGIARTI000006901793",
		"LEGIARTI000006901674",
	]
	assert all(article.code_id == DEFAULT_CODE_ID for article, _ in results)


def test_iter_corpus_uses_livre_i_by_default():
	assert list(iter_corpus(FIXTURES_DIR)) == []


def test_main_exposes_configurable_livre_parameter(tmp_path, monkeypatch, capsys):
	source = tmp_path / "article.xml"
	source.write_bytes((FIXTURES_DIR / "article_vigueur.xml").read_bytes())
	monkeypatch.setattr(
		"sys.argv",
		["load_corpus", str(source), "--livre", "II", "--dry-run"],
	)
	client = Mock(spec=BigQueryClient)
	monkeypatch.setattr(
		"vil_pipeline.jobs.load_corpus.BigQueryClient", Mock(return_value=client)
	)

	main()

	output = json.loads(capsys.readouterr().out)
	assert output["articles_lus"] == 1
	assert output["dry_run"] is True


def test_dry_run_counts_matching_records_and_only_writes_tracking(capsys):
	client = Mock(spec=BigQueryClient)
	stats = load_corpus(FIXTURES_DIR, livre="II", dry_run=True, client=client)

	assert stats.read == 2
	assert stats.inserted == 0
	assert stats.updated == 0
	assert stats.ignored == 0
	log = json.loads(capsys.readouterr().out)
	assert log["event"] == "corpus_load_complete"
	assert log["articles_lus"] == 2
	assert log["dry_run"] is True
	assert client.query.call_count == 2
	client.insert.assert_not_called()


def test_load_uses_temporary_table_and_merges_with_dml_counts(tmp_path):
	fixture = tmp_path / "article.xml"
	fixture.write_bytes((FIXTURES_DIR / "article_vigueur.xml").read_bytes())
	client = Mock(spec=BigQueryClient)
	loaded_rows = []

	def capture_load(_table_id, rows, *, schema):
		loaded_rows.extend(rows)

	client.insert.side_effect = capture_load
	articles_job = Mock()
	articles_job.dml_stats = SimpleNamespace(
		inserted_row_count=0,
		updated_row_count=0,
	)
	versions_job = Mock()
	versions_job.dml_stats = SimpleNamespace(
		inserted_row_count=1,
		updated_row_count=0,
	)
	client.query_job.side_effect = [articles_job, versions_job]

	stats = load_corpus(fixture, livre="II", project_id="test-project", client=client)

	assert stats.read == 1
	assert stats.inserted == 1
	assert stats.updated == 0
	assert stats.ignored == 0
	client.insert.assert_called_once()
	assert len(loaded_rows) == 1
	assert loaded_rows[0]["article_version_id"] == "LEGIARTI000006901674"
	assert loaded_rows[0]["texte"]
	assert loaded_rows[0]["code_id"] == DEFAULT_CODE_ID
	assert loaded_rows[0]["chapitre_id"].startswith("LEGISCTA")
	assert loaded_rows[0]["livre"]
	assert client.insert.call_args.args[0].startswith(
		"test-project.raw._tmp_corpus_",
	)
	assert client.query_job.call_count == 2
	assert (
		"MERGE `%s.raw.articles`"
		in client.query_job.call_args_list[0].args[0]
	)
	assert (
		"MERGE `%s.raw.article_versions`"
		in client.query_job.call_args_list[1].args[0]
	)
	for query_call in client.query_job.call_args_list:
		parameters = query_call.args[1]
		assert [parameter.value for parameter in parameters] == [
			"test-project",
			client.insert.call_args.args[0],
		]
	for job in (articles_job, versions_job):
		job.result.assert_called_once_with()
	client.delete_table.assert_called_once_with(client.insert.call_args.args[0])


def test_load_logs_inserted_and_updated_counts(tmp_path):
	fixture = tmp_path / "article.xml"
	fixture.write_bytes((FIXTURES_DIR / "article_vigueur.xml").read_bytes())
	client = Mock(spec=BigQueryClient)
	client.insert.side_effect = lambda _table, rows, **_kwargs: list(rows)
	articles_job = Mock()
	articles_job.dml_stats = SimpleNamespace(
		inserted_row_count=0,
		updated_row_count=0,
	)
	versions_job = Mock()
	versions_job.dml_stats = SimpleNamespace(
		inserted_row_count=0,
		updated_row_count=1,
	)
	client.query_job.side_effect = [articles_job, versions_job]
	logger = Mock()

	stats = load_corpus(
		fixture,
		livre="II",
		project_id="test-project",
		client=client,
		logger=logger,
	)

	assert stats.updated == 1
	assert stats.ignored == 0
	logger.info.assert_called_once_with(
		"corpus_load_complete",
		articles_lus=1,
		articles_inseres=0,
		articles_mis_a_jour=1,
		articles_ignores=0,
		dry_run=False,
	)


def test_merge_counts_unchanged_versions_as_ignored(tmp_path):
	fixture = tmp_path / "article.xml"
	fixture.write_bytes((FIXTURES_DIR / "article_vigueur.xml").read_bytes())
	client = Mock(spec=BigQueryClient)
	client.insert.side_effect = lambda _table, rows, **_kwargs: list(rows)
	jobs = []
	for _ in range(2):
		job = Mock()
		job.dml_stats = SimpleNamespace(
			inserted_row_count=0,
			updated_row_count=0,
		)
		jobs.append(job)
	client.query_job.side_effect = jobs

	stats = load_corpus(fixture, livre="II", project_id="test-project", client=client)

	assert stats.read == 1
	assert stats.inserted == 0
	assert stats.updated == 0
	assert stats.ignored == 1


def test_main_dry_run_creates_client_for_tracking(
	tmp_path,
	monkeypatch,
	capsys,
):
	fixture = tmp_path / "article.xml"
	fixture.write_bytes((FIXTURES_DIR / "article_vigueur.xml").read_bytes())
	monkeypatch.setattr(
		"sys.argv",
		["load_corpus", str(fixture), "--livre", "II", "--dry-run"],
	)
	client = Mock(spec=BigQueryClient)
	client_factory = Mock(return_value=client)
	monkeypatch.setattr("vil_pipeline.jobs.load_corpus.BigQueryClient", client_factory)

	main()

	client_factory.assert_called_once()
	assert client.query.call_count == 2
	client.insert.assert_not_called()
	log = json.loads(capsys.readouterr().out)
	assert log["articles_lus"] == 1
	assert log["articles_inseres"] == 0
	assert log["articles_mis_a_jour"] == 0
	assert log["articles_ignores"] == 0


def test_empty_corpus_is_tracked_without_creating_staging_table(tmp_path):
	client = Mock(spec=BigQueryClient)

	stats = load_corpus(tmp_path, project_id="test-project", client=client)

	assert stats.read == 0
	assert stats.inserted == 0
	assert stats.updated == 0
	assert stats.ignored == 0
	assert client.query.call_count == 2
	client.insert.assert_not_called()
