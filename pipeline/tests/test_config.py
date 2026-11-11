"""Tests for pipeline configuration."""

import pytest
from pydantic import ValidationError

from vil_pipeline.config import Settings

ENVIRONMENT = {
	"GCP_PROJECT_ID": "test-project",
	"BQ_LOCATION": "EU",
	"GCS_BUCKET_RAW": "raw-bucket",
	"DATAFORSEO_LOGIN": "test-login",
	"DATAFORSEO_PASSWORD": "test-dataforseo-password",
	"LLM_API_KEY": "test-llm-key",
	"NEO4J_URI": "neo4j+s://example.databases.neo4j.io",
	"NEO4J_USER": "neo4j",
	"NEO4J_PASSWORD": "test-neo4j-password",
	"NEXT_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
	"NEXT_PUBLIC_SUPABASE_ANON_KEY": "test-anon-key",
	"SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
	"STRIPE_SECRET_KEY": "test-stripe-secret-key",
	"STRIPE_WEBHOOK_SECRET": "test-stripe-webhook-secret",
}

SECRET_FIELDS = (
	("DATAFORSEO_PASSWORD", "dataforseo_password"),
	("LLM_API_KEY", "llm_api_key"),
	("NEO4J_PASSWORD", "neo4j_password"),
	("SUPABASE_SERVICE_ROLE_KEY", "supabase_service_role_key"),
	("STRIPE_SECRET_KEY", "stripe_secret_key"),
	("STRIPE_WEBHOOK_SECRET", "stripe_webhook_secret"),
)


def set_environment(monkeypatch, missing=()):
	for name in ENVIRONMENT:
		monkeypatch.delenv(name, raising=False)
	for name, value in ENVIRONMENT.items():
		if name not in missing:
			monkeypatch.setenv(name, value)


def test_settings_reads_environment_variables(monkeypatch):
	set_environment(monkeypatch)

	settings = Settings(_env_file=None)

	assert settings.gcp_project_id == ENVIRONMENT["GCP_PROJECT_ID"]
	assert settings.bq_location == ENVIRONMENT["BQ_LOCATION"]
	assert settings.gcs_bucket_raw == ENVIRONMENT["GCS_BUCKET_RAW"]
	assert settings.dataforseo_login == ENVIRONMENT["DATAFORSEO_LOGIN"]
	assert settings.dataforseo_password.get_secret_value() == ENVIRONMENT[
		"DATAFORSEO_PASSWORD"
	]
	assert settings.llm_api_key.get_secret_value() == ENVIRONMENT["LLM_API_KEY"]
	assert settings.neo4j_uri == ENVIRONMENT["NEO4J_URI"]
	assert settings.neo4j_user == ENVIRONMENT["NEO4J_USER"]
	assert settings.neo4j_password.get_secret_value() == ENVIRONMENT["NEO4J_PASSWORD"]
	assert settings.next_public_supabase_url == ENVIRONMENT["NEXT_PUBLIC_SUPABASE_URL"]
	assert settings.next_public_supabase_anon_key == ENVIRONMENT[
		"NEXT_PUBLIC_SUPABASE_ANON_KEY"
	]
	assert settings.supabase_service_role_key.get_secret_value() == ENVIRONMENT[
		"SUPABASE_SERVICE_ROLE_KEY"
	]
	assert settings.stripe_secret_key.get_secret_value() == ENVIRONMENT[
		"STRIPE_SECRET_KEY"
	]
	assert settings.stripe_webhook_secret.get_secret_value() == ENVIRONMENT[
		"STRIPE_WEBHOOK_SECRET"
	]


def test_settings_reports_missing_required_variable(monkeypatch):
	set_environment(monkeypatch, missing={"GCP_PROJECT_ID"})

	with pytest.raises(ValidationError) as error:
		Settings(_env_file=None)

	assert "gcp_project_id" in str(error.value)


def test_settings_rejects_empty_required_variable(monkeypatch):
	set_environment(monkeypatch)
	monkeypatch.setenv("GCP_PROJECT_ID", " ")

	with pytest.raises(ValidationError) as error:
		Settings(_env_file=None)

	assert "gcp_project_id" in str(error.value)
	assert "must not be empty" in str(error.value)


@pytest.mark.parametrize(("env_name", "field_name"), SECRET_FIELDS)
def test_secret_settings_have_no_default(monkeypatch, env_name, field_name):
	set_environment(monkeypatch, missing={env_name})

	with pytest.raises(ValidationError) as error:
		Settings(_env_file=None)

	assert field_name in str(error.value)
