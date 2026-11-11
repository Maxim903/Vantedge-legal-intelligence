#!/usr/bin/env python3
"""Generate a reproducible, title-stratified LEGI annotation sample."""

import argparse
import csv
import hashlib
import io
import json
import tarfile
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from lxml import etree  # type: ignore[import-untyped]

from vil_pipeline.errors import ExtractionError
from vil_pipeline.jobs.load_corpus import DEFAULT_CODE_ID, _normalize_livre, is_in_scope
from vil_pipeline.parsers.legi import parse_legi_article

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "05-ia" / "golden-set.csv"
SEED = 42
SAMPLE_SIZE = 100
FIELDS = ("article_version_id", "texte", "notions_attendues", "annotateur", "date")


@dataclass(frozen=True)
class Candidate:
	article_version_id: str
	texte: str
	titre: str
	strate: str


def _xml_documents(source: Path) -> Iterator[tuple[str, bytes]]:
	if source.is_dir():
		for path in sorted(source.rglob("*.xml")):
			yield str(path), path.read_bytes()
	elif tarfile.is_tarfile(source):
		with tarfile.open(source, "r|*") as archive:
			for member in archive:
				if not member.isfile() or not member.name.lower().endswith(".xml"):
					continue
				if "/article/LEGI/ARTI/" not in f"/{member.name}":
					continue
				stream = archive.extractfile(member)
				if stream is None:
					raise ValueError(f"Impossible de lire {member.name} dans {source}")
				with stream:
					yield f"{source}!{member.name}", stream.read()
	elif source.is_file() and source.suffix.lower() == ".xml":
		yield str(source), source.read_bytes()
	else:
		raise ValueError(f"Source LEGI introuvable ou non prise en charge : {source}")


def _json_candidates(source: Path, livre: str, as_of: date) -> Iterator[Candidate]:
	"""Read a SocialGouv legi-data snapshot for the requested date."""
	document = json.loads(source.read_text(encoding="utf-8"))
	code = document["data"]
	if code["cid"] != DEFAULT_CODE_ID:
		raise ValueError("Le fichier JSON ne contient pas le Code du travail")
	if not (
		date.fromisoformat(code["dateDebutVersion"])
		<= as_of
		< date.fromisoformat(code["dateFinVersion"])
	):
		raise ValueError("La date demandée est hors de la période du snapshot JSON")
	target = _normalize_livre(livre)
	if target is None:
		raise ValueError("Livre invalide")

	def walk(
		node: dict[str, Any],
		in_book: bool = False,
		title: tuple[str, str] | None = None,
	) -> Iterator[Candidate]:
		data = node["data"]
		kind = node["type"]
		if kind == "section":
			label = " ".join(data["title"].split())
			if label.lower().startswith("livre "):
				in_book = _normalize_livre(label) == target
				title = None
			elif in_book and label.lower().startswith("titre "):
				title = (data["id"], label)
		if kind == "article" and in_book and title and data["etat"] == "VIGUEUR":
			start = datetime.fromtimestamp(data["dateDebut"] / 1000, UTC).date()
			end = datetime.fromtimestamp(data["dateFin"] / 1000, UTC).date()
			if start <= as_of < end:
				article_id = data["id"]
				text = " ".join(data["texte"].split())
				if not article_id or not text:
					raise ValueError("Article JSON sans identifiant ou texte")
				yield Candidate(article_id, text, title[1], title[0])
		for child in node.get("children", []):
			yield from walk(child, in_book, title)

	yield from walk(document)


def candidates(source: Path, livre: str, as_of: date) -> list[Candidate]:
	"""Read matching, active versions; reject inconsistent duplicate IDs."""
	if source.is_file() and source.suffix.lower() == ".json":
		articles = _json_candidates(source, livre, as_of)
	else:
		articles = _xml_candidates(source, livre, as_of)
	unique: dict[str, Candidate] = {}
	for candidate in articles:
		previous = unique.setdefault(candidate.article_version_id, candidate)
		if previous != candidate:
			raise ValueError(
				f"Versions contradictoires pour {candidate.article_version_id}"
			)
	return list(unique.values())


def _xml_candidates(source: Path, livre: str, as_of: date) -> Iterator[Candidate]:
	for path, document in _xml_documents(source):
		try:
			root = etree.parse(
				io.BytesIO(document),
				etree.XMLParser(
					load_dtd=False, no_network=True, resolve_entities=False
				),
			)
			if root.getroot().tag != "ARTICLE":
				continue
			code = root.find(".//CONTEXTE/TEXTE")
			state = root.findtext(".//META_ARTICLE/ETAT")
			if code is None or code.get("cid") != DEFAULT_CODE_ID or state != "VIGUEUR":
				continue
			with NamedTemporaryFile(suffix=".xml") as temporary:
				temporary.write(document)
				temporary.flush()
				article, version = parse_legi_article(temporary.name)
		except (etree.XMLSyntaxError, ValueError, ExtractionError) as error:
			raise ValueError(f"Document LEGI invalide : {path} : {error}") from error
		if not is_in_scope(article, livre=livre):
			continue
		if version.date_debut > as_of or (
			version.date_fin is not None and version.date_fin <= as_of
		):
			continue
		if not version.texte or not article.titre:
			raise ValueError(f"Texte ou titre manquant : {path}")
		sections = [
			element for element in root.findall(".//TITRE_TM")
			if " ".join("".join(element.itertext()).split()) == article.titre
			and element.get("debut")
			and date.fromisoformat(element.get("debut")) <= version.date_debut
			and (
				not element.get("fin")
				or date.fromisoformat(element.get("fin")) == date(2999, 1, 1)
				or version.date_debut < date.fromisoformat(element.get("fin"))
			)
		]
		section_id = sections[-1].get("id") if sections else None
		if not section_id:
			raise ValueError(f"Identifiant du titre manquant : {path}")
		yield Candidate(
			version.article_version_id, version.texte, article.titre, section_id
		)


def stratified_sample(
	articles: list[Candidate], *, size: int = SAMPLE_SIZE, seed: int = SEED
) -> list[Candidate]:
	"""Allocate proportionally by title, including each title when possible."""
	if size <= 0:
		raise ValueError("La taille de l'échantillon doit être positive")
	by_id: dict[str, Candidate] = {}
	for article in articles:
		previous = by_id.setdefault(article.article_version_id, article)
		if previous != article:
			raise ValueError(
				f"Identifiant contradictoire : {article.article_version_id}"
			)
	if len(by_id) < size:
		raise ValueError(f"Seulement {len(by_id)} articles éligibles ; {size} requis")
	groups: dict[str, list[Candidate]] = defaultdict(list)
	for article in by_id.values():
		groups[article.strate].append(article)
	if len(groups) > size:
		raise ValueError(f"{len(groups)} titres dépassent la taille de l'échantillon")

	# Allocate one per stratum, then proportionally to remaining capacity.
	titles = sorted(groups)
	remaining = size - len(titles)
	capacity = sum(len(groups[title]) - 1 for title in titles)
	quotas = {title: 1 for title in titles}
	remainders: list[tuple[int, str]] = []
	for title in titles:
		numerator = remaining * (len(groups[title]) - 1)
		extra, remainder = divmod(numerator, capacity) if capacity else (0, 0)
		quotas[title] += extra
		remainders.append((remainder, title))
	for _, title in sorted(remainders, key=lambda pair: (-pair[0], pair[1]))[
		: size - sum(quotas.values())
	]:
		quotas[title] += 1

	def rank(article: Candidate) -> bytes:
		return hashlib.sha256(f"{seed}:{article.article_version_id}".encode()).digest()

	return [
		article
		for title in titles
		for article in sorted(
			groups[title], key=lambda item: (rank(item), item.article_version_id)
		)[: quotas[title]]
	]


def write_csv(output: Path, articles: list[Candidate]) -> None:
	"""Create a CSV without overwriting existing annotations."""
	output.parent.mkdir(parents=True, exist_ok=True)
	with output.open("x", encoding="utf-8", newline="") as stream:
		writer = csv.DictWriter(stream, fieldnames=FIELDS)
		writer.writeheader()
		for article in articles:
			writer.writerow({
				"article_version_id": article.article_version_id,
				"texte": article.texte,
				"notions_attendues": "",
				"annotateur": "",
				"date": "",
			})


def write_titles(output: Path, articles: list[Candidate]) -> None:
	"""Persist the original title and text hash for each sampled article."""
	output.parent.mkdir(parents=True, exist_ok=True)
	with output.open("x", encoding="utf-8", newline="") as stream:
		writer = csv.DictWriter(
			stream, fieldnames=(
				"article_version_id", "titre_id", "titre", "texte_sha256"
			)
		)
		writer.writeheader()
		for article in articles:
			writer.writerow({
				"article_version_id": article.article_version_id,
				"titre_id": article.strate,
				"titre": article.titre,
				"texte_sha256": hashlib.sha256(
					article.texte.encode("utf-8")
				).hexdigest(),
			})


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--source", type=Path, required=True, help="Archive ou dossier LEGI."
	)
	parser.add_argument(
		"--livre", default="I", help="Livre du Code du travail (défaut : I)."
	)
	parser.add_argument(
		"--as-of", type=date.fromisoformat, default=date.today(),
		help="Date de validité ISO (défaut : aujourd'hui).",
	)
	parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
	parser.add_argument(
		"--titles-output", type=Path, help="Fichier CSV de correspondance des titres."
	)
	args = parser.parse_args()
	try:
		articles = candidates(args.source, args.livre, args.as_of)
		sample = stratified_sample(articles)
		if args.titles_output is not None and args.titles_output.exists():
			raise FileExistsError(f"Fichier déjà présent : {args.titles_output}")
		if args.titles_output == args.output:
			raise ValueError("Les fichiers de sortie doivent être différents")
		write_csv(args.output, sample)
		if args.titles_output is not None:
			write_titles(args.titles_output, sample)
	except (OSError, ValueError) as error:
		parser.exit(1, f"Erreur : {error}\n")
	print(f"{len(sample)} articles écrits dans {args.output} (date : {args.as_of}).")


if __name__ == "__main__":
	main()
