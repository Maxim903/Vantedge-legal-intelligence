"""Tests for immutable DataForSEO response archiving."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from vil_pipeline.archive import archive_dataforseo_response
from vil_pipeline.clients.dataforseo import SearchVolumeResponse
from vil_pipeline.clients.gcs import GCSClient
from vil_pipeline.keys import idempotency_key

ENDPOINT = "keywords_data/google_ads/search_volume/live"
FIXTURE = Path(__file__).parent / "fixtures" / "dataforseo" / (
	"search_volume_success.json"
)


def test_archive_writes_response_to_expected_path_with_metadata():
	response = SearchVolumeResponse.model_validate_json(
		FIXTURE.read_text(encoding="utf-8")
	)
	client = Mock(spec=GCSClient)
	archive_date = date(2026, 11, 15)
	key = idempotency_key(ENDPOINT, "buy laptop", 2840, "en", "2021-08")

	path = archive_dataforseo_response(
		client,
		response,
		endpoint=ENDPOINT,
		mot_cle="buy laptop",
		localisation=2840,
		langue="en",
		periode="2021-08",
		cout=Decimal("0.075"),
		date_archive=archive_date,
	)

	expected_path = f"dataforseo/{ENDPOINT}/2026/11/15/{key}.json"
	assert path == expected_path
	client.upload_json_immutable.assert_called_once_with(
		expected_path,
		response.model_dump(mode="json"),
		metadata={
			"date": "2026-11-15",
			"endpoint": ENDPOINT,
			"cost": "0.075",
		},
	)


def test_archive_normalizes_keyword_for_stable_path():
	response = SearchVolumeResponse.model_validate_json(
		FIXTURE.read_text(encoding="utf-8")
	)
	first_client = Mock(spec=GCSClient)
	second_client = Mock(spec=GCSClient)
	shared = {
		"endpoint": ENDPOINT,
		"localisation": 2840,
		"langue": "en",
		"periode": "2021-08",
		"cout": 0.075,
		"date_archive": date(2026, 11, 15),
	}

	first = archive_dataforseo_response(
		first_client, response, mot_cle="  Buy\tLaptop ", **shared
	)
	second = archive_dataforseo_response(
		second_client, response, mot_cle="buy laptop", **shared
	)

	assert first == second


@pytest.mark.parametrize("endpoint", ["", "/v3/../other", "v3//broken"])
def test_archive_rejects_invalid_endpoint_paths(endpoint):
	client = Mock(spec=GCSClient)
	response = SearchVolumeResponse.model_validate_json(
		FIXTURE.read_text(encoding="utf-8")
	)

	with pytest.raises(ValueError):
		archive_dataforseo_response(
			client,
			response,
			endpoint=endpoint,
			mot_cle="keyword",
			localisation=2840,
			langue="en",
			periode="2021-08",
			cout=0.075,
			date_archive=date(2026, 11, 15),
		)
	client.upload_json_immutable.assert_not_called()