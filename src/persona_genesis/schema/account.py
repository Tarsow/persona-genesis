"""Account vault entry. Secrets plaintext in-memory; encrypted at the DB boundary."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Account(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID
    url: str
    login: str
    password: str
    session_token: str | None = None
    notes: str | None = None
    date_created: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    date_updated: datetime | None = None
