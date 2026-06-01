"""Standalone typed media with provenance. Binaries live on disk (file_path)."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from persona_genesis.schema.status import Status

ImageType = Literal["face", "full_body", "other", "unknown"]
AudioType = Literal["conversational", "voice_sample", "music", "other", "unknown"]
VideoType = Literal["clip", "avatar", "other", "unknown"]


class MediaOrigin(BaseModel):
    source: Literal["ai_generated", "caller_supplied"]
    provider: str | None = None
    model: str | None = None
    prompt: str | None = None
    generated_at: datetime | None = None

    @model_validator(mode="after")
    def _ai_requires_provenance(self) -> "MediaOrigin":
        if self.source == "ai_generated" and not (self.provider and self.model):
            raise ValueError("ai_generated media must record provider and model")
        return self


class Image(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_path: str
    media_type: str
    type: ImageType
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)
    width: int | None = None
    height: int | None = None
    description: str | None = None
    origin: MediaOrigin | None = None
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class Audio(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_path: str
    media_type: str
    type: AudioType
    text: str | None = None
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)
    sample_rate_hz: int | None = None
    duration_s: float | None = None
    origin: MediaOrigin | None = None
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class Video(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_path: str
    media_type: str
    type: VideoType
    text: str | None = None
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)
    width: int | None = None
    height: int | None = None
    duration_s: float | None = None
    fps: float | None = None
    description: str | None = None
    origin: MediaOrigin | None = None
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
