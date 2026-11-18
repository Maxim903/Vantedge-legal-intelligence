"""Deterministic idempotency keys for external API requests."""

import hashlib
import json
import unicodedata
from datetime import date


def idempotency_key(
	endpoint: str,
	mot_cle: str,
	localisation: str | int,
	langue: str,
	periode: str | date,
) -> str:
	"""Hash stable request dimensions, ignoring keyword case and whitespace."""
	keyword = unicodedata.normalize(
		"NFC", " ".join(mot_cle.casefold().split())
	)
	period = periode.isoformat() if isinstance(periode, date) else periode
	canonical_request = json.dumps(
		[endpoint, keyword, str(localisation), langue, period],
		ensure_ascii=False,
		separators=(",", ":"),
	)
	return hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()