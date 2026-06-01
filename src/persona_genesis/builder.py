"""PersonaBuilder — assemble a PartialPersona plus related entities into a
PersonaDraft. set() marks caller-provided scalars status="real". add_* write
binaries to disk and accumulate entities; extract=True runs the (deferred)
extraction seam. No generation, no DB here."""

from __future__ import annotations

import builtins
import io
from pathlib import Path
from typing import Any
from uuid import UUID

from PIL import Image as PILImage
from pydantic import BaseModel, create_model

from persona_genesis import extraction
from persona_genesis.media.storage import store_media
from persona_genesis.schema.account import Account
from persona_genesis.schema.appearance import Appearance
from persona_genesis.schema.backstory import Backstory
from persona_genesis.schema.biometrics import Body, Face, VoicePrint
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.device import Device
from persona_genesis.schema.document import Document
from persona_genesis.schema.draft import PersonaDraft
from persona_genesis.schema.identity import Identity
from persona_genesis.schema.location import Location
from persona_genesis.schema.media import (
    Audio,
    AudioType,
    Image,
    ImageType,
    MediaOrigin,
    Video,
    VideoType,
)
from persona_genesis.schema.metadata import PersonaMetadata
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.personality import Personality
from persona_genesis.schema.relationship import Relationship, RelationshipType
from persona_genesis.schema.status import Status
from persona_genesis.schema.voice import Voice
from persona_genesis.schema.work import Work

DEFAULT_MEDIA_DIR = "/srv/persona-genesis/media/"

_SECTION_MODELS: dict[str, builtins.type[Any]] = {
    "identity": Identity,
    "location": Location,
    "contact": Contact,
    "work": Work,
    "appearance": Appearance,
    "personality": Personality,
    "voice": Voice,
    "device": Device,
    "backstory": Backstory,
    "metadata": PersonaMetadata,
}
_CORE_SECTIONS: tuple[str, ...] = (
    "identity", "location", "contact", "work", "appearance",
    "personality", "voice", "device", "backstory",
)

_PIL_FORMAT: dict[str, str] = {
    "image/png": "PNG", "image/jpeg": "JPEG", "image/jpg": "JPEG",
    "image/webp": "WEBP", "image/gif": "GIF",
}


def _make_partial_validator(model: builtins.type[BaseModel]) -> builtins.type[BaseModel]:
    """Return a Pydantic model identical to *model* but with all fields optional.

    This lets set() validate individual field *types* without requiring all
    required fields to be present in the partial dict.
    """
    fields: dict[str, Any] = {}
    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        # Make every field Optional (union with None) with default None
        fields[field_name] = (annotation | None, None)  # type: ignore[operator]
    result: builtins.type[BaseModel] = create_model(
        f"_Partial{model.__name__}", **fields
    )
    return result


# Cache partial validators so we don't rebuild them on every set() call.
_PARTIAL_VALIDATORS: dict[str, builtins.type[BaseModel]] = {
    name: _make_partial_validator(model)
    for name, model in _SECTION_MODELS.items()
}


class PersonaBuilder:
    def __init__(
        self,
        *,
        locale: str | None = None,
        seed: int | None = None,
        media_dir: str | Path = DEFAULT_MEDIA_DIR,
    ) -> None:
        self._persona_id = PartialPersona(locale=locale, seed=seed).id
        self._locale = locale
        self._seed = seed
        self._media_dir = media_dir
        # raw merged dicts per section, accumulated across set() calls
        self._sections: dict[str, dict[str, Any]] = {}
        # accumulated entity lists
        self._faces: list[Face] = []
        self._bodies: list[Body] = []
        self._voices: list[VoicePrint] = []
        self._images: list[Image] = []
        self._audio: list[Audio] = []
        self._video: list[Video] = []
        self._documents: list[Document] = []
        self._accounts: list[Account] = []
        self._relationships: list[Relationship] = []
        self._image_face_links: list[tuple[UUID, UUID]] = []
        self._audio_voice_links: list[tuple[UUID, UUID]] = []
        self._document_persona_links: list[tuple[UUID, UUID]] = []

    # -- sections -------------------------------------------------------------

    def set(self, **sections: dict[str, Any]) -> PersonaBuilder:
        for name, value in sections.items():
            if name not in _SECTION_MODELS:
                raise ValueError(f"unknown section: {name!r}")
            model = _SECTION_MODELS[name]
            existing = self._sections.get(name, {})
            merged: dict[str, Any] = dict(existing)
            merged.update(value)
            # mark caller-provided scalars/lists real unless an explicit status was given
            for key in value:
                if key.endswith("_status"):
                    continue
                status_key = f"{key}_status"
                if status_key in model.model_fields and status_key not in value:
                    merged[status_key] = "real"
            # validate the provided types without requiring all fields to be present
            _PARTIAL_VALIDATORS[name].model_validate(merged)
            self._sections[name] = merged
        return self

    def set_status(self, section: str, field: str, status: str) -> PersonaBuilder:
        return self.set(**{section: {f"{field}_status": status}})

    def missing(self) -> builtins.set[str]:
        return {
            n for n in _CORE_SECTIONS
            if not any(not key.endswith("_status") for key in self._sections.get(n, {}))
        }

    # -- media ----------------------------------------------------------------

    def add_image(
        self,
        image: PILImage.Image | bytes,
        *,
        type: ImageType,
        media_type: str | None = None,
        nsfw: float = 0.0,
        description: str | None = None,
        status: Status = "real",
        origin: MediaOrigin | None = None,
        media_dir: str | Path | None = None,
        extract: bool = False,
        link_faces: list[Face] | None = None,
    ) -> Image:
        width: int | None = None
        height: int | None = None
        if isinstance(image, PILImage.Image):
            media_type = media_type or "image/png"
            width, height = image.size
            buf = io.BytesIO()
            image.save(buf, format=_PIL_FORMAT.get(media_type.lower(), "PNG"))
            data = buf.getvalue()
        else:
            if media_type is None:
                raise ValueError("media_type is required when adding raw image bytes")
            data = image
        rel = store_media(data, kind="image", media_type=media_type,
                          media_dir=media_dir or self._media_dir)
        entry = Image(
            file_path=rel,
            media_type=media_type,
            type=type,
            nsfw=nsfw,
            width=width,
            height=height,
            description=description,
            origin=origin or MediaOrigin(source="caller_supplied"),
            status=status,
        )
        self._images.append(entry)
        faces = list(link_faces or [])
        if extract:
            entry.description = extraction.describe_image(entry)
            entry.nsfw = extraction.score_nsfw(entry)
            entry.status = "gen"
            extracted = extraction.extract_faces(entry)
            self._faces.extend(extracted)
            faces.extend(extracted)
        for face in faces:
            self._image_face_links.append((entry.id, face.id))
        return entry

    def add_audio(
        self,
        *,
        data: bytes,
        media_type: str,
        type: AudioType,
        text: str | None = None,
        nsfw: float = 0.0,
        sample_rate_hz: int | None = None,
        duration_s: float | None = None,
        status: Status = "real",
        origin: MediaOrigin | None = None,
        media_dir: str | Path | None = None,
        extract: bool = False,
        link_voices: list[VoicePrint] | None = None,
    ) -> Audio:
        rel = store_media(data, kind="audio", media_type=media_type,
                          media_dir=media_dir or self._media_dir)
        entry = Audio(
            file_path=rel,
            media_type=media_type,
            type=type,
            text=text,
            nsfw=nsfw,
            sample_rate_hz=sample_rate_hz,
            duration_s=duration_s,
            origin=origin or MediaOrigin(source="caller_supplied"),
            status=status,
        )
        self._audio.append(entry)
        voices = list(link_voices or [])
        if extract:
            segments = extraction.transcribe(entry)
            entry.text = " ".join(s.text for s in segments)
            entry.nsfw = extraction.score_nsfw(entry)
            entry.status = "gen"
            for seg in segments:
                vp = extraction.extract_voice(seg)
                self._voices.append(vp)
                voices.append(vp)
        for voice in voices:
            self._audio_voice_links.append((entry.id, voice.id))
        return entry

    def add_video(
        self,
        *,
        data: bytes,
        media_type: str,
        type: VideoType,
        media_dir: str | Path | None = None,
        status: Status = "real",
        **fields: Any,
    ) -> Video:
        rel = store_media(data, kind="video", media_type=media_type,
                          media_dir=media_dir or self._media_dir)
        entry = Video(
            file_path=rel,
            media_type=media_type,
            type=type,
            status=status,
            **fields,
        )
        self._video.append(entry)
        return entry

    # -- biometrics -----------------------------------------------------------

    def add_face(self, *, embedding: list[float], status: Status = "real") -> Face:
        face = Face(
            persona_id=self._persona_id,
            embedding=embedding,
            status=status,
        )
        self._faces.append(face)
        return face

    def add_body(self, *, embedding: list[float], status: Status = "real") -> Body:
        body = Body(
            persona_id=self._persona_id,
            embedding=embedding,
            status=status,
        )
        self._bodies.append(body)
        return body

    def add_voice(
        self,
        *,
        embedding: list[float],
        label: str | None = None,
        status: Status = "real",
    ) -> VoicePrint:
        vp = VoicePrint(
            persona_id=self._persona_id,
            embedding=embedding,
            label=label,
            status=status,
        )
        self._voices.append(vp)
        return vp

    # -- documents / accounts / relationships ---------------------------------

    def add_document(
        self,
        *,
        content: str,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        status: Status = "real",
    ) -> Document:
        doc = Document(
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            status=status,
        )
        self._documents.append(doc)
        self._document_persona_links.append((doc.id, self._persona_id))
        return doc

    def add_account(
        self,
        *,
        url: str,
        login: str,
        password: str,
        session_token: str | None = None,
        notes: str | None = None,
    ) -> Account:
        acc = Account(
            persona_id=self._persona_id,
            url=url,
            login=login,
            password=password,
            session_token=session_token,
            notes=notes,
        )
        self._accounts.append(acc)
        return acc

    def add_relationship(
        self,
        *,
        other_persona_id: UUID,
        relationship: RelationshipType,
        status: Status = "gen",
        notes: str | None = None,
    ) -> Relationship:
        rel = Relationship(
            person_1_id=self._persona_id,
            person_2_id=other_persona_id,
            relationship=relationship,
            status=status,
            notes=notes,
        )
        self._relationships.append(rel)
        return rel

    # -- links / build --------------------------------------------------------

    def link_image_face(self, image: Image, face: Face) -> None:
        self._image_face_links.append((image.id, face.id))

    def link_audio_voice(self, audio: Audio, voice: VoicePrint) -> None:
        self._audio_voice_links.append((audio.id, voice.id))

    def build(self) -> PersonaDraft:
        """Assemble and return the current PersonaDraft.

        Section dicts are materialised into model instances via model_construct
        (skipping re-validation) since set() already validated field types.
        """
        # Build PartialPersona with the accumulated section dicts.
        # We use model_construct so that partially-filled sections are accepted.
        kwargs: dict[str, Any] = {
            "id": self._persona_id,
            "locale": self._locale,
            "seed": self._seed,
        }
        for name, model in _SECTION_MODELS.items():
            section = self._sections.get(name)
            if section is None:
                kwargs[name] = None
                continue
            validated = _PARTIAL_VALIDATORS[name].model_validate(section)
            provided = {key: getattr(validated, key) for key in section}
            kwargs[name] = model.model_construct(**provided)
        partial = PartialPersona.model_construct(**kwargs)

        return PersonaDraft(
            persona=partial,
            faces=list(self._faces),
            bodies=list(self._bodies),
            voices=list(self._voices),
            images=list(self._images),
            audio=list(self._audio),
            video=list(self._video),
            documents=list(self._documents),
            accounts=list(self._accounts),
            relationships=list(self._relationships),
            image_face_links=list(self._image_face_links),
            audio_voice_links=list(self._audio_voice_links),
            document_persona_links=list(self._document_persona_links),
        )
