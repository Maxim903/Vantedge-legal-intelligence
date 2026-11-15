"""Pipeline command-line interface."""

import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import perf_counter

import typer
from google.cloud import bigquery
from pydantic import SecretStr

from prompts.loader import load_prompt
from vil_pipeline.apply_migrations import apply_migrations
from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.clients.dataforseo import DataForSEOClient
from vil_pipeline.clients.gcs import GCSClient
from vil_pipeline.clients.llm_gemini import GeminiLLMClient
from vil_pipeline.jobs.collect_intent import (
	IntentCollectionStats,
	collect_intent,
)
from vil_pipeline.jobs.collect_serp import SerpCollectionStats, collect_serp
from vil_pipeline.jobs.collect_volumes import (
	VolumeCollectionStats,
	collect_volumes,
)
from vil_pipeline.jobs.evaluate_extraction import (
	DEFAULT_GOLDEN,
	DEFAULT_TITLES,
	evaluate_extraction,
)
from vil_pipeline.jobs.extract_entities import extract_entities
from vil_pipeline.jobs.load_corpus import load_corpus
from vil_pipeline.jobs.review_queue import export_review, import_review

app = typer.Typer(help="Outils du pipeline Vantedge Legal Intelligence.")
_ARCHIVE_OPTION = typer.Option(
	...,
	"--archive",
	exists=True,
	file_okay=True,
	dir_okay=True,
	readable=True,
	help="Archive LEGI (.tar.gz) ou dossier/fichier XML.",
)
_LIVRE_OPTION = typer.Option(
	"I",
	"--livre",
	help="Livre à charger, en chiffre romain (défaut : I).",
)
_DRY_RUN_OPTION = typer.Option(
	False,
	"--dry-run",
	help="Compte les articles sans écrire dans BigQuery.",
)
_GOLDEN_OPTION = typer.Option(DEFAULT_GOLDEN, "--golden")
_TITLES_OPTION = typer.Option(DEFAULT_TITLES, "--titles")
_REPORT_OPTION = typer.Option(None, "--output")
_REVIEW_OUTPUT_OPTION = typer.Option(..., "--output", help="Fichier CSV à créer.")
_REVIEW_INPUT_OPTION = typer.Option(
	..., "--input", exists=True, dir_okay=False, readable=True,
	help="Fichier CSV de revue complété.",
)


@app.callback()
def cli_root() -> None:
	"""Commandes du pipeline."""


@app.command("migrate")
def migrate_command(
	project_id: str = typer.Option(
		..., "--project-id", envvar="GCP_PROJECT_ID", help="Projet Google Cloud."
	),
	location: str | None = typer.Option(
		None, "--location", envvar="BQ_LOCATION", help="Emplacement BigQuery."
	),
) -> None:
	"""Applique les migrations BigQuery en attente."""
	client = bigquery.Client(project=project_id, location=location)
	for_migrations = apply_migrations(client)
	if for_migrations:
		for migration_id in for_migrations:
			typer.echo(f"Migration appliquée : {migration_id}")
	else:
		typer.echo("Aucune migration en attente.")


@app.command("extract-entities")
def extract_entities_command(
	max_cost: str = typer.Option(..., "--max-cost", help="Budget estimé maximal."),
	cost_per_call: str = typer.Option(
		..., "--cost-per-call", help="Coût estimé par appel LLM, dans la même devise."
	),
	project_id: str = typer.Option(..., "--project-id", envvar="GCP_PROJECT_ID"),
	location: str | None = typer.Option(None, "--location", envvar="BQ_LOCATION"),
	model: str = typer.Option("gemini-2.5-flash", "--model"),
	batch_size: int = typer.Option(100, "--batch-size", min=1),
	dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
	"""Extrait les notions des articles en vigueur non encore traités."""
	try:
		budget = Decimal(max_cost)
		unit_cost = Decimal(cost_per_call)
	except InvalidOperation as error:
		raise typer.BadParameter(
			"Les coûts doivent être des nombres décimaux."
		) from error
	prompt, version = load_prompt()
	bq = BigQueryClient(project_id, location)
	if dry_run:
		stats = extract_entities(
			bq, None, prompt=prompt, version_prompt=version, model=model,
			max_cost=budget, cost_per_call=unit_cost, batch_size=batch_size,
			dry_run=True,
		)
	else:
		import os

		key = os.environ.get("LLM_API_KEY")
		if not key:
			raise typer.BadParameter("LLM_API_KEY est nécessaire hors dry-run.")
		with GeminiLLMClient(SecretStr(key), model=model) as llm:
			stats = extract_entities(
				bq, llm, prompt=prompt, version_prompt=version, model=model,
				max_cost=budget, cost_per_call=unit_cost, batch_size=batch_size,
			)
	typer.echo(
		f"Extraction : statut {stats.status}, lus {stats.read}, "
		f"traités {stats.processed}, quarantaine {stats.quarantined}, "
		f"appels {stats.calls}, coût estimé {stats.estimated_cost}."
	)


@app.command("collect-volumes")
def collect_volumes_command(
	max_cost: str = typer.Option(..., "--max-cost", help="Budget maximal estimé."),
	cost_per_call: str = typer.Option(
		..., "--cost-per-call", help="Coût estimé par mot-clé DataForSEO."
	),
	project_id: str = typer.Option(..., "--project-id", envvar="GCP_PROJECT_ID"),
	location: str | None = typer.Option(None, "--location", envvar="BQ_LOCATION"),
	dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
	"""Collecte les volumes des requêtes candidates non archivées récemment."""
	try:
		budget = Decimal(max_cost)
		unit_cost = Decimal(cost_per_call)
	except InvalidOperation as error:
		raise typer.BadParameter(
			"Les coûts doivent être des nombres décimaux."
		) from error

	bucket = os.environ.get("GCS_BUCKET_RAW")
	if not bucket:
		raise typer.BadParameter("GCS_BUCKET_RAW est nécessaire.")
	bq = BigQueryClient(project_id, location)
	gcs = GCSClient(bucket)
	if dry_run:
		stats = collect_volumes(
			bq, gcs, None, max_cost=budget,
			cost_per_call=unit_cost, dry_run=True,
		)
	else:
		login = os.environ.get("DATAFORSEO_LOGIN")
		password = os.environ.get("DATAFORSEO_PASSWORD")
		if not login or not password:
			raise typer.BadParameter(
				"DATAFORSEO_LOGIN et DATAFORSEO_PASSWORD sont nécessaires hors dry-run."
			)
		with DataForSEOClient(login, password) as provider:
			stats = collect_volumes(
				bq, gcs, provider, max_cost=budget,
				cost_per_call=unit_cost,
			)
	if not isinstance(stats, VolumeCollectionStats):
		raise RuntimeError("Résultat inattendu du job collect_volumes")
	typer.echo(
		f"Volumes : statut {stats.status}, requêtes {stats.read}, "
		f"cache frais {stats.cached}, appels {stats.calls}, "
		f"coût estimé {stats.estimated_cost} USD, "
		f"coût réel {stats.actual_cost} USD."
	)


@app.command("collect-serp")
def collect_serp_command(
	top_n: int = typer.Option(
		..., "--top-n", min=1, help="Nombre de requêtes de plus fort volume."
	),
	max_cost: str = typer.Option(..., "--max-cost", help="Budget maximal estimé."),
	cost_per_call: str = typer.Option(
		..., "--cost-per-call", help="Coût estimé par SERP DataForSEO."
	),
	project_id: str = typer.Option(..., "--project-id", envvar="GCP_PROJECT_ID"),
	location: str | None = typer.Option(None, "--location", envvar="BQ_LOCATION"),
	dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
	"""Collecte le top 10 des résultats pour les requêtes de plus fort volume."""
	try:
		budget = Decimal(max_cost)
		unit_cost = Decimal(cost_per_call)
	except InvalidOperation as error:
		raise typer.BadParameter(
			"Les coûts doivent être des nombres décimaux."
		) from error

	bucket = os.environ.get("GCS_BUCKET_RAW")
	if not bucket:
		raise typer.BadParameter("GCS_BUCKET_RAW est nécessaire.")
	bq = BigQueryClient(project_id, location)
	gcs = GCSClient(bucket)
	if dry_run:
		stats = collect_serp(
			bq, gcs, None, top_n=top_n, max_cost=budget,
			cost_per_call=unit_cost, dry_run=True,
		)
	else:
		login = os.environ.get("DATAFORSEO_LOGIN")
		password = os.environ.get("DATAFORSEO_PASSWORD")
		if not login or not password:
			raise typer.BadParameter(
				"DATAFORSEO_LOGIN et DATAFORSEO_PASSWORD sont nécessaires hors dry-run."
			)
		with DataForSEOClient(login, password) as provider:
			stats = collect_serp(
				bq, gcs, provider, top_n=top_n, max_cost=budget,
				cost_per_call=unit_cost,
			)
	if not isinstance(stats, SerpCollectionStats):
		raise RuntimeError("Résultat inattendu du job collect_serp")
	typer.echo(
		f"SERP : statut {stats.status}, requêtes classées {stats.ranked}, "
		f"sélectionnées {stats.selected}, cache frais {stats.cached}, "
		f"appels {stats.calls}, coût estimé {stats.estimated_cost} USD, "
		f"coût réel {stats.actual_cost} USD."
	)


@app.command("collect-intent")
def collect_intent_command(
	project_id: str = typer.Option(..., "--project-id", envvar="GCP_PROJECT_ID"),
	location: str | None = typer.Option(None, "--location", envvar="BQ_LOCATION"),
	dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
	"""Classifie l'intention dominante des requêtes candidates."""
	bq = BigQueryClient(project_id, location)
	stats = collect_intent(bq, dry_run=dry_run)
	if not isinstance(stats, IntentCollectionStats):
		raise RuntimeError("Résultat inattendu du job collect_intent")
	typer.echo(
		f"Intentions : statut {stats.status}, requêtes {stats.read}, "
		f"classées {stats.classified}, répartition {stats.distribution}."
	)


@app.command("evaluate-extraction")
def evaluate_extraction_command(
	model: str = typer.Option(..., "--model", help="Modèle évalué."),
	version_prompt: str = typer.Option(..., "--version-prompt", help="Hash du prompt."),
	project_id: str = typer.Option(..., "--project-id", envvar="GCP_PROJECT_ID"),
	location: str | None = typer.Option(None, "--location", envvar="BQ_LOCATION"),
	golden: Path = _GOLDEN_OPTION,
	titles: Path = _TITLES_OPTION,
	output: Path | None = _REPORT_OPTION,
) -> None:
	"""Évalue des extractions déjà enregistrées par rapport au jeu annoté."""
	report = evaluate_extraction(
		BigQueryClient(project_id, location),
		model=model,
		version_prompt=version_prompt,
		golden_path=golden,
		titles_path=titles,
		output_path=output,
	)
	typer.echo(f"Rapport d'évaluation : {report}")


@app.command("load-corpus")
def load_corpus_command(
	archive: Path = _ARCHIVE_OPTION,
	livre: str = _LIVRE_OPTION,
	dry_run: bool = _DRY_RUN_OPTION,
) -> None:
	"""Charge les articles du corpus dans les tables BigQuery raw."""
	started = perf_counter()
	stats = load_corpus(archive, livre=livre, dry_run=dry_run)
	duration = perf_counter() - started
	typer.echo(
		f"Corpus chargé : lus {stats.read}, insérés {stats.inserted}, "
		f"mis à jour {stats.updated}, ignorés {stats.ignored}, "
		f"durée {duration:.2f} s.",
	)


@app.command("export-review")
def export_review_command(
	output: Path = _REVIEW_OUTPUT_OPTION,
	threshold: float = typer.Option(
		..., "--threshold", min=0, max=1, help="Seuil de confiance exclusif."
	),
	project_id: str = typer.Option(..., "--project-id", envvar="GCP_PROJECT_ID"),
	location: str | None = typer.Option(None, "--location", envvar="BQ_LOCATION"),
) -> None:
	"""Exporte les entités à revoir dans un nouveau CSV."""
	count = export_review(
		BigQueryClient(project_id, location), output, threshold=threshold
	)
	typer.echo(f"Entités exportées : {count} dans {output}")


@app.command("import-review")
def import_review_command(
	source: Path = _REVIEW_INPUT_OPTION,
	project_id: str = typer.Option(..., "--project-id", envvar="GCP_PROJECT_ID"),
	location: str | None = typer.Option(None, "--location", envvar="BQ_LOCATION"),
) -> None:
	"""Importe atomiquement les décisions du CSV de revue."""
	count = import_review(BigQueryClient(project_id, location), source)
	typer.echo(f"Décisions importées : {count}")


def main() -> None:
	"""Run the pipeline CLI."""
	app()


if __name__ == "__main__":
	main()
