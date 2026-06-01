"""RAG document: content + metadata + embedding. Linked M:N to personas in the DB."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status


class Document(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None
    status: Status = "real"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
