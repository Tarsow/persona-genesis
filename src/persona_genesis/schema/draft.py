"""PersonaDraft — the builder's output bundle: a partial persona plus the related
entities and link intents to be persisted together by repository.save_draft."""

from uuid import UUID

from pydantic import BaseModel, Field

from persona_genesis.schema.account import Account
from persona_genesis.schema.biometrics import Body, Face, VoicePrint
from persona_genesis.schema.document import Document
from persona_genesis.schema.media import Audio, Image, Video
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.relationship import Relationship


class PersonaDraft(BaseModel):
    persona: PartialPersona
    faces: list[Face] = Field(default_factory=list)
    bodies: list[Body] = Field(default_factory=list)
    voices: list[VoicePrint] = Field(default_factory=list)
    images: list[Image] = Field(default_factory=list)
    audio: list[Audio] = Field(default_factory=list)
    video: list[Video] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)
    accounts: list[Account] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    image_face_links: list[tuple[UUID, UUID]] = Field(default_factory=list)  # (image_id, face_id)
    audio_voice_links: list[tuple[UUID, UUID]] = Field(default_factory=list)  # (audio_id, voice_id)
    # tuple order: (document_id, persona_id)
    document_persona_links: list[tuple[UUID, UUID]] = Field(default_factory=list)
