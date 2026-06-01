"""SQLAlchemy 2.0 ORM built by a factory so pgvector dims come from Config.

Synthetic persona sections are stored as JSONB; faces/bodies/voices/documents carry
pgvector vector(N) embeddings; images/audio/video are standalone; junction tables link
image<->face, audio<->voice, document<->persona. Binaries never enter the DB.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


@dataclass(frozen=True)
class EmbeddingDims:
    face: int
    body: int
    voice: int
    document: int


@dataclass
class ModelRegistry:
    base: type[DeclarativeBase]
    PersonaRow: type[Any]
    FaceRow: type[Any]
    BodyRow: type[Any]
    VoiceRow: type[Any]
    ImageRow: type[Any]
    AudioRow: type[Any]
    VideoRow: type[Any]
    DocumentRow: type[Any]
    RelationshipRow: type[Any]
    AccountRow: type[Any]
    image_faces: Table
    audio_voices: Table
    document_personas: Table


def build_models(dims: EmbeddingDims) -> ModelRegistry:
    class Base(DeclarativeBase):
        pass

    class PersonaRow(Base):
        __tablename__ = "personas"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
        locale: Mapped[str | None] = mapped_column(String, nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
        updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
        identity: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        location: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        contact: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        work: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        appearance: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        personality: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        voice: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        device: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        backstory: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    class FaceRow(Base):
        __tablename__ = "faces"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        persona_id: Mapped[UUID | None] = mapped_column(
            ForeignKey("personas.id"), index=True, nullable=True
        )
        embedding = mapped_column(Vector(dims.face))
        status: Mapped[str] = mapped_column(String)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    class BodyRow(Base):
        __tablename__ = "bodies"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        persona_id: Mapped[UUID] = mapped_column(
            ForeignKey("personas.id"), index=True, nullable=False
        )
        embedding = mapped_column(Vector(dims.body))
        status: Mapped[str] = mapped_column(String)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    class VoiceRow(Base):
        __tablename__ = "voices"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        persona_id: Mapped[UUID] = mapped_column(
            ForeignKey("personas.id"), index=True, nullable=False
        )
        embedding = mapped_column(Vector(dims.voice))
        label: Mapped[str | None] = mapped_column(String, nullable=True)
        status: Mapped[str] = mapped_column(String)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    class ImageRow(Base):
        __tablename__ = "images"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        file_path: Mapped[str] = mapped_column(String)
        media_type: Mapped[str] = mapped_column(String)
        type: Mapped[str] = mapped_column(String)
        nsfw: Mapped[float] = mapped_column(Float, default=0.0)
        width: Mapped[int | None] = mapped_column(Integer, nullable=True)
        height: Mapped[int | None] = mapped_column(Integer, nullable=True)
        description: Mapped[str | None] = mapped_column(Text, nullable=True)
        origin: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        status: Mapped[str] = mapped_column(String)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    class AudioRow(Base):
        __tablename__ = "audio"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        file_path: Mapped[str] = mapped_column(String)
        media_type: Mapped[str] = mapped_column(String)
        type: Mapped[str] = mapped_column(String)
        text: Mapped[str | None] = mapped_column(Text, nullable=True)
        nsfw: Mapped[float] = mapped_column(Float, default=0.0)
        sample_rate_hz: Mapped[int | None] = mapped_column(Integer, nullable=True)
        duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
        origin: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        status: Mapped[str] = mapped_column(String)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    class VideoRow(Base):
        __tablename__ = "video"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        file_path: Mapped[str] = mapped_column(String)
        media_type: Mapped[str] = mapped_column(String)
        type: Mapped[str] = mapped_column(String)
        text: Mapped[str | None] = mapped_column(Text, nullable=True)
        nsfw: Mapped[float] = mapped_column(Float, default=0.0)
        width: Mapped[int | None] = mapped_column(Integer, nullable=True)
        height: Mapped[int | None] = mapped_column(Integer, nullable=True)
        duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
        fps: Mapped[float | None] = mapped_column(Float, nullable=True)
        description: Mapped[str | None] = mapped_column(Text, nullable=True)
        origin: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
        status: Mapped[str] = mapped_column(String)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    class DocumentRow(Base):
        __tablename__ = "documents"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        content: Mapped[str] = mapped_column(Text)
        meta: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
        embedding = mapped_column(Vector(dims.document), nullable=True)
        status: Mapped[str] = mapped_column(String)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    class RelationshipRow(Base):
        __tablename__ = "relationships"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        person_1_id: Mapped[UUID] = mapped_column(
            ForeignKey("personas.id"), index=True, nullable=False
        )
        person_2_id: Mapped[UUID] = mapped_column(
            ForeignKey("personas.id"), index=True, nullable=False
        )
        relationship: Mapped[str] = mapped_column(String)
        status: Mapped[str] = mapped_column(String)
        notes: Mapped[str | None] = mapped_column(Text, nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    class AccountRow(Base):
        __tablename__ = "accounts"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        persona_id: Mapped[UUID] = mapped_column(
            ForeignKey("personas.id"), index=True, nullable=False
        )
        url: Mapped[str] = mapped_column(String)
        login_enc: Mapped[str] = mapped_column(Text)
        password_enc: Mapped[str] = mapped_column(Text)
        session_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
        notes: Mapped[str | None] = mapped_column(Text, nullable=True)
        date_created: Mapped[datetime] = mapped_column(DateTime(timezone=True))
        date_updated: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )

    image_faces = Table(
        "image_faces", Base.metadata,
        Column("image_id", ForeignKey("images.id"), primary_key=True, index=True),
        Column("face_id", ForeignKey("faces.id"), primary_key=True, index=True),
    )
    audio_voices = Table(
        "audio_voices", Base.metadata,
        Column("audio_id", ForeignKey("audio.id"), primary_key=True, index=True),
        Column("voice_id", ForeignKey("voices.id"), primary_key=True, index=True),
    )
    document_personas = Table(
        "document_personas", Base.metadata,
        Column("document_id", ForeignKey("documents.id"), primary_key=True, index=True),
        Column("persona_id", ForeignKey("personas.id"), primary_key=True, index=True),
    )

    return ModelRegistry(
        base=Base, PersonaRow=PersonaRow, FaceRow=FaceRow, BodyRow=BodyRow,
        VoiceRow=VoiceRow, ImageRow=ImageRow, AudioRow=AudioRow, VideoRow=VideoRow,
        DocumentRow=DocumentRow, RelationshipRow=RelationshipRow, AccountRow=AccountRow,
        image_faces=image_faces, audio_voices=audio_voices, document_personas=document_personas,
    )
