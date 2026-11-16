"""Load and filter article XML files from a LEGI corpus."""

import argparse
import itertools
import os
import re
import shutil
import tarfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

import structlog
from google.cloud import bigquery

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.errors import ExtractionError
from vil_pipeline.logging import configure_logging
from vil_pipeline.models.corpus import Article, ArticleVersion
from vil_pipeline.parsers.legi import parse_legi_article

DEFAULT_CODE_ID = "LEGITEXT000006072050"
_STAGING_SCHEMA = [
	bigquery.SchemaField("article_id", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("article_version_id", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("numero", "STRING"),
	bigquery.SchemaField("code_id", "STRING"),
	bigquery.SchemaField("livre_id", "STRING"),
	bigquery.SchemaField("livre", "STRING"),
	bigquery.SchemaField("titre_id", "STRING"),
	bigquery.SchemaField("titre", "STRING"),
	bigquery.SchemaField("chapitre_id", "STRING"),
	bigquery.SchemaField("chapitre", "STRING"),
	bigquery.SchemaField("date_debut", "DATE", mode="REQUIRED"),
	bigquery.SchemaField("date_fin", "DATE"),
	bigquery.SchemaField("etat", "STRING", mode="REQUIRED"),
	bigquery.SchemaField("texte", "STRING"),
]
_MERGE_ARTICLES_SQL = '''
EXECUTE IMMEDIATE FORMAT("""
MERGE `%s.raw.articles` AS target
USING (
  SELECT
    article_id, numero, code_id, livre_id, livre,
    titre_id, titre, chapitre_id, chapitre
  FROM `%s`
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY article_id ORDER BY article_version_id DESC
  ) = 1
) AS source
ON target.article_id = source.article_id
WHEN MATCHED AND (
  target.numero IS DISTINCT FROM source.numero
  OR target.code_id IS DISTINCT FROM source.code_id
  OR target.livre_id IS DISTINCT FROM source.livre_id
  OR target.livre IS DISTINCT FROM source.livre
  OR target.titre_id IS DISTINCT FROM source.titre_id
  OR target.titre IS DISTINCT FROM source.titre
  OR target.chapitre_id IS DISTINCT FROM source.chapitre_id
  OR target.chapitre IS DISTINCT FROM source.chapitre
) THEN UPDATE SET
  numero = source.numero,
  code_id = source.code_id,
  livre_id = source.livre_id,
  livre = source.livre,
  titre_id = source.titre_id,
  titre = source.titre,
  chapitre_id = source.chapitre_id,
  chapitre = source.chapitre
WHEN NOT MATCHED THEN
  INSERT (
    article_id, numero, code_id, livre_id, livre,
    titre_id, titre, chapitre_id, chapitre
  )
  VALUES (
    source.article_id, source.numero, source.code_id, source.livre_id,
    source.livre, source.titre_id, source.titre, source.chapitre_id,
    source.chapitre
  )
""", @project_id, @staging_table)
'''
_MERGE_VERSIONS_SQL = '''
EXECUTE IMMEDIATE FORMAT("""
MERGE `%s.raw.article_versions` AS target
USING (
  SELECT
    article_version_id, article_id, date_debut, date_fin, etat, texte
  FROM `%s`
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY article_version_id ORDER BY article_version_id DESC
  ) = 1
) AS source
ON target.article_version_id = source.article_version_id
WHEN MATCHED AND (
  target.article_id IS DISTINCT FROM source.article_id
  OR target.date_debut IS DISTINCT FROM source.date_debut
  OR target.date_fin IS DISTINCT FROM source.date_fin
  OR target.etat IS DISTINCT FROM source.etat
  OR target.texte IS DISTINCT FROM source.texte
) THEN UPDATE SET
  article_id = source.article_id,
  date_debut = source.date_debut,
  date_fin = source.date_fin,
  etat = source.etat,
  texte = source.texte
WHEN NOT MATCHED THEN
  INSERT (article_version_id, article_id, date_debut, date_fin, etat, texte)
  VALUES (
    source.article_version_id, source.article_id,
    source.date_debut, source.date_fin, source.etat, source.texte
  )
""", @project_id, @staging_table)
'''
_LIVRE_PATTERN = re.compile(
	r"^(?:livre\s+)?(x{0,3}(?:ix|iv|v?i{0,3}))(?:er|re|e)?(?:\b|$)",
	re.IGNORECASE,
)


@dataclass(frozen=True)
class LoadStats:
	"""Counts for a corpus loading run."""

	read: int
	inserted: int
	updated: int
	ignored: int


def _normalize_livre(value: str) -> str | None:
	match = _LIVRE_PATTERN.match(value.strip())
	return match.group(1).upper() if match else None


def is_in_scope(
	article: Article,
	*,
	livre: str = "I",
	code_id: str = DEFAULT_CODE_ID,
) -> bool:
	"""Return whether an article belongs to the configured code and book."""
	target_livre = _normalize_livre(livre)
	article_livre = _normalize_livre(article.livre)
	return (
		article.code_id == code_id
		and target_livre is not None
		and article_livre == target_livre
	)


def iter_corpus(
	source: str | Path,
	*,
	livre: str = "I",
	code_id: str = DEFAULT_CODE_ID,
) -> Iterator[tuple[Article, ArticleVersion]]:
	"""Yield parsed article/version pairs matching the code and book filters."""
	path = Path(source)
	if path.is_dir():
		for xml_path in sorted(path.rglob("*.xml")):
			article, version = parse_legi_article(xml_path)
			if is_in_scope(article, livre=livre, code_id=code_id):
				yield article, version
		return

	if tarfile.is_tarfile(path):
		try:
			with tarfile.open(path, mode="r|*") as archive:
				for member in archive:
					if not member.isfile() or not member.name.lower().endswith(".xml"):
						continue
					stream = archive.extractfile(member)
					if stream is None:
						continue
					with stream, NamedTemporaryFile(suffix=".xml") as temporary:
						shutil.copyfileobj(stream, temporary)
						temporary.flush()
						try:
							article, version = parse_legi_article(temporary.name)
						except ExtractionError as exc:
							raise ExtractionError(
								f"Unable to parse {path}!{member.name}: {exc}",
							) from exc
					if is_in_scope(article, livre=livre, code_id=code_id):
						yield article, version
		except (OSError, tarfile.TarError) as exc:
			raise ExtractionError(f"Unable to read LEGI archive {path}: {exc}") from exc
		return

	article, version = parse_legi_article(path)
	if is_in_scope(article, livre=livre, code_id=code_id):
		yield article, version


def _dml_count(job: bigquery.QueryJob, operation: str) -> int:
	stats = job.dml_stats
	if stats is None:
		raise RuntimeError(f"BigQuery did not return DML statistics for {operation}")
	value = getattr(stats, f"{operation}_row_count")
	return int(value)


def load_corpus(
	source: str | Path,
	*,
	livre: str = "I",
	project_id: str | None = None,
	client: BigQueryClient | None = None,
	dry_run: bool = False,
	logger: structlog.stdlib.BoundLogger | None = None,
) -> LoadStats:
	"""Load matching corpus records through a temporary table and idempotent MERGEs."""
	log = logger or configure_logging(run_id=str(uuid4()), job="load_corpus")
	if dry_run:
		count = sum(1 for _ in iter_corpus(source, livre=livre))
		stats = LoadStats(read=count, inserted=0, updated=0, ignored=0)
		log.info(
			"corpus_load_complete",
			articles_lus=stats.read,
			articles_inseres=stats.inserted,
			articles_mis_a_jour=stats.updated,
			articles_ignores=stats.ignored,
			dry_run=True,
		)
		return stats

	project_id = project_id or os.environ.get("GCP_PROJECT_ID")
	if not project_id:
		raise ValueError("GCP_PROJECT_ID or project_id is required")

	if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project_id):
		raise ValueError("project_id must be a valid Google Cloud project ID")

	staging_table = f"{project_id}.raw._tmp_corpus_{uuid4().hex}"
	read_count = 0

	def rows() -> Iterator[dict[str, str | None]]:
		nonlocal read_count
		for article, version in iter_corpus(source, livre=livre):
			read_count += 1
			yield {
				"article_id": article.article_id,
				"article_version_id": version.article_version_id,
				"numero": article.numero,
				"code_id": article.code_id,
				"livre_id": article.livre_id,
				"livre": article.livre,
				"titre_id": article.titre_id,
				"titre": article.titre,
				"chapitre_id": article.chapitre_id,
				"chapitre": article.chapitre,
				"date_debut": version.date_debut.isoformat(),
				"date_fin": (
					version.date_fin.isoformat()
					if version.date_fin is not None
					else None
				),
				"etat": version.etat,
				"texte": version.texte,
			}

	row_iterator = rows()
	first_row = next(row_iterator, None)
	if first_row is None:
		stats = LoadStats(read=0, inserted=0, updated=0, ignored=0)
		log.info(
			"corpus_load_complete",
			articles_lus=stats.read,
			articles_inseres=stats.inserted,
			articles_mis_a_jour=stats.updated,
			articles_ignores=stats.ignored,
			dry_run=False,
		)
		return stats

	if client is None:
		client = BigQueryClient(project_id, os.environ.get("BQ_LOCATION"))

	try:
		client.insert(
			staging_table,
			itertools.chain((first_row,), row_iterator),
			schema=_STAGING_SCHEMA,
		)
		merge_parameters = [
			bigquery.ScalarQueryParameter("project_id", "STRING", project_id),
			bigquery.ScalarQueryParameter("staging_table", "STRING", staging_table),
		]
		articles_job = client.query_job(_MERGE_ARTICLES_SQL, merge_parameters)
		articles_job.result()
		versions_job = client.query_job(_MERGE_VERSIONS_SQL, merge_parameters)
		versions_job.result()
	finally:
		client.delete_table(staging_table)

	inserted = _dml_count(versions_job, "inserted")
	updated = _dml_count(versions_job, "updated")
	stats = LoadStats(
		read=read_count,
		inserted=inserted,
		updated=updated,
		ignored=read_count - inserted - updated,
	)
	log.info(
		"corpus_load_complete",
		articles_lus=stats.read,
		articles_inseres=stats.inserted,
		articles_mis_a_jour=stats.updated,
		articles_ignores=stats.ignored,
		dry_run=False,
	)
	return stats


def main() -> None:
	"""Load filtered corpus records into BigQuery raw tables."""
	parser = argparse.ArgumentParser(description="Filter a LEGI XML corpus.")
	parser.add_argument("source", type=Path, help="XML file or directory of XML files.")
	parser.add_argument(
		"--livre",
		default="I",
		help="Book to keep, as a Roman numeral (default: I).",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Parse and count matching articles without accessing BigQuery.",
	)
	args = parser.parse_args()

	project_id = os.environ.get("GCP_PROJECT_ID")
	load_corpus(
		args.source,
		livre=args.livre,
		project_id=project_id,
		dry_run=args.dry_run,
	)


if __name__ == "__main__":
	main()
