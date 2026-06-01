"""Top-level Persona model — synthetic sections only (media/biometrics are separate)."""

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


class Persona(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    seed: int | None = None
    locale: str

    identity: Identity
    location: Location
    contact: Contact
    work: Work
    appearance: Appearance
    personality: Personality
    voice: Voice
    device: Device
    backstory: Backstory

    metadata: PersonaMetadata
