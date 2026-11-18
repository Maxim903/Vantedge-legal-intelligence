"""Tests for the DataForSEO GCS cache freshness check."""

from datetime import date
from unittest.mock import Mock

import pytest

from vil_pipeline.cache import find_fresh_archive_keys, is_fresh
from vil_pipeline.clients.gcs import GCSClient
from vil_pipeline.config import DATAFORSEO_TTL_JOURS


def _key(archived_on: str) -> str:
	year, month, day = archived_on.split("-")
	return (
		"dataforseo/keywords_data/google_ads/search_volume/live/"
		f"{year}/{month}/{day}/request-key.json"
	)


def test_is_fresh_checks_gcs_and_accepts_object_within_ttl():
	client = Mock(spec=GCSClient)
	client.exists.return_value = True

	assert is_fresh(
		_key("2026-11-01"), 30, client=client, today=date(2026, 11, 15)
	)
	client.exists.assert_called_once_with(_key("2026-11-01"))


def test_is_fresh_returns_false_when_object_is_missing():
	client = Mock(spec=GCSClient)
	client.exists.return_value = False

	assert not is_fresh(
		_key("2026-11-15"), 30, client=client, today=date(2026, 11, 15)
	)
	client.exists.assert_called_once()


def test_is_fresh_returns_false_after_ttl_expiration():
	client = Mock(spec=GCSClient)
	client.exists.return_value = True

	assert not is_fresh(
		_key("2026-10-16"), 30, client=client, today=date(2026, 11, 15)
	)


def test_volume_endpoint_has_thirty_day_ttl():
	assert DATAFORSEO_TTL_JOURS[
		"keywords_data/google_ads/search_volume/live"
	] == 30


def test_find_fresh_archive_keys_lists_endpoint_once_and_filters_ttl():
	client = Mock(spec=GCSClient)
	fresh_key = "a" * 64
	old_key = "b" * 64
	client.list_blob_names.return_value = [
		f"dataforseo/volumes/2026/11/01/{fresh_key}.json",
		f"dataforseo/volumes/2026/10/01/{old_key}.json",
		f"dataforseo/another/2026/11/10/{'c' * 64}.json",
	]

	assert find_fresh_archive_keys(
		"volumes", 30, client=client, today=date(2026, 11, 15)
	) == {fresh_key}
	client.list_blob_names.assert_called_once_with(prefix="dataforseo/volumes/")


@pytest.mark.parametrize("ttl_jours", [-1, 0])
def test_is_fresh_rejects_non_positive_ttl(ttl_jours):
	client = Mock(spec=GCSClient)

	with pytest.raises(ValueError, match="ttl_jours"):
		is_fresh(_key("2026-11-15"), ttl_jours, client=client)
	client.exists.assert_not_called()


def test_is_fresh_rejects_invalid_archive_path():
	client = Mock(spec=GCSClient)

	with pytest.raises(ValueError, match="archive key"):
		is_fresh("dataforseo/endpoint/not-a-date/key.json", 30, client=client)
	client.exists.assert_not_called()