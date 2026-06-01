# PostgreSQL Persistence with pgvector & Vault (Plan 2 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Depends on Plan 1** (`2026-06-04-entities-provenance-contract.md`) being merged: the contract models, `PersonaBuilder`, `PersonaDraft`, and Config dim fields must exist.

**Goal:** Implement the persistence layer of `specs/2026-06-04-persona-genesis-entities-embeddings-rag-provenance-design.md`: a pgvector-backed SQLAlchemy 2.0 ORM (vector dims from `Config`), Fernet vault encryption for account secrets, and an async `AsyncPersonaRepository` (+ sync `PersonaRepository` facade) covering persona save/get, `save_draft`, biometric/media/document/relationship CRUD, M:N links, and pgvector similarity search.

**Architecture:** Synthetic persona sections persist as JSONB; faces/bodies/voices/document embeddings as `pgvector` `vector(N)` columns sized from `Config`; images/audio/video standalone; accounts encrypted at rest; junction tables for image↔face, audio↔voice, document↔persona. The ORM is built by a **factory** (`build_models(dims)`) so vector dimensions come from config without global state. The async repository is the source of truth; the sync facade delegates via an `anyio` blocking portal.

**Tech Stack:** Python 3.12 · SQLAlchemy 2.0 (asyncio) · psycopg 3 (`postgresql+psycopg`) · pgvector 0.3+ · cryptography (Fernet) · anyio · pytest · pytest-asyncio.

---

## Conventions & test database

- Commit messages end with the body (no `Co-Authored-By`).
- Persistence tests are **gated** behind `PERSONA_GENESIS_TEST_DATABASE_URL` (a `postgresql+psycopg://…` URL) and `pytest.skip` when unset, so the suite stays green without a DB. The target database **must have the `pgvector` extension installable** (superuser or pre-created extension); `db/engine.py` issues `CREATE EXTENSION IF NOT EXISTS vector`.
- A local PG 15 cluster may already run on `:5432`. To exercise these tests, create a database, ensure pgvector is available, and export the URL, e.g.:
  ```bash
  createdb persona_genesis_test
  psql -d persona_genesis_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
  export PERSONA_GENESIS_TEST_DATABASE_URL="postgresql+psycopg://USER:PASS@localhost:5432/persona_genesis_test"
  ```
  If pgvector is not installed on the server, the search tests cannot run; install `postgresql-15-pgvector` (or equivalent) first.

## File Structure

**Created — source:**
```
src/persona_genesis/db/
├── __init__.py
├── crypto.py       # VaultCipher (Fernet) + generate_vault_key
├── models.py       # build_models(dims) -> ModelRegistry (ORM + pgvector columns + junctions)
├── engine.py       # build_persistence(config) -> engines/sessions + create_all + registry
└── repository.py   # AsyncPersonaRepository + PersonaRepository (sync facade)
```

**Modified:** `pyproject.toml`, `src/persona_genesis/__init__.py`, `tests/conftest.py`, `CHANGELOG.md`.

**Created — tests:** `tests/unit/test_db_crypto.py`, `tests/unit/test_db_models.py`, `tests/unit/test_db_engine.py`, `tests/integration/__init__.py`, `tests/integration/test_repository.py`.

---

## Task 1: Dependencies & async test config

**Files:** Modify `pyproject.toml`

- [ ] **Step 1.1: Add deps + async mode + mypy overrides**

In `pyproject.toml`:
- Extend core `dependencies` with:
  ```toml
      "sqlalchemy[asyncio]>=2",
      "psycopg[binary]>=3",
      "pgvector>=0.3",
      "cryptography>=42",
  ```
- Extend `[dependency-groups] dev` with `"pytest-asyncio>=0.23"`.
- Replace `[tool.pytest.ini_options]` with:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  addopts = "-q"
  pythonpath = ["src"]
  asyncio_mode = "auto"
  ```
- Add `pgvector.*` to the mypy ignore-missing-imports override:
  ```toml
  [[tool.mypy.overrides]]
  module = ["fake_useragent.*", "polyfactory.*", "pgvector.*"]
  ignore_missing_imports = true
  ```

- [ ] **Step 1.2: Sync + verify**

Run:
```bash
uv sync --all-extras
uv run python -c "import sqlalchemy, psycopg, cryptography, greenlet; from pgvector.sqlalchemy import Vector; from sqlalchemy.ext.asyncio import create_async_engine; print('ok', sqlalchemy.__version__)"
```
Expected: `ok 2.x.x`.

- [ ] **Step 1.3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add sqlalchemy, psycopg, pgvector, cryptography deps"
```

---

## Task 2: Vault crypto

**Files:** Create `src/persona_genesis/db/__init__.py`, `src/persona_genesis/db/crypto.py`, `tests/unit/test_db_crypto.py`

- [ ] **Step 2.1: Write the failing tests**

Create `tests/unit/test_db_crypto.py`:
```python
import pytest

from persona_genesis.db.crypto import VaultCipher, generate_vault_key
from persona_genesis.exceptions import ConfigError


def test_round_trip() -> None:
    cipher = VaultCipher(generate_vault_key())
    token = cipher.encrypt("s3cret")
    assert token != "s3cret"
    assert cipher.decrypt(token) == "s3cret"


def test_accepts_str_key() -> None:
    cipher = VaultCipher(generate_vault_key().decode())
    assert cipher.decrypt(cipher.encrypt("x")) == "x"


def test_invalid_key_raises() -> None:
    with pytest.raises(ConfigError):
        VaultCipher("not-a-fernet-key")
```

- [ ] **Step 2.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_db_crypto.py -q`
Expected: ImportError.

- [ ] **Step 2.3: Implement**

Create `src/persona_genesis/db/__init__.py`:
```python
"""PostgreSQL persistence layer (ORM factory, engine wiring, repository, vault crypto)."""
```

Create `src/persona_genesis/db/crypto.py`:
```python
"""Reversible encryption for account-vault secrets (Fernet: AES-128-CBC + HMAC)."""

from cryptography.fernet import Fernet, InvalidToken

from persona_genesis.exceptions import ConfigError


def generate_vault_key() -> bytes:
    return Fernet.generate_key()


class VaultCipher:
    def __init__(self, key: str | bytes) -> None:
        key_bytes = key.encode() if isinstance(key, str) else key
        try:
            self._fernet = Fernet(key_bytes)
        except (ValueError, TypeError) as exc:
            raise ConfigError(
                "vault_key is not a valid Fernet key (use db.crypto.generate_vault_key())"
            ) from exc

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ConfigError("vault_key cannot decrypt stored secret") from exc
```

- [ ] **Step 2.4: Run + mypy**

Run: `uv run pytest tests/unit/test_db_crypto.py -q && uv run mypy src/persona_genesis/db/crypto.py`
Expected: 3 passed; mypy clean.

- [ ] **Step 2.5: Commit**

```bash
git add src/persona_genesis/db/__init__.py src/persona_genesis/db/crypto.py tests/unit/test_db_crypto.py
git commit -m "feat(db): add Fernet vault cipher"
```

---

## Task 3: ORM factory with pgvector columns

**Files:** Create `src/persona_genesis/db/models.py`, `tests/unit/test_db_models.py`

- [ ] **Step 3.1: Write the failing smoke test (no DB needed)**

Create `tests/unit/test_db_models.py`:
```python
from persona_genesis.db.models import EmbeddingDims, build_models


def test_registry_tables_and_columns() -> None:
    reg = build_models(EmbeddingDims(face=8, body=8, voice=8, document=8))
    tables = set(reg.base.metadata.tables)
    assert {
        "personas", "faces", "bodies", "voices", "images", "audio", "video",
        "documents", "relationships", "accounts",
        "image_faces", "audio_voices", "document_personas",
    } <= tables

    persona_cols = set(reg.PersonaRow.__table__.columns.keys())
    for s in ("identity", "location", "contact", "work", "appearance",
              "personality", "voice", "device", "backstory", "metadata"):
        assert s in persona_cols

    assert {"login_enc", "password_enc", "session_token_enc"} <= set(
        reg.AccountRow.__table__.columns.keys()
    )
    assert "embedding" in reg.FaceRow.__table__.columns
    assert reg.FaceRow.__table__.columns["persona_id"].nullable is True
    assert reg.BodyRow.__table__.columns["persona_id"].nullable is False
```

- [ ] **Step 3.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_db_models.py -q`
Expected: ImportError.

- [ ] **Step 3.3: Implement the factory**

Create `src/persona_genesis/db/models.py`:
```python
"""SQLAlchemy 2.0 ORM built by a factory so pgvector dims come from Config.

Synthetic persona sections are JSONB; faces/bodies/voices/documents carry pgvector
vector(N) embeddings; images/audio/video are standalone; junction tables link
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
        identity: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
        location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
        contact: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
        work: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
        appearance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
        personality: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
        voice: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
        device: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
        backstory: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
        metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

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
        origin: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
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
        origin: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
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
        origin: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
        status: Mapped[str] = mapped_column(String)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    class DocumentRow(Base):
        __tablename__ = "documents"
        id: Mapped[UUID] = mapped_column(primary_key=True)
        content: Mapped[str] = mapped_column(Text)
        meta: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
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
        date_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
```

Notes:
- The `metadata` columns on `personas` and `documents` are mapped via attributes `metadata_`/`meta` (the name `metadata` is reserved on the Declarative base) with the actual DB column named `"metadata"`.
- If mypy flags bare `dict` in `Mapped[dict | None]`, use `Mapped[dict[str, Any] | None]`.

- [ ] **Step 3.4: Run + mypy**

Run: `uv run pytest tests/unit/test_db_models.py -q && uv run mypy src/persona_genesis/db/models.py`
Expected: 1 passed; mypy clean.

- [ ] **Step 3.5: Commit**

```bash
git add src/persona_genesis/db/models.py tests/unit/test_db_models.py
git commit -m "feat(db): ORM factory with pgvector columns and junction tables"
```

---

## Task 4: Engine wiring

**Files:** Create `src/persona_genesis/db/engine.py`, `tests/unit/test_db_engine.py`

- [ ] **Step 4.1: Write the failing test (no connection opened)**

Create `tests/unit/test_db_engine.py`:
```python
from sqlalchemy.ext.asyncio import AsyncEngine

from persona_genesis.config import Config
from persona_genesis.db.engine import build_persistence


def test_build_persistence_from_config() -> None:
    cfg = Config.from_dict(
        {"database_url": "postgresql+psycopg://u:p@localhost:5432/db",
         "face_embedding_dim": 16}
    )
    p = build_persistence(cfg)
    assert isinstance(p.engine, AsyncEngine)
    assert p.registry.FaceRow.__table__.columns["embedding"] is not None
    assert p.session_factory is not None
```

- [ ] **Step 4.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_db_engine.py -q`
Expected: ImportError.

- [ ] **Step 4.3: Implement**

Create `src/persona_genesis/db/engine.py`:
```python
"""Build async engine/session factory + ORM registry from Config, and create the
schema (pgvector extension + tables). psycopg 3 serves the async engine via the
postgresql+psycopg dialect. No env reading — values come from Config."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from persona_genesis.config import Config
from persona_genesis.db.models import EmbeddingDims, ModelRegistry, build_models
from persona_genesis.exceptions import ConfigError


@dataclass
class Persistence:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    registry: ModelRegistry


def build_persistence(config: Config) -> Persistence:
    if not config.database_url:
        raise ConfigError("database_url is required to build the persistence layer")
    dims = EmbeddingDims(
        face=config.face_embedding_dim,
        body=config.body_embedding_dim,
        voice=config.voice_embedding_dim,
        document=config.document_embedding_dim,
    )
    registry = build_models(dims)
    engine = create_async_engine(config.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return Persistence(engine=engine, session_factory=session_factory, registry=registry)


async def create_all(persistence: Persistence) -> None:
    async with persistence.engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(persistence.registry.base.metadata.create_all)


async def drop_all(persistence: Persistence) -> None:
    async with persistence.engine.begin() as conn:
        await conn.run_sync(persistence.registry.base.metadata.drop_all)
```

- [ ] **Step 4.4: Run + mypy**

Run: `uv run pytest tests/unit/test_db_engine.py -q && uv run mypy src/persona_genesis/db/engine.py`
Expected: 1 passed; mypy clean.

- [ ] **Step 4.5: Commit**

```bash
git add src/persona_genesis/db/engine.py tests/unit/test_db_engine.py
git commit -m "feat(db): build_persistence wiring + create_all (pgvector extension)"
```

---

## Task 5: Repository (async + sync facade)

**Files:** Create `src/persona_genesis/db/repository.py`

This task implements the full repository. Its behaviour is verified by the gated integration tests in Task 6 (no separate unit test here — the module is import-checked by mypy and exercised against Postgres in Task 6).

- [ ] **Step 5.1: Implement the repository**

Create `src/persona_genesis/db/repository.py`:
```python
"""Persona persistence. AsyncPersonaRepository is the implementation; the sync
PersonaRepository delegates to it via an anyio blocking portal."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from anyio.from_thread import BlockingPortal, start_blocking_portal
from sqlalchemy import delete, or_, select
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

    async def _upsert_persona(self, session: AsyncSession, persona: Persona | PartialPersona) -> None:
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
        now = datetime.now(tz=UTC)
        async with self._sf() as session:
            await self._upsert_persona(session, draft.persona)
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
                    session.add(self._account_row(acc, cipher, now))
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
                    .join(self._r.image_faces, self._r.image_faces.c.image_id == self._r.ImageRow.id)
                    .join(self._r.FaceRow, self._r.FaceRow.id == self._r.image_faces.c.face_id)
                    .where(self._r.FaceRow.persona_id == persona_id).distinct())
            rows = (await session.execute(stmt)).scalars().all()
            return [self._to_image(r) for r in rows]

    async def get_audio_for_persona(self, persona_id: UUID) -> list[Audio]:
        async with self._sf() as session:
            stmt = (select(self._r.AudioRow)
                    .join(self._r.audio_voices, self._r.audio_voices.c.audio_id == self._r.AudioRow.id)
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
                    self._r.document_personas.insert().values(document_id=document.id, persona_id=pid)
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
            session.add(self._account_row(account, cipher, datetime.now(tz=UTC)))
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
            R = self._r.RelationshipRow
            rows = (await session.execute(
                select(R).where(or_(R.person_1_id == persona_id, R.person_2_id == persona_id))
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

    def _account_row(self, acc: Account, cipher: VaultCipher, now: datetime) -> Any:
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
        return Account(id=r.id, persona_id=r.persona_id, url=r.url,
                       login=cipher.decrypt(r.login_enc), password=cipher.decrypt(r.password_enc),
                       session_token=cipher.decrypt(r.session_token_enc) if r.session_token_enc else None,
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
```

Notes:
- `__getattr__` forwards every async method through the portal, so the sync facade needs no per-method boilerplate. `self._portal.call` takes a zero-arg callable; the lambda captures args. (If you prefer explicitness/typing, replace `__getattr__` with one wrapper per method — the integration test only needs `save`/`get_partial`.)
- `uuid4` import is retained for any incidental id needs; remove it if ruff flags it as unused.

- [ ] **Step 5.2: mypy + lint**

Run:
```bash
uv run ruff check src/persona_genesis/db/repository.py
uv run mypy src/persona_genesis/db/repository.py
```
Expected: clean. (For pgvector's `.cosine_distance`, the `pgvector.*` mypy override from Task 1 suppresses missing-stub errors; if mypy still flags `Column.cosine_distance`, add `# type: ignore[attr-defined]` on those lines.)

- [ ] **Step 5.3: Commit**

```bash
git add src/persona_genesis/db/repository.py
git commit -m "feat(db): async repository (+ sync facade) for personas, draft, biometrics, media, RAG, vault, relationships"
```

---

## Task 6: Integration tests + public API + conftest + verification

**Files:** Modify `src/persona_genesis/__init__.py`, `tests/conftest.py`; Create `tests/integration/__init__.py`, `tests/integration/test_repository.py`

- [ ] **Step 6.1: Export the repositories**

In `src/persona_genesis/__init__.py`, add imports + `__all__` entries:
```python
from persona_genesis.db.repository import AsyncPersonaRepository, PersonaRepository
```
Add `"AsyncPersonaRepository"` and `"PersonaRepository"` to `__all__` (keep it sorted).

- [ ] **Step 6.2: Add DB fixtures to conftest**

Append to `tests/conftest.py`:
```python
import os

DATABASE_URL_ENV = "PERSONA_GENESIS_TEST_DATABASE_URL"


@pytest.fixture
def database_url() -> str:
    url = os.environ.get(DATABASE_URL_ENV)
    if not url:
        pytest.skip(f"set {DATABASE_URL_ENV} to run persistence tests")
    return url


@pytest.fixture
def vault_key() -> bytes:
    from persona_genesis.db.crypto import generate_vault_key

    return generate_vault_key()
```
(`import pytest` already exists in conftest — only add `import os` and these fixtures.)

- [ ] **Step 6.3: Write the integration tests**

Create `tests/integration/__init__.py` (empty).

Create `tests/integration/test_repository.py`:
```python
import uuid
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import text

from persona_genesis.config import Config
from persona_genesis.db.engine import Persistence, build_persistence, create_all, drop_all
from persona_genesis.db.repository import AsyncPersonaRepository, PersonaRepository
from persona_genesis.schema.account import Account
from persona_genesis.schema.biometrics import Face
from persona_genesis.schema.document import Document
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.relationship import Relationship

DIM = 8


def _cfg(database_url: str) -> Config:
    return Config.from_dict({
        "database_url": database_url,
        "face_embedding_dim": DIM, "body_embedding_dim": DIM,
        "voice_embedding_dim": DIM, "document_embedding_dim": DIM,
    })


def _partial() -> PartialPersona:
    return PartialPersona(id=uuid.uuid4(), seed=7, locale="pt_BR")


@pytest_asyncio.fixture
async def persistence(database_url: str) -> AsyncIterator[Persistence]:
    p = build_persistence(_cfg(database_url))
    await drop_all(p)
    await create_all(p)
    yield p
    await drop_all(p)
    await p.engine.dispose()


async def test_save_and_get_partial(persistence: Persistence, vault_key: bytes) -> None:
    repo = AsyncPersonaRepository(persistence.session_factory, persistence.registry, vault_key=vault_key)
    partial = _partial()
    await repo.save(partial)
    loaded = await repo.get_partial(partial.id)
    assert loaded is not None
    assert loaded.locale == "pt_BR"
    assert loaded.seed == 7


async def test_face_store_and_search(persistence: Persistence, vault_key: bytes) -> None:
    repo = AsyncPersonaRepository(persistence.session_factory, persistence.registry, vault_key=vault_key)
    partial = _partial()
    await repo.save(partial)
    near = Face(persona_id=partial.id, embedding=[1.0] + [0.0] * (DIM - 1))
    far = Face(persona_id=partial.id, embedding=[0.0] * (DIM - 1) + [1.0])
    await repo.add_face(near)
    await repo.add_face(far)
    got = await repo.get_faces(partial.id)
    assert {f.id for f in got} == {near.id, far.id}
    ranked = await repo.search_faces([1.0] + [0.0] * (DIM - 1), k=1)
    assert ranked[0].id == near.id


async def test_document_rag_is_persona_scoped(persistence: Persistence, vault_key: bytes) -> None:
    repo = AsyncPersonaRepository(persistence.session_factory, persistence.registry, vault_key=vault_key)
    a, b = _partial(), _partial()
    await repo.save(a)
    await repo.save(b)
    doc_a = Document(content="A's event", embedding=[1.0] + [0.0] * (DIM - 1))
    doc_b = Document(content="B's event", embedding=[0.0] * (DIM - 1) + [1.0])
    await repo.add_document(doc_a, persona_ids=(a.id,))
    await repo.add_document(doc_b, persona_ids=(b.id,))
    a_docs = await repo.get_documents(a.id)
    assert {d.id for d in a_docs} == {doc_a.id}
    hits = await repo.search_documents([0.0] * (DIM - 1) + [1.0], k=5, persona_id=a.id)
    assert {d.id for d in hits} == {doc_a.id}  # only A's docs are searched


async def test_account_ciphertext_at_rest(persistence: Persistence, vault_key: bytes) -> None:
    repo = AsyncPersonaRepository(persistence.session_factory, persistence.registry, vault_key=vault_key)
    partial = _partial()
    await repo.save(partial)
    await repo.add_account(Account(persona_id=partial.id, url="https://m", login="u", password="s3cret"))
    got = await repo.get_accounts(partial.id)
    assert got[0].password == "s3cret"
    async with persistence.session_factory() as session:
        raw = (await session.execute(text("select password_enc from accounts"))).all()
    assert raw[0][0] != "s3cret"


async def test_relationship_surfaces_for_both(persistence: Persistence, vault_key: bytes) -> None:
    repo = AsyncPersonaRepository(persistence.session_factory, persistence.registry, vault_key=vault_key)
    a, b = _partial(), _partial()
    await repo.save(a)
    await repo.save(b)
    rel = Relationship(person_1_id=a.id, person_2_id=b.id, relationship="friend")
    await repo.add_relationship(rel)
    assert {r.id for r in await repo.get_relationships(a.id)} == {rel.id}
    assert {r.id for r in await repo.get_relationships(b.id)} == {rel.id}


def test_sync_facade(database_url: str, vault_key: bytes) -> None:
    import anyio

    p = build_persistence(_cfg(database_url))
    anyio.run(drop_all, p)
    anyio.run(create_all, p)
    partial = _partial()
    with PersonaRepository(p.session_factory, p.registry, vault_key=vault_key) as repo:
        repo.save(partial)
        loaded = repo.get_partial(partial.id)
        assert loaded is not None
        assert loaded.locale == "pt_BR"
    anyio.run(drop_all, p)
    anyio.run(p.engine.dispose)
```

- [ ] **Step 6.4: Run (gated) + lint + mypy**

If a pgvector-enabled Postgres is available:
```bash
export PERSONA_GENESIS_TEST_DATABASE_URL="postgresql+psycopg://USER:PASS@localhost:5432/persona_genesis_test"
uv run pytest tests/integration -q
```
Expected: 6 passed. Otherwise:
```bash
uv run pytest tests/integration -q
```
Expected: 6 skipped.

Always run:
```bash
uv run pytest tests/unit -q
uv run ruff check src tests
uv run mypy src/persona_genesis tests
```
Expected: unit green; lint clean; mypy clean.

- [ ] **Step 6.5: Commit**

```bash
git add src/persona_genesis/__init__.py tests/conftest.py tests/integration
git commit -m "feat(db): export repositories + gated pgvector persistence integration tests"
```

---

## Task 7: CHANGELOG

**Files:** Modify `CHANGELOG.md`

- [ ] **Step 7.1: Record persistence changes**

Under `## [Unreleased]`, add an `### Added` entry: PostgreSQL persistence with pgvector — `build_persistence`/`create_all`, ORM factory (vector dims from Config), `AsyncPersonaRepository` + sync `PersonaRepository` (persona save/get, `save_draft`, biometric/media/document/relationship CRUD, M:N links, similarity search, persona-scoped RAG retrieval), and Fernet vault encryption for account secrets.

- [ ] **Step 7.2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: changelog for the pgvector persistence layer"
```

---

## Self-Review (against the spec)

**Spec coverage (§ refs to 2026-06-04 spec):**
- §2.2 deps (sqlalchemy/psycopg/pgvector/cryptography) → Task 1.
- §6.1 tables (personas JSONB; faces/bodies/voices/documents pgvector; images/audio/video standalone; relationships; accounts; junctions) + dims from Config + `CREATE EXTENSION` → Tasks 3, 4.
- §6.2 repository API (save/get/get_partial/save_draft; add/get/search biometrics; add/link/get media; add/link/get/search documents; accounts encrypted; relationships) + sync facade → Tasks 5, 6.
- §7.2 vault encryption + missing-key error → Tasks 2, 5.
- §3 row-level `status` persisted on every entity row → Task 5 (row builders carry `status`).
- §13 persistence testing (save/get round-trip, embedding store + `<->` search, persona-scoped RAG, account ciphertext/plaintext, relationship surfaces-both, sync parity) → Task 6.

**Type consistency:** the `ModelRegistry` attribute names (`PersonaRow`, `FaceRow`, … `image_faces`, `audio_voices`, `document_personas`) are used identically in `engine.py`, `repository.py`, and the model test. `VoicePrint` ↔ `VoiceRow` mapping is consistent. `EmbeddingDims(face/body/voice/document)` matches `Config.*_embedding_dim` in `build_persistence`. Junction column names (`image_id/face_id`, `audio_id/voice_id`, `document_id/persona_id`) match the repository inserts/joins.

**Deferred (NOT built here):** AI extraction impls, Video extraction, Alembic migrations, ANN index tuning, generator/CLI. Correct.
