"""PartialPersona — all-optional, in-progress mirror of Persona (sections only)."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from persona_genesis.schema.appearance import Appearance
from persona_genesis.schema.backstory import Backstory
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.device import Device
from persona_genesis.schema.identity import Identity
from persona_genesis.schema.location import Location
from persona_genesis.schema.metadata import PersonaMetadata
from persona_genesis.schema.personality import Personality
from persona_genesis.schema.voice import Voice
from persona_genesis.schema.work import Work


class PartialPersona(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    seed: int | None = None
    locale: str | None = None
    identity: Identity | None = None
    location: Location | None = None
    contact: Contact | None = None
    work: Work | None = None
    appearance: Appearance | None = None
    personality: Personality | None = None
    voice: Voice | None = None
    device: Device | None = None
    backstory: Backstory | None = None
    metadata: PersonaMetadata | None = None
