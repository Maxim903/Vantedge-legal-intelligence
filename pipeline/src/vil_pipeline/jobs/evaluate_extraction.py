"""Evaluate saved extraction results against an annotated golden set."""

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from google.cloud.bigquery import QueryJob, ScalarQueryParameter

from vil_pipeline.clients.bigquery import BigQueryClient
from vil_pipeline.extraction.validate import validate_extraction

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_GOLDEN = ROOT / "docs/05-ia/golden-set.csv"
DEFAULT_TITLES = ROOT / "docs/05-ia/golden-set-titres.csv"
DEFAULT_REPORTS = ROOT / "docs/05-ia/evaluations"

_RESULTS_SQL = """
SELECT article_version_id, statut, resultat_json
FROM `ops.extraction_results`
WHERE version_prompt = @version_prompt AND modele_llm = @model
  AND article_version_id IN UNNEST(JSON_VALUE_ARRAY(@article_ids))
"""


@dataclass(frozen=True)
class ArticleReference:
	article_id: str
	text: str
	title_id: str
	title: str
	notions: frozenset[str]


@dataclass(frozen=True)
class Counts:
	tp: int = 0
	fp: int = 0
	fn: int = 0

	def __add__(self, other: "Counts") -> "Counts":
		return Counts(self.tp + other.tp, self.fp + other.fp, self.fn + other.fn)

	@property
	def precision(self) -> float | None:
		return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

	@property
	def recall(self) -> float | None:
		return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

	@property
	def f1(self) -> float | None:
		denominator = 2 * self.tp + self.fp + self.fn
		return 2 * self.tp / denominator if denominator else None


def normalize_notion(value: str) -> str:
	"""Lowercase, remove accents and apply a deliberately simple plural rule."""
	plain = "".join(
		char for char in unicodedata.normalize("NFKD", value.casefold())
		if not unicodedata.combining(char)
	)

	def singular(match: re.Match[str]) -> str:
		word = match.group()
		if len(word) > 4 and word.endswith("eaux"):
			return word[:-1]
		if (
			len(word) > 3
			and word.endswith("s")
			and not word.endswith(("ss", "us", "is"))
		):
			return word[:-1]
		return word

	return " ".join(re.sub(r"[^\W\d_]+", singular, plain).split())


def _read_csv(path: Path, fields: set[str]) -> list[dict[str, str]]:
	with path.open(encoding="utf-8-sig", newline="") as stream:
		reader = csv.DictReader(stream)
		if reader.fieldnames is None or not fields.issubset(reader.fieldnames):
			raise ValueError(f"Colonnes manquantes dans {path} : {sorted(fields)}")
		rows: list[dict[str, str]] = []
		for row in reader:
			if None in row or any(value is None for value in row.values()):
				raise ValueError(
					f"Ligne CSV invalide dans {path}, ligne {reader.line_num}"
				)
			rows.append(row)
		return rows


def load_reference(
	golden_path: Path, titles_path: Path
) -> tuple[list[ArticleReference], int, int]:
	"""Read references, omitting unannotated rows but never treating them as empty."""
	titles: dict[str, dict[str, str]] = {}
	for row in _read_csv(
		titles_path, {"article_version_id", "titre_id", "titre", "texte_sha256"}
	):
		key = row["article_version_id"].strip()
		if (
			not key or key in titles
			or not row["titre_id"].strip() or not row["titre"].strip()
		):
			raise ValueError(f"Correspondance de titre invalide ou dupliquée : {key}")
		titles[key] = row

	refs: list[ArticleReference] = []
	seen: set[str] = set()
	labels: dict[str, str] = {}
	skipped = 0
	for row in _read_csv(
		golden_path, {"article_version_id", "texte", "notions_attendues"}
	):
		key, text = row["article_version_id"].strip(), row["texte"]
		if not key or key in seen or not text.strip():
			raise ValueError(
				f"Article vide ou dupliqué dans le jeu de référence : {key}"
			)
		seen.add(key)
		if key not in titles:
			raise ValueError(f"Titre manquant pour {key}")
		title = titles[key]
		if hashlib.sha256(text.encode("utf-8")).hexdigest() != title["texte_sha256"]:
			raise ValueError(
				f"Le texte de référence ne correspond pas au titre : {key}"
			)
		title_id = title["titre_id"]
		if title_id in labels and labels[title_id] != title["titre"]:
			raise ValueError(f"Libellés contradictoires pour le titre {title_id}")
		labels[title_id] = title["titre"]
		annotation = row["notions_attendues"].strip()
		if not annotation:
			skipped += 1
			continue
		try:
			data = json.loads(annotation)
		except json.JSONDecodeError as error:
			raise ValueError(f"Annotation JSON invalide pour {key}") from error
		if not isinstance(data, list) or any(
			not isinstance(item, str) or not item.strip() for item in data
		):
			raise ValueError(f"Liste de notions invalide pour {key}")
		refs.append(ArticleReference(
			key, text, title_id, title["titre"], frozenset(map(normalize_notion, data))
		))
	if set(titles) != seen:
		raise ValueError("Le fichier des titres ne correspond pas au jeu de référence")
	if not refs:
		raise ValueError("Aucun article annoté dans le jeu de référence")
	return refs, len(seen), skipped


def fetch_predictions(
	client: BigQueryClient, refs: list[ArticleReference], *, model: str, prompt: str
) -> dict[str, frozenset[str]]:
	"""Fetch one validated, successful result per annotated article."""
	if not model.strip() or not prompt.strip():
		raise ValueError("Le modèle et la version du prompt sont obligatoires")
	rows = client.query(_RESULTS_SQL, [
		ScalarQueryParameter("model", "STRING", model),
		ScalarQueryParameter("version_prompt", "STRING", prompt),
		ScalarQueryParameter(
			"article_ids", "STRING", json.dumps([ref.article_id for ref in refs])
		),
	])
	if isinstance(rows, QueryJob):
		raise ValueError("Le client BigQuery ne doit pas être en mode dry-run")
	by_id = {ref.article_id: ref for ref in refs}
	predictions: dict[str, frozenset[str]] = {}
	for row in rows:
		key = row["article_version_id"]
		if key not in by_id or key in predictions:
			raise ValueError(f"Résultat inattendu ou dupliqué pour {key}")
		if row["statut"] != "SUCCESS":
			raise ValueError(f"Extraction non réussie pour {key} : {row['statut']}")
		result = validate_extraction(
			row["resultat_json"], by_id[key].text, article_version_id=key
		)
		predictions[key] = frozenset(
			normalize_notion(n.libelle) for n in result.notions
		)
	missing = sorted(set(by_id) - set(predictions))
	if missing:
		raise ValueError(
			f"Résultats absents pour {len(missing)} articles : {', '.join(missing)}"
		)
	return predictions


def score(
	refs: list[ArticleReference], predictions: dict[str, frozenset[str]]
) -> tuple[Counts, dict[tuple[str, str], tuple[Counts, int]]]:
	"""Compute article-level set matches aggregated as micro counts."""
	if set(predictions) != {ref.article_id for ref in refs}:
		raise ValueError("Les résultats ne correspondent pas aux articles évalués")
	total = Counts()
	titles: dict[tuple[str, str], tuple[Counts, int]] = {}
	for ref in refs:
		found = predictions[ref.article_id]
		counts = Counts(
			len(ref.notions & found), len(found - ref.notions), len(ref.notions - found)
		)
		total += counts
		key = (ref.title_id, ref.title)
		current, articles = titles.get(key, (Counts(), 0))
		titles[key] = current + counts, articles + 1
	return total, titles


def _metric(value: float | None) -> str:
	return "N/D" if value is None else f"{value:.2%}"


def _markdown(value: str) -> str:
	return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def evaluate_extraction(
	client: BigQueryClient,
	*,
	model: str,
	version_prompt: str,
	golden_path: Path = DEFAULT_GOLDEN,
	titles_path: Path = DEFAULT_TITLES,
	output_path: Path | None = None,
) -> Path:
	"""Write an evaluation report without changing references or stored results."""
	refs, total_articles, skipped = load_reference(golden_path, titles_path)
	predictions = fetch_predictions(client, refs, model=model, prompt=version_prompt)
	total, titles = score(refs, predictions)
	now = datetime.now(UTC)
	if output_path is None:
		output_path = DEFAULT_REPORTS / f"{now:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}.md"
	golden_hash = hashlib.sha256(golden_path.read_bytes()).hexdigest()
	titles_hash = hashlib.sha256(titles_path.read_bytes()).hexdigest()
	lines = [
		"# Évaluation de l'extraction",
		"",
		f"- Date UTC : {now.isoformat()}",
		f"- Modèle : {_markdown(model)}",
		f"- Version du prompt : {_markdown(version_prompt)}",
		f"- Jeu de référence SHA-256 : {golden_hash}",
		f"- Titres SHA-256 : {titles_hash}",
		f"- Articles évalués : {len(refs)} / {total_articles}",
		f"- Articles non annotés exclus : {skipped}",
		"- Agrégation : micro, correspondances exactes après normalisation "
		"par article.",
		"- N/D : dénominateur nul ; les cellules vides ne sont pas des annotations.",
		"",
		"| Périmètre | Articles | VP | FP | FN | Précision | Rappel | F1 |",
		"|---|---:|---:|---:|---:|---:|---:|---:|",
	]

	def add_row(label: str, articles: int, counts: Counts) -> None:
		lines.append(
			f"| {_markdown(label)} | {articles} | {counts.tp} | {counts.fp} | "
			f"{counts.fn} | {_metric(counts.precision)} | {_metric(counts.recall)} "
			f"| {_metric(counts.f1)} |"
		)

	add_row("Global", len(refs), total)
	for (title_id, title), (counts, count) in sorted(titles.items()):
		add_row(f"{title} ({title_id})", count, counts)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("x", encoding="utf-8", newline="\n") as stream:
		stream.write("\n".join(lines) + "\n")
	return output_path
