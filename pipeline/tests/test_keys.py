"""Tests for deterministic API idempotency keys."""

import re

from vil_pipeline.keys import idempotency_key


def test_idempotency_key_is_a_stable_sha256_digest():
	arguments = (
		"google_ads/search_volume",
		"droit du travail",
		2250,
		"fr",
		"2026-11",
	)

	key = idempotency_key(*arguments)

	assert key == idempotency_key(*arguments)
	assert re.fullmatch(r"[0-9a-f]{64}", key)


def test_idempotency_key_ignores_keyword_case_and_whitespace():
	first = idempotency_key(
		"google_ads/search_volume", "  Droit\tdu   Travail ", 2250, "fr", "2026-11"
	)
	second = idempotency_key(
		"google_ads/search_volume", "droit du travail", 2250, "fr", "2026-11"
	)

	assert first == second


def test_idempotency_key_changes_when_request_dimensions_change():
	base = idempotency_key("endpoint", "mot clé", 2250, "fr", "2026-11")

	assert idempotency_key("endpoint", "mot clé", 2251, "fr", "2026-11") != base
	assert idempotency_key("endpoint", "mot clé", 2250, "en", "2026-11") != base
	assert idempotency_key("endpoint", "mot clé", 2250, "fr", "2026-12") != base