"""Directional persona<->persona relationship."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status

RelationshipType = Literal[
    "friend", "family", "partner", "coworker", "acquaintance", "other", "unknown"
]


class Relationship(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    person_1_id: UUID  # subject
    person_2_id: UUID  # object
    relationship: RelationshipType
    status: Status = "gen"
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
