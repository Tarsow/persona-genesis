"""Biometric embedding models. Embeddings are list[float] in the contract;
the DB layer maps them to pgvector vector(N)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status


class Face(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID | None = None  # 0..1 persona
    embedding: list[float]
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class Body(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID
    embedding: list[float]
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class VoicePrint(BaseModel):
    """Biometric speaker embedding (named VoicePrint to avoid clashing with the
    text-section schema.voice.Voice)."""

    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID
    embedding: list[float]
    label: str | None = None  # optional tone descriptor
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
