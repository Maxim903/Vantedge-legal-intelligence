"""Pipeline configuration."""

from pathlib import Path
from typing import Any

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DATAFORSEO_TTL_JOURS: dict[str, int] = {
	"keywords_data/google_ads/search_volume/live": 30,
	"serp/google/organic/live/regular": 30,
}


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=Path(__file__).resolve().parents[3] / ".env",
		env_file_encoding="utf-8",
		env_ignore_empty=True,
		extra="ignore",
	)

	gcp_project_id: str
	bq_location: str
	gcs_bucket_raw: str
	dataforseo_login: str
	dataforseo_password: SecretStr
	llm_api_key: SecretStr
	neo4j_uri: str
	neo4j_user: str
	neo4j_password: SecretStr
	next_public_supabase_url: str
	next_public_supabase_anon_key: str
	supabase_service_role_key: SecretStr
	stripe_secret_key: SecretStr
	stripe_webhook_secret: SecretStr

	@field_validator("*", mode="before")
	@classmethod
	def reject_blank_values(cls, value: Any) -> Any:
		if isinstance(value, str) and not value.strip():
			raise ValueError("must not be empty")
		return value
