"""DataForSEO tests with intercepted HTTP requests."""

import base64
import json
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx
from pydantic import SecretStr

from vil_pipeline.clients.dataforseo import DataForSEOClient

ENDPOINT = (
	"https://api.dataforseo.com/v3/keywords_data/"
	"google_ads/search_volume/live"
)
FIXTURE = Path(__file__).parents[1] / "fixtures" / "dataforseo" / (
	"search_volume_success.json"
)
SERP_ENDPOINT = (
	"https://api.dataforseo.com/v3/serp/google/organic/live/regular"
)
SERP_FIXTURE = Path(__file__).parents[1] / "fixtures" / "dataforseo" / (
	"serp_organic_success.json"
)


@respx.mock
def test_serp_organic_requests_depth_and_parses_organic_items():
	payload = json.loads(SERP_FIXTURE.read_text(encoding="utf-8"))
	route = respx.post(SERP_ENDPOINT).mock(
		return_value=httpx.Response(200, json=payload)
	)
	client = DataForSEOClient("test-login", "test-password")

	try:
		response = client.serp_organic(
			"droit du travail", location_code=2250, language_code="fr"
		)
	finally:
		client.close()

	request = route.calls[0].request
	assert request.headers["authorization"].startswith("Basic ")
	assert json.loads(request.content) == [{
		"keyword": "droit du travail",
		"location_code": 2250,
		"language_code": "fr",
		"depth": 10,
	}]
	items = response.tasks[0].result[0].items
	assert [item.type for item in items] == [
		"featured_snippet", "organic", "organic"
	]
	assert items[1].domain == "code.travail.gouv.fr"
	assert items[2].rank_group == 2


@respx.mock
def test_serp_organic_retries_rate_limits():
	payload = json.loads(SERP_FIXTURE.read_text(encoding="utf-8"))
	route = respx.post(SERP_ENDPOINT).mock(side_effect=[
		httpx.Response(429, json={"status_code": 42900}),
		httpx.Response(200, json=payload),
	])
	client = DataForSEOClient("test-login", "test-password", max_attempts=2)
	try:
		response = client.serp_organic(
			"droit du travail", location_code=2250, language_code="fr"
		)
	finally:
		client.close()

	assert route.call_count == 2
	assert response.tasks_count == 1


@pytest.mark.parametrize(
	"kwargs",
	[
		{"keyword": " ", "location_code": 2250, "language_code": "fr"},
		{"keyword": "k", "location_code": 0, "language_code": "fr"},
		{"keyword": "k", "location_code": 2250, "language_code": " "},
		{"keyword": "k", "location_code": 2250, "language_code": "fr", "depth": 0},
	],
)
def test_serp_organic_rejects_invalid_input(kwargs):
	client = DataForSEOClient("test-login", "test-password")
	try:
		with pytest.raises(ValueError):
			client.serp_organic(**kwargs)
	finally:
		client.close()


@respx.mock
def test_search_volume_uses_basic_auth_and_parses_recorded_response():
	payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
	route = respx.post(ENDPOINT).mock(
		return_value=httpx.Response(200, json=payload)
	)
	client = DataForSEOClient("test-login", SecretStr("test-password"), timeout=12.5)

	try:
		response = client.search_volume(
			["buy laptop"],
			location_code=2840,
			date_from=date(2021, 8, 1),
			search_partners=True,
		)
	finally:
		client.close()

	request = route.calls[0].request
	assert request.headers["authorization"] == "Basic " + base64.b64encode(
		b"test-login:test-password"
	).decode("ascii")
	assert request.url == ENDPOINT
	assert json.loads(request.content) == [{
		"location_code": 2840,
		"keywords": ["buy laptop"],
		"date_from": "2021-08-01",
		"search_partners": True,
	}]
	assert client.timeout == 12.5
	assert response.status_code == 20000
	assert response.tasks[0].result[0].search_volume == 2900
	assert response.tasks[0].result[0].cpc == 7.95
	assert response.tasks[0].result[0].monthly_searches[0].month == 10


@pytest.mark.parametrize(
	"failure",
	[
		httpx.Response(
			429, json={"status_code": 42900, "status_message": "Rate limit"}
		),
		httpx.ConnectError("network unavailable"),
	],
)
@respx.mock
def test_search_volume_retries_rate_limits_and_network_errors(failure):
	payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
	route = respx.post(ENDPOINT).mock(
		side_effect=[failure, httpx.Response(200, json=payload)]
	)
	client = DataForSEOClient(
		"test-login", "test-password", max_attempts=2
	)
	try:
		response = client.search_volume(["buy laptop"], location_code=2840)
	finally:
		client.close()

	assert route.call_count == 2
	assert response.tasks_count == 1


@respx.mock
def test_search_volume_does_not_retry_other_client_errors():
	route = respx.post(ENDPOINT).mock(
		return_value=httpx.Response(400, json={"error": "invalid request"})
	)
	client = DataForSEOClient("test-login", "private-password", max_attempts=3)
	try:
		with pytest.raises(httpx.HTTPStatusError) as error:
			client.search_volume(["buy laptop"], location_code=2840)
	finally:
		client.close()

	assert route.call_count == 1
	assert "private-password" not in str(error.value)


@pytest.mark.parametrize(
	"kwargs",
	[
		{"keywords": [], "location_code": 2840},
		{"keywords": ["  "], "location_code": 2840},
		{"keywords": ["keyword"], "location_code": 0},
	],
)
def test_search_volume_rejects_invalid_input(kwargs):
	client = DataForSEOClient("test-login", "test-password")
	try:
		with pytest.raises(ValueError):
			client.search_volume(**kwargs)
	finally:
		client.close()