"""Tests for the Google Cloud Storage client."""

import json
from unittest.mock import Mock

import pytest
from google.cloud import storage

from vil_pipeline.clients.gcs import GCSClient


@pytest.fixture
def gcs_client():
	client = Mock(spec=storage.Client)
	bucket = Mock()
	client.bucket.return_value = bucket
	return GCSClient("test-bucket", client=client), client, bucket


def test_upload_json_immutable_creates_blob_with_generation_precondition(gcs_client):
	wrapper, client, bucket = gcs_client
	blob = Mock()
	bucket.blob.return_value = blob
	data = {"article_id": "LEGIARTI000000000001", "title": "Droit"}

	wrapper.upload_json_immutable("articles/one.json", data)

	client.bucket.assert_called_once_with("test-bucket")
	bucket.blob.assert_called_once_with("articles/one.json")
	blob.upload_from_string.assert_called_once_with(
		json.dumps(data),
		content_type="application/json",
		if_generation_match=0,
	)


def test_upload_json_immutable_propagates_existing_object_error(gcs_client):
	wrapper, _, bucket = gcs_client
	blob = Mock()
	bucket.blob.return_value = blob
	error = RuntimeError("object already exists")
	blob.upload_from_string.side_effect = error

	with pytest.raises(RuntimeError, match="object already exists"):
		wrapper.upload_json_immutable("articles/one.json", {"id": 1})


@pytest.mark.parametrize("found", [True, False])
def test_exists_returns_blob_existence(gcs_client, found):
	wrapper, _, bucket = gcs_client
	blob = Mock()
	blob.exists.return_value = found
	bucket.blob.return_value = blob

	assert wrapper.exists("articles/one.json") is found

	bucket.blob.assert_called_once_with("articles/one.json")
	blob.exists.assert_called_once_with()


def test_download_json_decodes_blob_content(gcs_client):
	wrapper, _, bucket = gcs_client
	blob = Mock()
	blob.download_as_text.return_value = '{"id": 1, "title": "Droit"}'
	bucket.blob.return_value = blob

	assert wrapper.download_json("articles/one.json") == {
		"id": 1,
		"title": "Droit",
	}

	bucket.blob.assert_called_once_with("articles/one.json")
	blob.download_as_text.assert_called_once_with()


def test_download_json_propagates_invalid_json(gcs_client):
	wrapper, _, bucket = gcs_client
	blob = Mock()
	blob.download_as_text.return_value = "{invalid"
	bucket.blob.return_value = blob

	with pytest.raises(json.JSONDecodeError):
		wrapper.download_json("articles/one.json")
