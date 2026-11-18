"""Tests for prompt loading and versioning."""

import hashlib
import re
from pathlib import Path

import pytest

from prompts.loader import load_prompt
from vil_pipeline.extraction.validate import validate_extraction
from vil_pipeline.models.extraction import ResultatExtraction


def test_load_prompt_returns_text_and_sha256_version():
	text, version = load_prompt()

	assert "analyste du droit du travail français" in text
	assert "N'invente aucune notion" in text
	assert version == hashlib.sha256(text.encode("utf-8")).hexdigest()
	assert len(version) == 64


def test_extraction_prompt_includes_schema_fields_and_two_examples():
	text, _ = load_prompt()

	for field in (
		"article_version_id",
		"libelle",
		"definition_courte",
		"situations_de_vie",
		"confiance",
		"citation_article",
	):
		assert f'"{field}"' in text
	assert text.count("### Exemple ") == 2


def test_v1_format_and_examples_validate_against_extraction_model():
	text, _ = load_prompt()
	format_section = re.search(
		r"## Format de sortie.*?```json\n(.*?)\n```", text, flags=re.DOTALL
	)
	assert format_section is not None
	ResultatExtraction.model_validate_json(format_section.group(1))

	examples = re.split(r"^### Exemple \d+\s*$", text, flags=re.MULTILINE)[1:]
	assert len(examples) == 2
	for example in examples:
		article_match = re.search(
			r"Article :\s*> (.*?)\s*Sortie :", example, flags=re.DOTALL
		)
		json_match = re.search(r"```json\n(.*?)\n```", example, flags=re.DOTALL)
		assert article_match is not None
		assert json_match is not None
		article = " ".join(article_match.group(1).split())
		result = ResultatExtraction.model_validate_json(json_match.group(1))
		assert all(notion.citation_article in article for notion in result.notions)


def test_prompt_version_changes_with_content(tmp_path, monkeypatch):
	prompt = tmp_path / "prompt.md"
	prompt.write_text("Version un", encoding="utf-8")
	monkeypatch.setattr("prompts.loader.PROMPTS_DIR", tmp_path)
	first_text, first_version = load_prompt("prompt.md")

	prompt.write_text("Version deux", encoding="utf-8")
	second_text, second_version = load_prompt("prompt.md")

	assert first_text != second_text
	assert first_version != second_version


def test_load_prompt_reports_missing_file():
	with pytest.raises(FileNotFoundError):
		load_prompt("missing.md")


def test_load_prompt_rejects_paths_outside_prompt_directory(tmp_path):
	with pytest.raises(ValueError, match="prompts directory"):
		load_prompt(str(Path("..") / tmp_path / "outside.md"))


def test_v2_examples_match_the_article_id_and_exact_citations():
	text, version = load_prompt("extraction_v2.md")
	assert version == hashlib.sha256(text.encode("utf-8")).hexdigest()
	examples = re.split(r"^### ", text, flags=re.MULTILINE)[1:]
	assert len(examples) == 3
	for example in examples:
		id_match = re.search(r"Identifiant : `(LEGIARTI\d{12})`", example)
		article_match = re.search(r"Article : « (.*?) »", example, flags=re.DOTALL)
		json_match = re.search(r"```json\n(.*?)\n```", example, flags=re.DOTALL)
		assert id_match and article_match and json_match
		article = " ".join(article_match.group(1).split())
		result = validate_extraction(
			json_match.group(1), article, article_version_id=id_match.group(1)
		)
		assert result.article_version_id == id_match.group(1)
	assert validate_extraction(
		re.search(r"```json\n(.*?)\n```", examples[1], re.DOTALL).group(1),
		"Les modalités prévues à l'article L. 123-4 s'appliquent.",
	).notions == []
