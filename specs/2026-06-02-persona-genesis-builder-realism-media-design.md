# persona-genesis — Builder, Realism Honesty, Typed Media & PostgreSQL Persistence

**Date:** 2026-06-02
**Status:** Approved
**Branch:** `feat/foundation` (these changes land before the foundation merges to `main`)
**Supersedes parts of:** `specs/2026-06-01-persona-genesis-library-design.md` (§3.2 `Contact`, `Location`, `PersonaImages`)

## 1. Context

The foundation branch ships the `Persona` Pydantic contract, `Config`, and exceptions. Before merging, the data model grows a builder, a realism-honesty declaration, typed multi-media with provenance, an encrypted account vault, and — new in this revision — a **PostgreSQL persistence layer**:

1. **Empty-persona builder + fill-the-rest** — create a blank persona, set fields by hand or attach media, then generate only what's missing.
2. **Realism honesty** — everything should be as real as possible, all addresses should be real, also define functions to create fake emails and phone numbers.
3. **Typed, multiple images / audio / video with provenance** — a persona holds lists of typed media, each recording `type`, `nsfw`, `origin` provenance, and a `file_path` (binaries live on disk, never in the database). AI-generated media must record its origin.
4. **Account vault** — an `Account` table (FK → persona) stores real, caller-owned accounts (url, login, password, session tokens, …) so a persona's accounts can be operated later. Secrets are encrypted at rest and returned in plaintext through the API.
5. **PostgreSQL persistence** — every model persists to PostgreSQL (MySQL support may follow). The DB is an *added* layer: the Pydantic models remain the clean, DB-free public contract; a `db/` layer maps them to/from rows.

## 2. Architecture overview

The Pydantic models stay the public **contract** and never import SQLAlchemy. A new `db/` layer owns persistence and a `media/` layer owns on-disk binaries.

```
src/persona_genesis/
  schema/            # Pydantic contract: Persona, PartialPersona, media models, Account, …
  db/
    engine.py        # async + sync engine/session factories built from Config
    models.py        # SQLAlchemy 2.0 ORM rows: PersonaRow, AccountRow, MediaRow
    repository.py    # AsyncPersonaRepository (primary) + PersonaRepository (sync facade)
    crypto.py        # encrypt/decrypt vault secrets with Config.vault_key
  media/
    storage.py       # write bytes/PIL -> hashed path under media_dir/<kind>/
  builder.py         # PartialPersona + PersonaBuilder
  config.py
  exceptions.py
  __init__.py
```

New runtime dependencies that land with this work: `sqlalchemy>=2`, a PostgreSQL driver (`psycopg[binary]>=3`, async-capable), and `cryptography>=42` (vault encryption). `asyncpg` is an acceptable alternative driver for the async engine; the spec assumes `psycopg` 3 because it serves both sync and async engines from one dependency.

### 2.1 Async-first, sync-compatible

The persistence API is **async-first** (consistent with the already-async generator/`afill` design). A thin **synchronous facade** wraps it for callers that are not in an event loop. The async implementation is the source of truth; the sync facade delegates to it (e.g. via `anyio.from_thread`/a dedicated worker loop) and exposes the same method names without the `await`.

## 3. Complete integration

- **Account vault.** Storing email passwords, account login credentials, and session tokens for later automated operation of a persona's accounts is part of this design. The `Account` model + `accounts` table are the vault (§7). Secrets are encrypted at rest (§7.2).
- **Audio / video synthesis.** Media is handled as *containers* you attach (a `file_path` plus metadata). Text-to-speech / audio / video generation is not built now; a provider seam (`create_image` / `create_audio`, §6.4) is left so synthesis can be added later.

## 4. Scope boundary: what lands now vs. later

The orchestrator (`PersonaGenerator`), the structured/narrative/visual generators, and the CLI **do not exist yet** (deferred to later milestones in the original spec). Therefore:

**Lands on `feat/foundation` now (schema + builder + persistence, testable against a local/containerized Postgres):**
- Schema changes to `Contact` and `Location` (real-only optional fields).
- Media models: `MediaOrigin`, `PersonaImage`, `PersonaAudio`, `PersonaVideo`, `PersonaMedia`; `Persona.media` replaces `Persona.images`. Binaries are stored on disk; models carry `file_path`.
- `Account` model (the vault).
- `PartialPersona` (all sections optional) and `PersonaBuilder` with `set`, `add_image`, `add_audio`, `add_video`, `add_account`, `missing`, `build_partial`.
- `db/` layer: ORM models, async + sync repository, vault encryption, engine wiring from `Config`.
- `media/storage.py`: writing attached binaries to `media_dir/<kind>/<hash>.<ext>`.
- `Config` additions: `database_url`, `vault_key`, `media_dir`.
- Public-API / schema re-export updates.

**Deferred to the milestone that introduces the generator + CLI (documented here, not built now):**
- `PersonaGenerator.afill(builder)` / `fill(builder)` — generate only missing sections; never overwrite caller-set fields.
- `create_image()` / `create_audio()` provider calls (§6.4): the visual/audio layers append media entries with `origin.source == "ai_generated"`.
- CLI commands wrapping the repository and media save.

These deferred items are part of the design so later plans implement them consistently, but the implementation plan produced from *this* spec covers only the "lands now" set.

### 4.1 `Contact` (real-only)

```python
class Contact(BaseModel):
    phone: str | None = None   # real-only: None unless caller supplies a number they own
    email: str | None = None   # real-only: full address, caller-owned; None otherwise
```

`email_handle` is removed. A generated persona leaves `Contact` empty (`Contact()`), per the honesty guard (§4.4).

### 4.2 `Location` (precise address is real-only)

```python
class Location(BaseModel):
    country: str            # real, auto-generated (ISO 3166-1 alpha-2)
    region: str             # real, auto-generated (state / province)
    city: str               # real, auto-generated
    timezone: str           # real, auto-generated (IANA tz)
    street: str | None = None        # real, auto-generated
    postal_code: str | None = None   # real, auto-generated
```
- if ip is defined, all the location attributes should be generated based on the location of the ip.
### 4.3 The synthetic half

Names, `dob`, `nationality`, `appearance`, `personality`, `voice`, `device`/user-agent, and the coarse location fields remain generated and run through the coherence pass (locale-appropriate names, age vs. seniority, UA matches device, etc.). This is the "as real as possible" fidelity.

### 4.4 Realism honesty rule

`Contact` is only generated specifically through the function or caller provided, `Location.street`, and `Location.postal_code` will be auto-generate (if not already defined) and base on ip. The `Account` vault is caller-supplied only.

## 5. Builder: empty persona + fill-the-rest

### 5.1 `PartialPersona`

A mirror of `Persona` where every section is optional, representing an incomplete persona:

```python
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
    media: PersonaMedia = Field(default_factory=PersonaMedia)
    accounts: list[Account] = Field(default_factory=list)
    metadata: PersonaMetadata | None = None
```

The strict `Persona` remains the validated "complete" contract. `PartialPersona` is the in-progress working shape. (Both are persistable; the repository accepts either — §8.)

### 5.2 `PersonaBuilder`

```python
builder = PersonaBuilder(locale="pt_BR", seed=42)

builder.set(identity={"given_name": "Ana", "gender": "female"})  # partial section dicts merge
builder.set(work={"occupation": "Backend Engineer"})
builder.set(contact={"email": "me@mydomain.com"})                # real, caller-owned

builder.add_image(img, type="face", nsfw=0.0)                    # PIL or bytes -> saved to disk
builder.add_audio(data=b"...", media_type="audio/wav", type="voice_sample", text="...")
builder.add_video(data=b"...", media_type="video/mp4", type="clip")

builder.add_account(url="https://mail.example.com", login="ana", password="…")  # vault entry

builder.missing()          # -> {"location", "appearance", "personality", "voice", "device", "backstory"}
partial = builder.build_partial()   # PartialPersona; nothing generated
```

Behavior:
- `set(**sections)` merges partial dicts into the working `PartialPersona`. Setting a field marks it as caller-provided ground truth.
- `set` validates each section's known fields against its Pydantic model; invalid values raise Pydantic `ValidationError` immediately (fail fast). The builder does not wrap or swallow it.
- `add_image` / `add_audio` / `add_video` accept a binary (PIL `Image.Image` or `bytes`), write it to `media_dir/<kind>/<hash>.<ext>` via `media/storage.py`, and append a typed media entry (see §6) holding the resulting `file_path`. `origin.source` defaults to `"caller_supplied"`. The destination directory is `Config.media_dir` by default and overridable per call (`media_dir=`).
- `add_account(...)` appends an `Account` to `accounts` (plaintext in-memory; encrypted only at the DB boundary).
- `missing()` returns the set of section names that are still `None`.
- `build_partial()` returns the current `PartialPersona` with no generation.

### 5.3 `afill` (deferred — design only)

When the generator exists: `await gen.afill(builder)` generates only the sections in `builder.missing()`, treats caller-set fields as ground truth (never overwritten), feeds them into coherence for the generated remainder, and returns a complete strict `Persona`. Deterministic given `seed` + the pre-set fields.

## 6. Typed media with provenance (binaries on disk)

A persona holds **lists** of typed images, audio, and video. The binary payload is **never** stored in the database or in `persona.json`; only a `file_path` (relative to `media_dir`) plus full metadata is persisted, making both the DB row and the JSON a complete provenance record.

```python
class MediaOrigin(BaseModel):
    source: Literal["ai_generated", "caller_supplied"]
    provider: str | None = None        # e.g. "fal"                 (required when ai_generated)
    model: str | None = None           # e.g. "fal-ai/flux/schnell" (required when ai_generated)
    prompt: str | None = None          # generation prompt, if any
    generated_at: datetime | None = None
    

    @model_validator(mode="after")
    def _ai_requires_provenance(self) -> "MediaOrigin":
        if self.source == "ai_generated" and not (self.provider and self.model):
            raise ValueError("ai_generated media must record provider and model")
        return self


class PersonaImage(BaseModel):
    file_path: str                                    # relative to media_dir, e.g. "image/<hash>.png"
    media_type: str                                   # mime, e.g. "image/png"
    type: Literal["face", "full_body", "other"]       # snake_case; extend enum as needed
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)  # 0 = safe … 1 = fully nsfw
    width: int | None = None
    height: int | None = None
    origin: MediaOrigin | None = None                 # required for AI-generated content
    description: str | None = None                    # defined by image-to-text ai models (if defined)

class PersonaAudio(BaseModel):
    file_path: str                                    # relative to media_dir, e.g. "audio/<hash>.wav"
    media_type: str                                   # mime, e.g. "audio/wav"
    type: Literal["conversational", "voice_sample", "music", "other"]
    text: str | None = None                           # transcript / spoken text
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)
    sample_rate_hz: int | None = None
    duration_s: float | None = None
    origin: MediaOrigin | None = None


class PersonaVideo(BaseModel):
    file_path: str                                    # relative to media_dir, e.g. "video/<hash>.mp4"
    media_type: str                                   # mime, e.g. "video/mp4"
    type: Literal["clip", "avatar", "other"]
    text: str | None = None                           # transcript / caption
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)
    width: int | None = None
    height: int | None = None
    duration_s: float | None = None
    fps: float | None = None
    origin: MediaOrigin | None = None
    description: str | None = None                    # defined by image-to-text ai models (if defined)


class PersonaMedia(BaseModel):
    images: list[PersonaImage] = Field(default_factory=list)
    audio: list[PersonaAudio] = Field(default_factory=list)
    video: list[PersonaVideo] = Field(default_factory=list)
```

`Persona.media: PersonaMedia` replaces the earlier `Persona.images: PersonaImages`; `PersonaImages` is removed (the branch is unreleased, so no compatibility shim needed). The media models no longer hold PIL/bytes fields, so `arbitrary_types_allowed` is no longer needed on them.

### 6.1 On-disk storage (`media/storage.py`)

- `media_dir` defaults to `/srv/persona-genesis/media/` (from `Config.media_dir`) and is overridable per `add_*` / `create_*` call.
- Under `media_dir` there are per-kind subdirectories: `image/`, `audio/`, `video/` (one per media kind / table), and `other/` reserved as a fallback for attachments that aren't one of the three typed kinds (no typed table yet — see §11).
- The filename is a **content hash** plus an extension derived from `media_type` (e.g. `image/<sha256-hex>.png`). Identical bytes map to the same path (natural dedupe).
- The stored `file_path` is **relative** to `media_dir` (e.g. `image/<hash>.png`), so the media tree is portable; consumers resolve it against their own `media_dir`.

### 6.2 Serialization

- No binary is ever serialized. The model fields (`file_path`, `media_type`, `type`, `nsfw`, dimensions, `sample_rate_hz`, `duration_s`, `fps`, `text`, `origin`) **are** serialized.
- `persona.json` and the `media` DB rows therefore list every media item with its full metadata + path, minus the bytes. JSON round-trips losslessly.

### 6.3 Provenance rule

- Anything the library generates sets `origin` with `source="ai_generated"` and the generating `provider` + `model` (and `prompt` where applicable). Enforced by `MediaOrigin`'s validator.
- Caller-supplied media uses `source="caller_supplied"` (the builder default) or may leave `origin=None`.

### 6.4 `create_image()` / `create_audio()` (deferred — design only)

`create_image(persona, prompt, *, type=..., media_dir=...)` and `create_audio(persona, prompt, *, type=..., media_dir=...)` take the persona's **most important existing media of that kind as a reference sample** (e.g. the first `face` image / `voice_sample` audio) plus the `prompt`, call the configured provider, save the result to disk (§6.1) with an `ai_generated` `MediaOrigin` (provider + model + prompt recorded), and append the new entry. Implemented in the generator milestone; the contract is fixed here.

### 6.5 Handling operations

1. **Attach** (now): `builder.add_image(...)` / `add_audio(...)` / `add_video(...)` — saves bytes to disk, records `file_path`.
2. **Generate** (deferred): `create_image` / `create_audio` append entries with `ai_generated` origin.
3. **Persist** (now): the repository writes each entry to its per-kind media table (metadata + `file_path`, never bytes — §8).

## 7. Account vault

### 7.1 `Account` model

```python
class Account(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID                       # FK -> personas.id
    url: str                               # e.g. "https://mail.example.com"
    login: str                             # plaintext in-memory; encrypted at rest
    password: str                          # plaintext in-memory; encrypted at rest
    session_token: str | None = None       # cookie / JWT / session for automation; encrypted at rest
    notes: str | None = None
    date_created: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    date_updated: datetime | None = None
```

The `Account` object always carries **plaintext** secrets in memory. Callers read `account.password` directly.

### 7.2 Encryption at rest

- The `accounts` table stores `login`, `password`, and `session_token` as **ciphertext** columns. Encryption uses `cryptography` (Fernet — AES + HMAC) with a key supplied via `Config.vault_key`.
- The repository encrypts on write and decrypts on read, so `repo.get_accounts(persona_id)` returns `Account` objects with plaintext secrets while a raw DB dump never exposes them.
- This is **reversible** encryption (not hashing): the requirement is plaintext recoverability for later automation, not verification.
- If `vault_key` is absent when an account write/read is attempted, the repository raises a clear configuration error (it does not silently store plaintext).

## 8. Persistence layer (`db/`)

### 8.1 Tables

- **`personas`** — `id` (UUID PK), `seed`, `locale`, `created_at`, `updated_at`, and the synthetic sub-sections as **JSONB** columns (`identity`, `location`, `contact`, `work`, `appearance`, `personality`, `voice`, `device`, `backstory`, `metadata`). These sections are always read/written as a whole, so JSONB avoids a wide normalized schema while staying queryable.
- **`accounts`** — relational child: `id` (UUID PK), `persona_id` (FK → personas, indexed), `url`, `login_enc`, `password_enc`, `session_token_enc` (nullable), `notes`, `date_created`, `date_updated`. The encrypted columns hold ciphertext (§7.2).
- **One media table per kind** — each carries only the columns its kind needs (no null-padding from a shared table) plus `id` (UUID PK), `persona_id` (FK → personas, indexed), `type`, `file_path`, `media_type`, `nsfw`, `origin` (JSONB), `created_at`:
  - **`persona_images`** — adds `width`, `height`.
  - **`persona_audio`** — adds `sample_rate_hz`, `duration_s`, `text`.
  - **`persona_video`** — adds `width`, `height`, `duration_s`, `fps`, `text`.

`accounts` and the per-kind media tables are relational (you query, FK, and append to them); the synthetic persona sections are JSONB. Schema is created via SQLAlchemy metadata `create_all` for now; Alembic migrations are a follow-up (§11).

### 8.2 Repository API

```python
class AsyncPersonaRepository:
    def __init__(self, session_factory: async_sessionmaker, *, vault_key: bytes): ...

    async def save(self, persona: Persona | PartialPersona) -> UUID      # upsert by id
    async def get(self, persona_id: UUID) -> Persona | None              # strict; None if absent/incomplete
    async def get_partial(self, persona_id: UUID) -> PartialPersona | None

    async def add_account(self, account: Account) -> UUID                # encrypts secrets
    async def get_accounts(self, persona_id: UUID) -> list[Account]      # decrypts -> plaintext

    async def add_media(self, persona_id: UUID, item: PersonaImage | PersonaAudio | PersonaVideo) -> UUID
    async def get_media(self, persona_id: UUID) -> PersonaMedia


class PersonaRepository:
    """Synchronous facade over AsyncPersonaRepository — same methods, no await."""
```

- `save` maps a `Persona`/`PartialPersona` to a `personas` row (sub-sections → JSONB) and writes any `accounts` / `media` it carries.
- `get` returns a strict `Persona`, raising/None when the stored row is incomplete; `get_partial` always returns a `PartialPersona`.
- The async repository is the implementation; the sync `PersonaRepository` delegates to it (worker loop / `anyio.from_thread`) so both back ends share one code path.

### 8.3 Engine & Config

```python
class Config:
    database_url: str | None = None     # e.g. "postgresql+psycopg://user:pw@host/db"
    vault_key: str | bytes | None = None
    media_dir: str = "/srv/persona-genesis/media/"
    # … existing injected nested config (generation/provider settings) …
```

`db/engine.py` builds an async engine/`async_sessionmaker` (and a sync engine/`sessionmaker`) from `database_url`, consistent with the existing injected-config convention (no env/`.env` reading — values come from `Config`). MySQL support is a documented future option behind the same `database_url` seam.

## 9. Contract impact summary

| Model | Change |
|---|---|
| `Contact` | `phone`/`email` now `str \| None = None`; `email_handle` removed |
| `Location` | `street`, `postal_code` now `str \| None = None` |
| `PersonaImages` | **removed** |
| `PersonaImage`, `PersonaAudio`, `PersonaVideo` | **new** — carry `file_path` + metadata; no in-memory binary |
| `PersonaMedia` | **new** — `images`, `audio`, `video` lists |
| `MediaOrigin` | **new** — provenance; AI-generated requires provider+model |
| `Account` | **new** — vault entry (FK → persona); secrets plaintext in-memory, encrypted at rest |
| `Persona` | `images: PersonaImages` → `media: PersonaMedia` |
| `PartialPersona` | **new** — all-optional working shape; adds `accounts` list |
| `PersonaBuilder` | **new** — `set`, `add_image`, `add_audio`, `add_video`, `add_account`, `missing`, `build_partial` |
| `db/` (ORM + repository) | **new** — `personas`/`accounts` + per-kind media tables (`persona_images`/`persona_audio`/`persona_video`), async + sync repository, vault crypto |
| `media/storage.py` | **new** — hashed on-disk media under `media_dir/<kind>/` |
| `Config` | adds `database_url`, `vault_key`, `media_dir` |

Public API (`persona_genesis/__init__.py`) and `schema/__init__.py` re-exports updated to add the new symbols (media models, `PersonaVideo`, `Account`, `PartialPersona`, `PersonaBuilder`, repository classes) and drop `PersonaImages`.

## 10. Testing strategy

- **Schema round-trip:** `Contact`/`Location` with `None` real-only fields; `PersonaMedia` with multiple typed images/audio/video — assert no binary in JSON, but `file_path`/`type`/`nsfw`/`origin` present and round-tripping.
- **Provenance validator:** `MediaOrigin(source="ai_generated")` without `provider`/`model` raises; with them passes; `caller_supplied` needs neither.
- **nsfw bounds:** values outside `[0.0, 1.0]` rejected.
- **Builder:** empty builder → `build_partial()` has all sections `None`; `set` merges and validates; `missing()` reflects unset sections; `add_image`/`add_audio`/`add_video` write a file under `media_dir/<kind>/` with a hashed name and append an entry with `caller_supplied` origin default; `add_account` appends a vault entry.
- **Media storage:** identical bytes hash to the same `file_path`; the file lands in the correct per-kind subdir; per-call `media_dir` override is honored.
- **Persistence (against Postgres — testcontainers or a local DB):** `save` then `get` round-trips a persona; `add_media`/`get_media` round-trips metadata + `file_path` (no bytes in DB); `add_account` stores ciphertext (raw column ≠ plaintext) while `get_accounts` returns plaintext; missing `vault_key` raises.
- **Sync facade:** the sync `PersonaRepository` produces the same results as the async one for `save`/`get`/account/media paths.
- **Realism honesty:** (when the structured generator exists) a generated persona has `contact == Contact()` (all None), `location.street is None` / `location.postal_code is None`, and no auto-generated accounts. Documented now; implemented in the generator milestone.

## 11. Follow-up

- Implementation plan for the "lands now" scope (§4): schema changes + media models + `Account` + `PartialPersona` + `PersonaBuilder` + `media/storage.py` + `db/` (ORM, async+sync repository, vault crypto) + `Config` additions + tests.
- Alembic migrations (the lands-now build uses `create_all`).
- A generic attachment model + table backing the `other/` media subdir, if non image/audio/video attachments are needed.
- MySQL support behind the `database_url` seam.
- The deferred generator/CLI behavior (`afill`, `create_image`/`create_audio` provider calls, visual provenance, CLI persistence/media commands) folds into the generator and CLI milestone plans, referencing this spec for the contract.
