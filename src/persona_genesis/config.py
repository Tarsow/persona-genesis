"""Configuration models. Config is injected as a nested dict; the library never
reads environment variables or files itself."""

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from persona_genesis.exceptions import ConfigError

LLMProviderName = Literal["anthropic", "openai", "openai_compat", "deepseek"]
ImageProviderName = Literal["fal", "replicate", "openai", "diffusers_local"]


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: LLMProviderName = "deepseek"
    api_key: str | None = None
    model: str = "deepseek-chat"
    base_url: str | None = None  # only used by openai_compat
    timeout_s: int = 60
    max_retries: int = 2


class ImageConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: ImageProviderName = "fal"
    api_key: str | None = None
    model: str = "fal-ai/flux/schnell"
    timeout_s: int = 120


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    llm: LLMConfig = Field(default_factory=LLMConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    default_locale: str = "en_US"
    log_level: str = "INFO"
    database_url: str | None = None
    vault_key: str | bytes | None = None
    media_dir: str = "/srv/persona-genesis/media/"
    face_embedding_dim: int = 512
    body_embedding_dim: int = 2048
    voice_embedding_dim: int = 192
    document_embedding_dim: int = 1536
    geoip_database_path: str | None = None  # path to a caller-provided GeoLite2-City.mmdb

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Config":
        """Validate an injected nested config dict into a Config.

        Known keys are read; unknown keys (top-level and nested) are ignored.
        Building this dict — from .env, a secrets manager, literals, etc. — is the
        caller's responsibility and is not enforced by the library.
        """
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise ConfigError(f"Invalid persona-genesis configuration: {exc}") from exc
