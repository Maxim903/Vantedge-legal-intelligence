"""HTTP client for DataForSEO Google Ads search-volume requests."""

from collections.abc import Sequence
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

_SEARCH_VOLUME_URL = (
	"https://api.dataforseo.com/v3/keywords_data/"
	"google_ads/search_volume/live"
)
_SERP_ORGANIC_URL = (
	"https://api.dataforseo.com/v3/serp/google/organic/live/regular"
)


class DataForSEOModel(BaseModel):
	model_config = ConfigDict(extra="allow")


class MonthlySearch(DataForSEOModel):
	year: int
	month: int
	search_volume: int | None = None


class SearchVolumeResult(DataForSEOModel):
	keyword: str
	spell: str | None = None
	location_code: int | None = None
	language_code: str | None = None
	search_partners: bool | None = None
	competition: str | None = None
	competition_index: int | None = None
	search_volume: int | None = None
	low_top_of_page_bid: float | None = None
	high_top_of_page_bid: float | None = None
	cpc: float | None = None
	monthly_searches: list[MonthlySearch] | None = None


class SearchVolumeTask(DataForSEOModel):
	id: str | None = None
	status_code: int
	status_message: str
	time: str | None = None
	cost: float = 0
	result_count: int = 0
	path: list[str] = Field(default_factory=list)
	data: dict[str, Any] = Field(default_factory=dict)
	result: list[SearchVolumeResult] | None = None


class SearchVolumeResponse(DataForSEOModel):
	version: str
	status_code: int
	status_message: str
	time: str
	cost: float
	tasks_count: int
	tasks_error: int
	tasks: list[SearchVolumeTask]


class SerpItem(DataForSEOModel):
	type: str
	rank_group: int | None = None
	rank_absolute: int | None = None
	domain: str | None = None
	title: str | None = None
	url: str | None = None


class SerpResult(DataForSEOModel):
	keyword: str
	location_code: int | None = None
	language_code: str | None = None
	items_count: int | None = None
	items: list[SerpItem] = Field(default_factory=list)


class SerpTask(DataForSEOModel):
	id: str | None = None
	status_code: int
	status_message: str
	cost: float = 0
	result_count: int = 0
	result: list[SerpResult] | None = None


class SerpResponse(DataForSEOModel):
	version: str
	status_code: int
	status_message: str
	cost: float
	tasks_count: int
	tasks_error: int
	tasks: list[SerpTask]


def _is_retryable(error: BaseException) -> bool:
	if isinstance(error, httpx.TransportError):
		return True
	return isinstance(error, httpx.HTTPStatusError) and (
		error.response.status_code == 429 or error.response.status_code >= 500
	)


class DataForSEOClient:
	"""Fetch keyword volumes from the DataForSEO live endpoint."""

	def __init__(
		self,
		login: SecretStr | str,
		password: SecretStr | str,
		*,
		timeout: float = 30.0,
		max_attempts: int = 3,
	) -> None:
		username_value = (
			login.get_secret_value() if isinstance(login, SecretStr) else login
		)
		password_value = (
			password.get_secret_value()
			if isinstance(password, SecretStr)
			else password
		)
		if not username_value.strip() or not password_value.strip():
			raise ValueError("DataForSEO login and password must not be empty")
		if timeout <= 0:
			raise ValueError("timeout must be greater than zero")
		if max_attempts < 1:
			raise ValueError("max_attempts must be at least one")

		self.timeout = timeout
		self._client = httpx.Client(
			auth=httpx.BasicAuth(username_value, password_value),
			timeout=timeout,
		)
		self._retry = Retrying(
			retry=retry_if_exception(_is_retryable),
			stop=stop_after_attempt(max_attempts),
			wait=wait_exponential(multiplier=1, min=1, max=8),
			reraise=True,
		)

	def search_volume(
		self,
		keywords: Sequence[str],
		*,
		location_code: int,
		language_code: str | None = None,
		date_from: date | None = None,
		date_to: date | None = None,
		search_partners: bool = False,
	) -> SearchVolumeResponse:
		"""Request search volume and return the validated DataForSEO response."""
		if not keywords or any(not keyword.strip() for keyword in keywords):
			raise ValueError("At least one non-empty keyword is required")
		if location_code < 1:
			raise ValueError("location_code must be positive")
		if language_code is not None and not language_code.strip():
			raise ValueError("language_code must not be empty")
		if date_from is not None and date_to is not None and date_from > date_to:
			raise ValueError("date_from must not be after date_to")

		task: dict[str, object] = {
			"location_code": location_code,
			"keywords": list(keywords),
		}
		if language_code is not None:
			task["language_code"] = language_code
		if date_from is not None:
			task["date_from"] = date_from.isoformat()
		if date_to is not None:
			task["date_to"] = date_to.isoformat()
		if search_partners:
			task["search_partners"] = True

		response = self._retry(self._post, _SEARCH_VOLUME_URL, [task])
		return SearchVolumeResponse.model_validate(response)

	def serp_organic(
		self,
		keyword: str,
		*,
		location_code: int,
		language_code: str,
		depth: int = 10,
	) -> SerpResponse:
		"""Request the first ``depth`` organic Google results for one keyword."""
		if not keyword.strip():
			raise ValueError("keyword must not be empty")
		if location_code < 1:
			raise ValueError("location_code must be positive")
		if not language_code.strip():
			raise ValueError("language_code must not be empty")
		if depth < 1:
			raise ValueError("depth must be positive")

		task: dict[str, object] = {
			"keyword": keyword,
			"location_code": location_code,
			"language_code": language_code,
			"depth": depth,
		}
		response = self._retry(self._post, _SERP_ORGANIC_URL, [task])
		return SerpResponse.model_validate(response)

	def _post(self, url: str, payload: list[dict[str, object]]) -> dict[str, Any]:
		response = self._client.post(url, json=payload)
		response.raise_for_status()
		body = response.json()
		if not isinstance(body, dict):
			raise ValueError("DataForSEO returned a non-object response")
		return body

	def close(self) -> None:
		"""Close the underlying HTTP connection pool."""
		self._client.close()

	def __enter__(self) -> "DataForSEOClient":
		return self

	def __exit__(self, *_: object) -> None:
		self.close()