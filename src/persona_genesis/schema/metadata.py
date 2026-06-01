"""PersonaMetadata: provenance for a generated persona."""

from datetime import datetime

from pydantic import BaseModel, Field


class PersonaMetadata(BaseModel):
    generated_at: datetime
    generator_version: str
    provider_versions: dict[str, str] = Field(default_factory=dict)
