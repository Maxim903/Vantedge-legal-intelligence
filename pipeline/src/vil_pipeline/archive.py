"""Archive immutable DataForSEO responses in Google Cloud Storage."""

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from vil_pipeline.clients.dataforseo import SearchVolumeResponse, SerpResponse
from vil_pipeline.clients.gcs import GCSClient
from vil_pipeline.keys import idempotency_key


def archive_dataforseo_response(
	client: GCSClient,
	response: SearchVolumeResponse | SerpResponse,
	*,
	endpoint: str,
	mot_cle: str,
	localisation: str | int,
	langue: str,
	periode: str | date,
	cout: Decimal | float | int,
	date_archive: date | None = None,
) -> str:
	"""Write a response to an immutable dated object and return its GCS path."""
	normalized_endpoint = endpoint.strip("/")
	segments = normalized_endpoint.split("/")
	invalid_segment = any(segment in {"", ".", ".."} for segment in segments)
	if not normalized_endpoint or invalid_segment:
		raise ValueError(
			"endpoint must be a relative path without empty or parent segments"
		)
	if not mot_cle.strip() or not langue.strip():
		raise ValueError("mot_cle and langue must not be empty")
	if isinstance(localisation, int) and localisation <= 0:
		raise ValueError("localisation must be positive")
	if isinstance(localisation, str) and not localisation.strip():
		raise ValueError("localisation must not be empty")
	if isinstance(periode, str) and not periode.strip():
		raise ValueError("periode must not be empty")

	try:
		cost = Decimal(str(cout))
	except InvalidOperation as error:
		raise ValueError("cout must be a finite non-negative number") from error
	if not cost.is_finite() or cost < 0:
		raise ValueError("cout must be a finite non-negative number")

	archived_on = date_archive or datetime.now(UTC).date()
	key = idempotency_key(
		normalized_endpoint, mot_cle, localisation, langue, periode
	)
	blob_name = (
		f"dataforseo/{normalized_endpoint}/{archived_on:%Y/%m/%d}/{key}.json"
	)
	client.upload_json_immutable(
		blob_name,
		response.model_dump(mode="json", exclude_unset=True),
		metadata={
			"date": archived_on.isoformat(),
			"endpoint": normalized_endpoint,
			"cost": format(cost, "f"),
		},
	)
	return blob_name