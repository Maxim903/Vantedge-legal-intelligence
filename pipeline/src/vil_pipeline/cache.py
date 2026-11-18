"""Freshness checks for immutable DataForSEO objects in GCS."""

from datetime import UTC, date, datetime
from pathlib import PurePosixPath

from vil_pipeline.clients.gcs import GCSClient


def _archive_date(cle: str) -> date:
	parts = PurePosixPath(cle).parts
	if (
		len(parts) < 6
		or parts[0] != "dataforseo"
		or not parts[-1].endswith(".json")
	):
		raise ValueError("Invalid DataForSEO archive key")

	try:
		return date(int(parts[-4]), int(parts[-3]), int(parts[-2]))
	except ValueError as error:
		raise ValueError("Invalid date in DataForSEO archive key") from error


def is_fresh(
	cle: str,
	ttl_jours: int,
	*,
	client: GCSClient,
	today: date | None = None,
) -> bool:
	"""Return whether an archived object exists and is younger than its TTL.

	``cle`` is the full object path returned by ``archive_dataforseo_response``.
	"""
	if ttl_jours <= 0:
		raise ValueError("ttl_jours must be greater than zero")
	archived_on = _archive_date(cle)
	if not client.exists(cle):
		return False
	current_date = today or datetime.now(UTC).date()
	age_days = (current_date - archived_on).days
	return 0 <= age_days < ttl_jours


def list_fresh_archive_blobs(
	endpoint: str,
	ttl_jours: int,
	*,
	client: GCSClient,
	today: date | None = None,
) -> list[str]:
	"""List fresh archived object names for one endpoint, oldest first."""
	normalized_endpoint = endpoint.strip("/")
	segments = normalized_endpoint.split("/")
	invalid_segment = any(segment in {"", ".", ".."} for segment in segments)
	if not normalized_endpoint or invalid_segment:
		raise ValueError("Invalid DataForSEO endpoint")
	if ttl_jours <= 0:
		raise ValueError("ttl_jours must be greater than zero")

	current_date = today or datetime.now(UTC).date()
	prefix = f"dataforseo/{normalized_endpoint}/"
	fresh: list[str] = []
	for blob_name in client.list_blob_names(prefix=prefix):
		if not blob_name.startswith(prefix) or not blob_name.endswith(".json"):
			continue
		try:
			archived_on = _archive_date(blob_name)
		except ValueError:
			continue
		age_days = (current_date - archived_on).days
		if 0 <= age_days < ttl_jours:
			fresh.append(blob_name)
	return sorted(fresh)


def find_fresh_archive_keys(
	endpoint: str,
	ttl_jours: int,
	*,
	client: GCSClient,
	today: date | None = None,
) -> set[str]:
	"""List fresh archived request keys for one endpoint with a single GCS list."""
	blobs = list_fresh_archive_blobs(
		endpoint, ttl_jours, client=client, today=today
	)
	return {PurePosixPath(blob_name).stem for blob_name in blobs}