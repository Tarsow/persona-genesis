"""Persona persistence. AsyncPersonaRepository is the implementation; the sync
PersonaRepository delegates to it via an anyio blocking portal."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from anyio.from_thread import BlockingPortal, start_blocking_portal
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from persona_genesis.db.crypto import VaultCipher
from persona_genesis.db.models import ModelRegistry
from persona_genesis.exceptions import ConfigError
from persona_genesis.schema.account import Account
from persona_genesis.schema.biometrics import Body, Face, VoicePrint
from persona_genesis.schema.document import Document
from persona_genesis.schema.draft import PersonaDraft
from persona_genesis.schema.media import Audio, Image, Video
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.persona import Persona
from persona_genesis.schema.relationship import Relationship

_SECTIONS = (
    "identity", "location", "contact", "work", "appearance",
    "personality", "voice", "device", "backstory",
)


def _dump(section: Any) -> dict[str, Any] | None:
    return None if section is None else section.model_dump(mode="json")


class AsyncPersonaRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: ModelRegistry,
        *,
        vault_key: str | bytes | None = None,
    ) -> None:
        self._sf = session_factory
        self._r = registry
        self._vault_key = vault_key

    def _cipher(self) -> VaultCipher:
        if self._vault_key is None:
            raise ConfigError("vault_key is required for account operations")
        return VaultCipher(self._vault_key)

    # -- persona --------------------------------------------------------------

    async def save(self, persona: Persona | PartialPersona) -> UUID:
        async with self._sf() as session:
            await self._upsert_persona(session, persona)
            await session.commit()
            return persona.id

    async def _upsert_persona(
        self, session: AsyncSession, persona: Persona | PartialPersona
    ) -> None:
        now = datetime.now(tz=UTC)
        row = await session.get(self._r.PersonaRow, persona.id)
        if row is None:
            row = self._r.PersonaRow(id=persona.id, created_at=now)
            session.add(row)
        row.updated_at = now
        row.seed = persona.seed
        row.locale = persona.locale
        for name in _SECTIONS:
            setattr(row, name, _dump(getattr(persona, name, None)))
        row.metadata_ = _dump(getattr(persona, "metadata", None))

    async def get_partial(self, persona_id: UUID) -> PartialPersona | None:
        async with self._sf() as session:
            row = await session.get(self._r.PersonaRow, persona_id)
            if row is None:
                return None
            data: dict[str, Any] = {
                "id": row.id, "seed": row.seed, "locale": row.locale,
                "metadata": row.metadata_,
            }
            for name in _SECTIONS:
                data[name] = getattr(row, name)
            return PartialPersona.model_validate(data)

    async def get(self, persona_id: UUID) -> Persona | None:
        partial = await self.get_partial(persona_id)
        if partial is None:
            return None
        try:
            return Persona.model_validate(partial.model_dump(mode="json"))
        except Exception:
            return None

    # -- draft ----------------------------------------------------------------

    async def save_draft(self, draft: PersonaDraft) -> UUID:
        async with self._sf() as session:
            await self._upsert_persona(session, draft.persona)
            # Flush the persona row first so FK-dependent children (accounts,
            # faces, voices, relationships) reference an existing personas row.
            await session.flush()
            for f in draft.faces:
                session.add(self._face_row(f))
            for b in draft.bodies:
                session.add(self._body_row(b))
            for v in draft.voices:
                session.add(self._voice_row(v))
            for im in draft.images:
                session.add(self._image_row(im))
            for au in draft.audio:
                session.add(self._audio_row(au))
            for vi in draft.video:
                session.add(self._video_row(vi))
            for doc in draft.documents:
                session.add(self._document_row(doc))
            for rel in draft.relationships:
                session.add(self._relationship_row(rel))
            if draft.accounts:
                cipher = self._cipher()
                for acc in draft.accounts:
                    session.add(self._account_row(acc, cipher))
            await session.flush()
            for image_id, face_id in draft.image_face_links:
                await session.execute(
                    self._r.image_faces.insert().values(image_id=image_id, face_id=face_id)
                )
            for audio_id, voice_id in draft.audio_voice_links:
                await session.execute(
                    self._r.audio_voices.insert().values(audio_id=audio_id, voice_id=voice_id)
                )
            for document_id, persona_id in draft.document_persona_links:
                await session.execute(
                    self._r.document_personas.insert().values(
                        document_id=document_id, persona_id=persona_id
                    )
                )
            await session.commit()
            return draft.persona.id

    # -- biometrics -----------------------------------------------------------

    async def add_face(self, face: Face) -> UUID:
        async with self._sf() as session:
            session.add(self._face_row(face))
            await session.commit()
            return face.id

    async def add_body(self, body: Body) -> UUID:
        async with self._sf() as session:
            session.add(self._body_row(body))
            await session.commit()
            return body.id

    async def add_voice(self, voice: VoicePrint) -> UUID:
        async with self._sf() as session:
            session.add(self._voice_row(voice))
            await session.commit()
            return voice.id

    async def get_faces(self, persona_id: UUID) -> list[Face]:
        async with self._sf() as session:
            rows = (await session.execute(
                select(self._r.FaceRow).where(self._r.FaceRow.persona_id == persona_id)
            )).scalars().all()
            return [self._to_face(r) for r in rows]

    async def get_bodies(self, persona_id: UUID) -> list[Body]:
        async with self._sf() as session:
            rows = (await session.execute(
                select(self._r.BodyRow).where(self._r.BodyRow.persona_id == persona_id)
            )).scalars().all()
            return [self._to_body(r) for r in rows]

    async def get_voices(self, persona_id: UUID) -> list[VoicePrint]:
        async with self._sf() as session:
            rows = (await session.execute(
                select(self._r.VoiceRow).where(self._r.VoiceRow.persona_id == persona_id)
            )).scalars().all()
            return [self._to_voice(r) for r in rows]

    async def search_faces(self, embedding: list[float], *, k: int = 5,
                           persona_id: UUID | None = None) -> list[Face]:
        async with self._sf() as session:
            stmt = select(self._r.FaceRow).order_by(
                self._r.FaceRow.embedding.cosine_distance(embedding)
            ).limit(k)
            if persona_id is not None:
                stmt = stmt.where(self._r.FaceRow.persona_id == persona_id)
            rows = (await session.execute(stmt)).scalars().all()
            return [self._to_face(r) for r in rows]

    async def search_bodies(self, embedding: list[float], *, k: int = 5,
                            persona_id: UUID | None = None) -> list[Body]:
        async with self._sf() as session:
            stmt = select(self._r.BodyRow).order_by(
                self._r.BodyRow.embedding.cosine_distance(embedding)
            ).limit(k)
            if persona_id is not None:
                stmt = stmt.where(self._r.BodyRow.persona_id == persona_id)
            rows = (await session.execute(stmt)).scalars().all()
            return [self._to_body(r) for r in rows]

    async def search_voices(self, embedding: list[float], *, k: int = 5,
                            persona_id: UUID | None = None) -> list[VoicePrint]:
        async with self._sf() as session:
            stmt = select(self._r.VoiceRow).order_by(
                self._r.VoiceRow.embedding.cosine_distance(embedding)
            ).limit(k)
            if persona_id is not None:
                stmt = stmt.where(self._r.VoiceRow.persona_id == persona_id)
            rows = (await session.execute(stmt)).scalars().all()
            return [self._to_voice(r) for r in rows]

    # -- media + links --------------------------------------------------------

    async def add_image(self, image: Image) -> UUID:
        async with self._sf() as session:
            session.add(self._image_row(image))
            await session.commit()
            return image.id

    async def add_audio(self, audio: Audio) -> UUID:
        async with self._sf() as session:
            session.add(self._audio_row(audio))
            await session.commit()
            return audio.id

    async def link_image_face(self, image_id: UUID, face_id: UUID) -> None:
        async with self._sf() as session:
            await session.execute(
                self._r.image_faces.insert().values(image_id=image_id, face_id=face_id)
            )
            await session.commit()

    async def link_audio_voice(self, audio_id: UUID, voice_id: UUID) -> None:
        async with self._sf() as session:
            await session.execute(
                self._r.audio_voices.insert().values(audio_id=audio_id, voice_id=voice_id)
            )
            await session.commit()

    async def get_faces_for_image(self, image_id: UUID) -> list[Face]:
        async with self._sf() as session:
            stmt = (select(self._r.FaceRow)
                    .join(self._r.image_faces, self._r.image_faces.c.face_id == self._r.FaceRow.id)
                    .where(self._r.image_faces.c.image_id == image_id))
            rows = (await session.execute(stmt)).scalars().all()
            return [self._to_face(r) for r in rows]

    async def get_images_for_persona(self, persona_id: UUID) -> list[Image]:
        async with self._sf() as session:
            stmt = (select(self._r.ImageRow)
                    .join(self._r.image_faces,
                          self._r.image_faces.c.image_id == self._r.ImageRow.id)
                    .join(self._r.FaceRow, self._r.FaceRow.id == self._r.image_faces.c.face_id)
                    .where(self._r.FaceRow.persona_id == persona_id).distinct())
            rows = (await session.execute(stmt)).scalars().all()
            return [self._to_image(r) for r in rows]

    async def get_audio_for_persona(self, persona_id: UUID) -> list[Audio]:
        async with self._sf() as session:
            stmt = (select(self._r.AudioRow)
                    .join(self._r.audio_voices,
                          self._r.audio_voices.c.audio_id == self._r.AudioRow.id)
                    .join(self._r.VoiceRow, self._r.VoiceRow.id == self._r.audio_voices.c.voice_id)
                    .where(self._r.VoiceRow.persona_id == persona_id).distinct())
            rows = (await session.execute(stmt)).scalars().all()
            return [self._to_audio(r) for r in rows]

    # -- documents / RAG ------------------------------------------------------

    async def add_document(self, document: Document, *, persona_ids: tuple[UUID, ...] = ()) -> UUID:
        async with self._sf() as session:
            session.add(self._document_row(document))
            await session.flush()
            for pid in persona_ids:
                await session.execute(
                    self._r.document_personas.insert().values(
                        document_id=document.id, persona_id=pid
                    )
                )
            await session.commit()
            return document.id

    async def link_document_persona(self, document_id: UUID, persona_id: UUID) -> None:
        async with self._sf() as session:
            await session.execute(
                self._r.document_personas.insert().values(
                    document_id=document_id, persona_id=persona_id
                )
            )
            await session.commit()

    async def get_documents(self, persona_id: UUID) -> list[Document]:
        async with self._sf() as session:
            stmt = (select(self._r.DocumentRow)
                    .join(self._r.document_personas,
                          self._r.document_personas.c.document_id == self._r.DocumentRow.id)
                    .where(self._r.document_personas.c.persona_id == persona_id))
            rows = (await session.execute(stmt)).scalars().all()
            return [self._to_document(r) for r in rows]

    async def search_documents(self, embedding: list[float], *, k: int = 5,
                               persona_id: UUID) -> list[Document]:
        async with self._sf() as session:
            stmt = (select(self._r.DocumentRow)
                    .join(self._r.document_personas,
                          self._r.document_personas.c.document_id == self._r.DocumentRow.id)
                    .where(self._r.document_personas.c.persona_id == persona_id)
                    .order_by(self._r.DocumentRow.embedding.cosine_distance(embedding))
                    .limit(k))
            rows = (await session.execute(stmt)).scalars().all()
            return [self._to_document(r) for r in rows]

    # -- accounts / relationships ---------------------------------------------

    async def add_account(self, account: Account) -> UUID:
        cipher = self._cipher()
        async with self._sf() as session:
            session.add(self._account_row(account, cipher))
            await session.commit()
            return account.id

    async def get_accounts(self, persona_id: UUID) -> list[Account]:
        cipher = self._cipher()
        async with self._sf() as session:
            rows = (await session.execute(
                select(self._r.AccountRow).where(self._r.AccountRow.persona_id == persona_id)
            )).scalars().all()
            return [self._to_account(r, cipher) for r in rows]

    async def add_relationship(self, relationship: Relationship) -> UUID:
        async with self._sf() as session:
            session.add(self._relationship_row(relationship))
            await session.commit()
            return relationship.id

    async def get_relationships(self, persona_id: UUID) -> list[Relationship]:
        async with self._sf() as session:
            rel_row = self._r.RelationshipRow
            rows = (await session.execute(
                select(rel_row).where(
                    or_(rel_row.person_1_id == persona_id, rel_row.person_2_id == persona_id)
                )
            )).scalars().all()
            return [self._to_relationship(r) for r in rows]

    # -- row builders ---------------------------------------------------------

    def _face_row(self, f: Face) -> Any:
        return self._r.FaceRow(id=f.id, persona_id=f.persona_id, embedding=f.embedding,
                               status=f.status, created_at=f.created_at)

    def _body_row(self, b: Body) -> Any:
        return self._r.BodyRow(id=b.id, persona_id=b.persona_id, embedding=b.embedding,
                               status=b.status, created_at=b.created_at)

    def _voice_row(self, v: VoicePrint) -> Any:
        return self._r.VoiceRow(id=v.id, persona_id=v.persona_id, embedding=v.embedding,
                                label=v.label, status=v.status, created_at=v.created_at)

    def _image_row(self, im: Image) -> Any:
        return self._r.ImageRow(
            id=im.id, file_path=im.file_path, media_type=im.media_type, type=im.type,
            nsfw=im.nsfw, width=im.width, height=im.height, description=im.description,
            origin=im.origin.model_dump(mode="json") if im.origin else None,
            status=im.status, created_at=im.created_at)

    def _audio_row(self, au: Audio) -> Any:
        return self._r.AudioRow(
            id=au.id, file_path=au.file_path, media_type=au.media_type, type=au.type,
            text=au.text, nsfw=au.nsfw, sample_rate_hz=au.sample_rate_hz,
            duration_s=au.duration_s,
            origin=au.origin.model_dump(mode="json") if au.origin else None,
            status=au.status, created_at=au.created_at)

    def _video_row(self, vi: Video) -> Any:
        return self._r.VideoRow(
            id=vi.id, file_path=vi.file_path, media_type=vi.media_type, type=vi.type,
            text=vi.text, nsfw=vi.nsfw, width=vi.width, height=vi.height,
            duration_s=vi.duration_s, fps=vi.fps, description=vi.description,
            origin=vi.origin.model_dump(mode="json") if vi.origin else None,
            status=vi.status, created_at=vi.created_at)

    def _document_row(self, doc: Document) -> Any:
        return self._r.DocumentRow(id=doc.id, content=doc.content, meta=doc.metadata,
                                   embedding=doc.embedding, status=doc.status,
                                   created_at=doc.created_at)

    def _relationship_row(self, rel: Relationship) -> Any:
        return self._r.RelationshipRow(
            id=rel.id, person_1_id=rel.person_1_id, person_2_id=rel.person_2_id,
            relationship=rel.relationship, status=rel.status, notes=rel.notes,
            created_at=rel.created_at)

    def _account_row(self, acc: Account, cipher: VaultCipher) -> Any:
        return self._r.AccountRow(
            id=acc.id, persona_id=acc.persona_id, url=acc.url,
            login_enc=cipher.encrypt(acc.login), password_enc=cipher.encrypt(acc.password),
            session_token_enc=cipher.encrypt(acc.session_token) if acc.session_token else None,
            notes=acc.notes, date_created=acc.date_created, date_updated=acc.date_updated)

    # -- row -> model ---------------------------------------------------------

    def _to_face(self, r: Any) -> Face:
        return Face(id=r.id, persona_id=r.persona_id, embedding=list(r.embedding),
                    status=r.status, created_at=r.created_at)

    def _to_body(self, r: Any) -> Body:
        return Body(id=r.id, persona_id=r.persona_id, embedding=list(r.embedding),
                    status=r.status, created_at=r.created_at)

    def _to_voice(self, r: Any) -> VoicePrint:
        return VoicePrint(id=r.id, persona_id=r.persona_id, embedding=list(r.embedding),
                          label=r.label, status=r.status, created_at=r.created_at)

    def _to_image(self, r: Any) -> Image:
        return Image(id=r.id, file_path=r.file_path, media_type=r.media_type, type=r.type,
                     nsfw=r.nsfw, width=r.width, height=r.height, description=r.description,
                     origin=r.origin, status=r.status, created_at=r.created_at)

    def _to_audio(self, r: Any) -> Audio:
        return Audio(id=r.id, file_path=r.file_path, media_type=r.media_type, type=r.type,
                     text=r.text, nsfw=r.nsfw, sample_rate_hz=r.sample_rate_hz,
                     duration_s=r.duration_s, origin=r.origin, status=r.status,
                     created_at=r.created_at)

    def _to_document(self, r: Any) -> Document:
        return Document(id=r.id, content=r.content, metadata=r.meta or {},
                        embedding=list(r.embedding) if r.embedding is not None else None,
                        status=r.status, created_at=r.created_at)

    def _to_account(self, r: Any, cipher: VaultCipher) -> Account:
        tok = cipher.decrypt(r.session_token_enc) if r.session_token_enc else None
        return Account(id=r.id, persona_id=r.persona_id, url=r.url,
                       login=cipher.decrypt(r.login_enc), password=cipher.decrypt(r.password_enc),
                       session_token=tok,
                       notes=r.notes, date_created=r.date_created, date_updated=r.date_updated)

    def _to_relationship(self, r: Any) -> Relationship:
        return Relationship(id=r.id, person_1_id=r.person_1_id, person_2_id=r.person_2_id,
                            relationship=r.relationship, status=r.status, notes=r.notes,
                            created_at=r.created_at)


class PersonaRepository:
    """Synchronous facade over AsyncPersonaRepository (anyio blocking portal)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession],
                 registry: ModelRegistry, *, vault_key: str | bytes | None = None) -> None:
        self._async = AsyncPersonaRepository(session_factory, registry, vault_key=vault_key)
        self._portal_cm = start_blocking_portal()
        self._portal: BlockingPortal = self._portal_cm.__enter__()

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._async, name)
        if not callable(attr):
            return attr

        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            return self._portal.call(lambda: attr(*args, **kwargs))

        return _wrapped

    def close(self) -> None:
        self._portal_cm.__exit__(None, None, None)

    def __enter__(self) -> "PersonaRepository":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
