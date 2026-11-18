"""Load prompt templates and compute their content-based version."""

import hashlib
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str = "extraction_v1.md") -> tuple[str, str]:
	"""Return a prompt's UTF-8 text and its SHA-256 version hash."""
	prompt_path = PROMPTS_DIR / name
	if prompt_path.parent != PROMPTS_DIR:
		raise ValueError("Prompt name must refer to a file in the prompts directory")

	text = prompt_path.read_text(encoding="utf-8")
	version = hashlib.sha256(text.encode("utf-8")).hexdigest()
	return text, version
