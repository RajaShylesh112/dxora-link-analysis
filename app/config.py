from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    openrouter_api_key: SecretStr = SecretStr("")
    openrouter_model: str = "openrouter/free"
    openrouter_fallback_model: str = ""
    llm_strict_schema: bool = True
    analysis_api_key: SecretStr = SecretStr("")
    fetch_timeout_seconds: float = Field(default=12, ge=1, le=30)
    llm_timeout_seconds: float = Field(default=60, ge=5, le=120)
    cache_ttl_seconds: int = Field(default=900, ge=0, le=86400)
    cache_max_entries: int = Field(default=64, ge=1, le=256)
    max_pages: int = Field(default=3, ge=1, le=5)
    max_html_bytes: int = Field(default=1_500_000, ge=1000, le=3_000_000)
    max_content_chars: int = Field(default=22_000, ge=1000, le=40_000)
    requests_per_minute: int = Field(default=6, ge=1, le=60)
    max_concurrent_analyses: int = Field(default=2, ge=1, le=8)

    @field_validator("openrouter_model", "openrouter_fallback_model")
    @classmethod
    def only_free_models(cls, value: str, info: ValidationInfo) -> str:
        if info.field_name == "openrouter_model" and not value:
            raise ValueError("A primary free model is required")
        if value and value != "openrouter/free" and not value.endswith(":free"):
            raise ValueError("Only openrouter/free or explicit :free model IDs are supported")
        return value
