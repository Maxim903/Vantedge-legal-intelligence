"""Streaming parser for DILA LEGI article XML files."""

import re
from datetime import date
from pathlib import Path
from typing import Literal

from lxml import etree  # type: ignore[import-untyped]
from pydantic import ValidationError

from vil_pipeline.errors import ExtractionError
from vil_pipeline.models.corpus import Article, ArticleVersion

_OPEN_END_DATE = date(2999, 1, 1)
_SECTION_PATTERN = re.compile(r"^(Livre|Titre|Chapitre)\b", re.IGNORECASE)
_VALID_STATES: dict[str, Literal["VIGUEUR", "MODIFIE", "ABROGE"]] = {
	"VIGUEUR": "VIGUEUR",
	"MODIFIE": "MODIFIE",
	"ABROGE": "ABROGE",
}


def _local_name(element: etree._Element) -> str:
	return str(etree.QName(element).localname)


def _date(value: str | None, *, open_end: bool = False) -> date | None:
	if not value:
		return None
	parsed = date.fromisoformat(value.strip())
	if open_end and parsed == _OPEN_END_DATE:
		return None
	return parsed


def _plain_text(element: etree._Element) -> str:
	return " ".join("".join(element.itertext()).split())


def _is_text_content_descendant(element: etree._Element) -> bool:
	ancestor = element.getparent()
	in_content = False
	while ancestor is not None:
		tag = _local_name(ancestor)
		if tag == "CONTENU":
			in_content = True
		elif tag == "BLOC_TEXTUEL":
			return in_content
		ancestor = ancestor.getparent()
	return False


def parse_legi_article(path: str | Path) -> tuple[Article, ArticleVersion]:
	"""Parse one LEGI article XML file into its article and version models."""
	source = Path(path)
	article_id: str | None = None
	numero: str | None = None
	code_id: str | None = None
	state: Literal["VIGUEUR", "MODIFIE", "ABROGE"] | None = None
	start_date: date | None = None
	end_date: date | None = None
	text_parts: list[str] = []
	sections: dict[str, list[tuple[str, date | None, date | None]]] = {
		"Livre": [],
		"Titre": [],
		"Chapitre": [],
	}

	try:
		context = etree.iterparse(
			str(source),
			events=("start", "end"),
			load_dtd=False,
			no_network=True,
			resolve_entities=False,
			recover=False,
		)
		for event, element in context:
			tag = _local_name(element)
			if event == "start":
				if tag == "TEXTE":
					code_id = element.get("cid")
				continue

			parent = element.getparent()
			parent_tag = _local_name(parent) if parent is not None else ""
			if parent_tag == "META_COMMUN" and tag == "ID":
				article_id = _plain_text(element)
			elif parent_tag == "META_ARTICLE":
				value = _plain_text(element)
				if tag == "NUM":
					numero = value
				elif tag == "ETAT":
					state = _VALID_STATES.get(value)
					if state is None:
						raise ValueError(f"unsupported article state: {value}")
				elif tag == "DATE_DEBUT":
					start_date = _date(value)
				elif tag == "DATE_FIN":
					end_date = _date(value, open_end=True)
			elif tag == "TITRE_TM":
				label = _plain_text(element)
				match = _SECTION_PATTERN.match(label)
				if match:
					kind = match.group(1).capitalize()
					begin = _date(element.get("debut"))
					end = _date(element.get("fin"), open_end=True)
					sections[kind].append((label, begin, end))
			elif tag == "CONTENU" and parent_tag == "BLOC_TEXTUEL":
				text = _plain_text(element)
				if text:
					text_parts.append(text)

			if _is_text_content_descendant(element) and tag != "CONTENU":
				continue
			element.clear()
			if parent is not None:
				while element.getprevious() is not None:
					del parent[0]

		if (
			not article_id
			or not numero
			or not code_id
			or not state
			or start_date is None
		):
			raise ValueError("missing required article metadata")

		def effective_section(kind: str) -> str:
			for label, begin, end in reversed(sections[kind]):
				if begin is not None and begin <= start_date and (
					end is None or start_date < end
				):
					return label
			raise ValueError(f"missing effective {kind.lower()} metadata")

		article = Article(
			article_id=article_id,
			numero=numero,
			code_id=code_id,
			livre=effective_section("Livre"),
			titre=effective_section("Titre"),
			chapitre=effective_section("Chapitre"),
		)
		version = ArticleVersion(
			article_version_id=article_id,
			article_id=article_id,
			texte=" ".join(text_parts),
			etat=state,
			date_debut=start_date,
			date_fin=end_date,
		)
		return article, version
	except (OSError, etree.XMLSyntaxError, ValueError, ValidationError) as exc:
		raise ExtractionError(f"Unable to parse LEGI XML {source}: {exc}") from exc
