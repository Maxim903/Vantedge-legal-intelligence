"""Google Cloud Storage client."""

import json
from collections.abc import Mapping
from typing import Any

from google.cloud import storage  # type: ignore[attr-defined]


class GCSClient:
	"""Thin wrapper around the Google Cloud Storage client."""

	def __init__(
		self,
		bucket_name: str,
		*,
		client: storage.Client | None = None,
	) -> None:
		self._bucket = (client if client is not None else storage.Client()).bucket(
			bucket_name,
		)

	def upload_json_immutable(
		self,
		blob_name: str,
		data: Any,
		*,
		metadata: Mapping[str, str] | None = None,
	) -> None:
		"""Upload JSON only if the object does not already exist."""
		blob = self._bucket.blob(blob_name)
		if metadata is not None:
			blob.metadata = dict(metadata)
		blob.upload_from_string(
			json.dumps(data),
			content_type="application/json",
			if_generation_match=0,
		)

	def exists(self, blob_name: str) -> bool:
		"""Return whether an object exists in the configured bucket."""
		return bool(self._bucket.blob(blob_name).exists())

	def list_blob_names(self, prefix: str) -> list[str]:
		"""List object names under a bucket prefix."""
		return [blob.name for blob in self._bucket.list_blobs(prefix=prefix)]

	def download_json(self, blob_name: str) -> Any:
		"""Download an object and decode its JSON content."""
		content = self._bucket.blob(blob_name).download_as_text()
		return json.loads(content)
