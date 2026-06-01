# persona-genesis — Decoupled Entities, Vector Embeddings, RAG & Field-Level Provenance

**Date:** 2026-06-04
**Status:** Approved
**Branch:** `feat/foundation` (lands before the foundation merges to `main`)
**Supersedes parts of:**
- `specs/2026-06-01-persona-genesis-library-design.md` — §3.2 (`Persona.images`), §11 (relationships were out-of-scope; now in scope).
- `specs/2026-06-02-persona-genesis-builder-realism-media-design.md` — §6 (`PersonaMedia` nesting, `Persona`-prefixed media models), §5.1 (`PartialPersona.media`/`accounts`), §8 (media tables are persona-FK'd).

## 1. Context

The 2026-06-02 revision attached typed media to a persona as a nested `PersonaMedia`. This revision **decouples** media and biometrics from the persona, makes them first-class entities related through the database, and adds three new capabilities:

1. **Decoupled, shareable media + biometric vectors.** Images and audio are standalone (not owned by one persona). Faces, bodies, and voices are AI-produced embedding vectors stored with `pgvector`. Images link to faces (M:N), audio links to voices (M:N), and faces/bodies/voices link back to personas. A persona is reachable from a photo (via the faces in it) or a recording (via the voices in it), and the same audio can be shared across multiple personas.
2. **RAG knowledge base.** A `documents` table (content + jsonb metadata + embedding vector) holds events/facts. Documents relate to personas M:N; an LLM call for a persona retrieves only that persona's linked documents.
3. **Field-level provenance (`_status`).** Every tracked attribute carries a sibling `<field>_status ∈ {real, gen, fake}` recording how real that value is. `relationships` between personas are also added.

The Pydantic models remain the clean, DB-free public contract; the `db/` layer maps them to rows. AI extraction (the models that *produce* the vectors, transcripts, descriptions, and NSFW scores) is a **fixed seam** here — signatures and an `extract=` parameter land now; the model implementations are deferred to the extraction milestone.

## 2. Architecture overview

`Persona` shrinks to **synthetic sections only**. Everything else is an independent entity with DB-owned links. Media models drop the `Persona` prefix (`Image`, `Audio`, `Video`), and `PersonaMedia` is removed.

```
src/persona_genesis/
  schema/
    status.py          # Status = Literal["real","gen","fake"]
    persona.py         # Persona (synthetic sections only; no media)
    partial.py         # PartialPersona (sections only; no media/accounts)
    identity.py …      # synthetic sections, each gains <field>_status siblings
    media.py           # MediaOrigin, Image, Audio, Video
    biometrics.py      # Face, Body, Voice (embedding vectors)
    document.py        # Document (RAG)
    account.py         # Account (vault)
    relationship.py    # Relationship, RelationshipType
    draft.py           # PersonaDraft (builder output bundle)
  media/storage.py     # on-disk hashed binaries (unchanged from 2026-06-02)
  extraction.py        # AI extraction seam (signatures now; impls deferred)
  builder.py           # PersonaBuilder -> PersonaDraft
  db/
    crypto.py          # vault encryption (unchanged)
    models.py          # ORM + vector columns built from Config dims (factory)
    engine.py          # engines/sessions + CREATE EXTENSION vector + create_all
    repository.py      # async repository (+ sync facade): CRUD, links, vector search
  config.py            # adds embedding-dim fields
```

### 2.1 Entity–relationship model

```
personas ──1───<  faces        faces.persona_id     FK NULL      (persona has 0..N faces; a face has 0..1 persona)
personas ──1───<  bodies       bodies.persona_id    FK NOT NULL  (persona has 0..N bodies)
personas ──1───<  voices       voices.persona_id    FK NOT NULL  (persona has 1..N voices)
personas ──1───<  accounts     accounts.persona_id  FK NOT NULL
personas ──1───<  relationships (person_1_id / person_2_id, both FK -> personas)

images   >──M:N──<  faces       via image_faces       (image has 0..N faces; face in 0..N images)
audio    >──M:N──<  voices      via audio_voices      (audio has 1..N voices; voice in 0..N audio)
documents>──M:N──<  personas    via document_personas (per-persona RAG retrieval)

images / audio / video  : standalone media. Binaries on disk (file_path + content hash); never in DB/JSON.
faces / bodies / voices : pgvector embedding rows; vector(N), N from Config.
documents               : content text + metadata jsonb + embedding vector(N).
```

Reachability:
- *Photo → who is in it:* `image → image_faces → faces → faces.persona_id`.
- *Recording → who is speaking:* `audio → audio_voices → voices → voices.persona_id`.
- *Persona → its knowledge:* `personas → document_personas → documents` (RAG retrieval, filtered to the persona).

### 2.2 New dependencies

- `pgvector>=0.3` (Python: `pgvector.sqlalchemy.Vector` column type).
- The PostgreSQL server must have the `vector` extension available; `db/engine.py` runs `CREATE EXTENSION IF NOT EXISTS vector` before `create_all`.
- (Already landing from 2026-06-02: `sqlalchemy[asyncio]>=2`, `psycopg[binary]>=3`, `cryptography>=42`.)

## 3. Field-level provenance (`_status`)

```python
# schema/status.py
Status = Literal["real", "gen", "fake"]
```

- **`real`** — the value came from the caller (set via `PersonaBuilder.set(...)` or an `add_*` call with caller data).
- **`gen`** — generated but *basically real*: derived from real-world data (street/postal/city/region/timezone from an IP), LLM narrative (backstory, appearance text, voice text), or an AI embedding/description.
- **`fake`** — randomly generated and only *looks* real (Faker-invented name/dob/nationality, fake phone/email, sampled device/UA).

### 3.1 Where status lives

**Synthetic sections (JSONB):** each leaf scalar gets a sibling `<field>_status: Status`; a list/collection field gets one `<field>_status` for the whole list. Status serializes with the value (into JSON and the JSONB column).

```python
class Identity(BaseModel):
    full_name: str;        full_name_status: Status = "fake"
    given_name: str;       given_name_status: Status = "fake"
    family_name: str;      family_name_status: Status = "fake"
    gender: Gender;        gender_status: Status = "fake"
    dob: date;             dob_status: Status = "fake"
    nationality: str;      nationality_status: Status = "fake"

class Location(BaseModel):
    country: str;          country_status: Status = "gen"
    region: str;           region_status: Status = "gen"
    city: str;             city_status: Status = "gen"
    timezone: str;         timezone_status: Status = "gen"
    street: str | None = None;       street_status: Status = "gen"
    postal_code: str | None = None;  postal_code_status: Status = "gen"

class Personality(BaseModel):
    ocean: OceanScores;    ocean_status: Status = "gen"
    traits: list[str];     traits_status: Status = "gen"   # one status per list
    values: list[str];     values_status: Status = "gen"
    quirks: list[str];     quirks_status: Status = "gen"
```

**Default-status map** (so an un-annotated value is never silently `real`):

| Section | Fields | Default status |
|---|---|---|
| `Identity` | full_name, given_name, family_name, gender, dob, nationality | `fake` |
| `Location` | country, region, city, timezone, street, postal_code | `gen` |
| `Contact` | phone, email | `fake` (caller-set ⇒ `real`) |
| `Work` | occupation, employer, industry, seniority, schedule | `fake` |
| `Appearance` | hair_*, eye_color, build, height_cm, distinguishing_features | `fake`; `description` | `gen` |
| `Personality` | ocean, traits, values, quirks | `gen` |
| `Voice` (text) | writing_style, posting_cadence, typical_topics, sample_paragraph | `gen` |
| `Device` | primary_device, os, browser, user_agent, screen_resolution | `fake` |
| `Backstory` | bio, education, key_life_events | `gen` |

**Embedding / media / document / relationship rows:** a single **row-level** `status: Status` column (not per-field). Defaults: `Face`/`Body`/`Voice`/`Image`/`Audio`/`Video` ⇒ `gen` (AI-produced); `Document` ⇒ `real` (caller info by default); `Relationship` ⇒ `gen`.

### 3.2 Who sets status

- `PersonaBuilder.set(identity={"full_name": "Ana"})` automatically sets `full_name_status = "real"` for every scalar key provided (and for a list key, sets that list's status to `real`). `set_status(section, field, status)` overrides any status explicitly.
- The (deferred) structured/narrative generators set `gen`/`fake` per the map above.
- `add_*` calls with caller data default the row `status` to `real`; artifacts produced by `extract=True` get `gen`.

## 4. Synthetic persona contract

```python
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
    # NO media / faces / accounts here — those are separate entities (DB-linked)

class PartialPersona(BaseModel):
    # all sections optional; sections only (no media, no accounts)
    id: UUID = Field(default_factory=uuid4)
    seed: int | None = None
    locale: str | None = None
    identity: Identity | None = None
    # … location, contact, work, appearance, personality, voice, device, backstory …
    metadata: PersonaMetadata | None = None
```

`PersonaMedia`, `Persona.media`, `PersonaImage`/`PersonaAudio`/`PersonaVideo`, and `PartialPersona.media`/`PartialPersona.accounts` (from 2026-06-02) are **removed**. The branch is unreleased, so no shim.

## 5. Standalone media & biometric models

```python
# schema/media.py
class MediaOrigin(BaseModel):          # provenance — distinct from realism `status`
    source: Literal["ai_generated", "caller_supplied"]
    provider: str | None = None        # required when ai_generated
    model: str | None = None           # required when ai_generated
    prompt: str | None = None
    generated_at: datetime | None = None
    # @model_validator: ai_generated requires provider+model

ImageType = Literal["face", "full_body", "other", "unknown"]
AudioType = Literal["conversational", "voice_sample", "music", "other", "unknown"]
VideoType = Literal["clip", "avatar", "other", "unknown"]

class Image(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_path: str                     # relative to media_dir, e.g. "image/<hash>.png"
    media_type: str
    type: ImageType
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)   # from an AI model
    width: int | None = None
    height: int | None = None
    description: str | None = None      # CLIP/caption (AI)
    origin: MediaOrigin | None = None
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

class Audio(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_path: str                     # "audio/<hash>.wav"
    media_type: str
    type: AudioType
    text: str | None = None            # ASR transcript
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)
    sample_rate_hz: int | None = None
    duration_s: float | None = None
    origin: MediaOrigin | None = None
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

class Video(BaseModel):                # placeholder — see §9
    id: UUID = Field(default_factory=uuid4)
    file_path: str
    media_type: str
    type: VideoType
    text: str | None = None
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)
    width: int | None = None
    height: int | None = None
    duration_s: float | None = None
    fps: float | None = None
    description: str | None = None
    origin: MediaOrigin | None = None
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
```

```python
# schema/biometrics.py  — embeddings are list[float] in the contract; the DB maps them to vector(N)
class Face(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID | None = None     # 0..1 persona
    embedding: list[float]             # face vector (ArcFace/FaceNet); dim from Config
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

class Body(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID                   # 1 persona
    embedding: list[float]             # person-ReID vector
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

class Voice(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID                   # 1 persona (a persona may have several voices/tones)
    embedding: list[float]             # speaker embedding (ECAPA-TDNN)
    label: str | None = None           # optional tone descriptor, e.g. "calm", "phone"
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
```

> **Naming note.** `schema.voice.Voice` (writing-style text section) and `schema.biometrics.Voice` (speaker embedding) collide. The biometric one is exported as **`VoicePrint`** at the package level; internally it lives in `biometrics.py` as `Voice` but is re-exported as `VoicePrint` to avoid the clash. The text section keeps the name `Voice`.

```python
# schema/document.py
class Document(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None   # text embedding; dim from Config
    status: Status = "real"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
```

```python
# schema/relationship.py
RelationshipType = Literal[
    "friend", "family", "partner", "coworker", "acquaintance", "other", "unknown"
]

class Relationship(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    person_1_id: UUID                  # subject
    person_2_id: UUID                  # object
    relationship: RelationshipType
    status: Status = "gen"
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
```

```python
# schema/account.py — unchanged from 2026-06-02 (vault entry, FK -> persona, secrets plaintext in-memory)
```

## 6. Persistence layer (`db/`)

### 6.1 Tables

- **`personas`** — `id`, `seed`, `locale`, `created_at`, `updated_at`, and the synthetic sub-sections as **JSONB** (`identity`, `location`, `contact`, `work`, `appearance`, `personality`, `voice`, `device`, `backstory`, `metadata`). The `_status` siblings live inside each section's JSONB.
- **`faces`** — `id`, `persona_id` (FK NULL, indexed), `embedding vector(face_dim)`, `status`, `created_at`.
- **`bodies`** — `id`, `persona_id` (FK NOT NULL, indexed), `embedding vector(body_dim)`, `status`, `created_at`.
- **`voices`** — `id`, `persona_id` (FK NOT NULL, indexed), `embedding vector(voice_dim)`, `label`, `status`, `created_at`.
- **`images`** — `id`, `file_path`, `media_type`, `type`, `nsfw`, `width`, `height`, `description`, `origin` (JSONB), `status`, `created_at`. **No** persona FK.
- **`audio`** — `id`, `file_path`, `media_type`, `type`, `text`, `nsfw`, `sample_rate_hz`, `duration_s`, `origin` (JSONB), `status`, `created_at`. **No** persona FK.
- **`video`** — placeholder columns mirroring `Video` (§9).
- **`documents`** — `id`, `content`, `metadata` (JSONB), `embedding vector(document_dim)`, `status`, `created_at`.
- **`relationships`** — `id`, `person_1_id` (FK), `person_2_id` (FK), `relationship`, `status`, `notes`, `created_at`. Both FKs indexed.
- **`accounts`** — as 2026-06-02 (`login_enc`/`password_enc`/`session_token_enc` ciphertext).
- **Junctions** — `image_faces (image_id, face_id)`, `audio_voices (audio_id, voice_id)`, `document_personas (document_id, persona_id)`; composite PKs, both columns FK + indexed.

Vector columns are sized from `Config` at engine-construction time. `db/models.py` exposes a **factory** that builds the ORM/metadata for a given set of dimensions (no global mutable dim state); `db/engine.py` calls it with the `Config` dims. The repository receives the resulting model registry. Schema is created via `Base.metadata.create_all` after `CREATE EXTENSION IF NOT EXISTS vector` (Alembic is a follow-up).

### 6.2 Repository API

```python
class AsyncPersonaRepository:
    def __init__(self, session_factory, *, vault_key=None, models): ...

    # persona
    async def save(self, persona: Persona | PartialPersona) -> UUID
    async def get(self, persona_id: UUID) -> Persona | None
    async def get_partial(self, persona_id: UUID) -> PartialPersona | None
    async def save_draft(self, draft: PersonaDraft) -> UUID    # persona + all entities + links, one tx

    # biometrics
    async def add_face(self, face: Face) -> UUID
    async def add_body(self, body: Body) -> UUID
    async def add_voice(self, voice: VoicePrint) -> UUID
    async def get_faces(self, persona_id: UUID) -> list[Face]
    async def get_bodies(self, persona_id: UUID) -> list[Body]
    async def get_voices(self, persona_id: UUID) -> list[VoicePrint]
    async def search_faces(self, embedding, *, k=5, persona_id=None) -> list[Face]   # pgvector <->
    async def search_bodies(self, embedding, *, k=5, persona_id=None) -> list[Body]
    async def search_voices(self, embedding, *, k=5, persona_id=None) -> list[VoicePrint]

    # media + links
    async def add_image(self, image: Image) -> UUID
    async def add_audio(self, audio: Audio) -> UUID
    async def link_image_face(self, image_id: UUID, face_id: UUID) -> None
    async def link_audio_voice(self, audio_id: UUID, voice_id: UUID) -> None
    async def get_images_for_persona(self, persona_id: UUID) -> list[Image]   # via faces
    async def get_audio_for_persona(self, persona_id: UUID) -> list[Audio]    # via voices
    async def get_faces_for_image(self, image_id: UUID) -> list[Face]

    # documents / RAG
    async def add_document(self, document: Document, *, persona_ids: list[UUID] = ()) -> UUID
    async def link_document_persona(self, document_id: UUID, persona_id: UUID) -> None
    async def get_documents(self, persona_id: UUID) -> list[Document]
    async def search_documents(self, embedding, *, k=5, persona_id: UUID) -> list[Document]  # persona-filtered

    # accounts (encrypted) + relationships
    async def add_account(self, account: Account) -> UUID
    async def get_accounts(self, persona_id: UUID) -> list[Account]
    async def add_relationship(self, relationship: Relationship) -> UUID
    async def get_relationships(self, persona_id: UUID) -> list[Relationship]  # person_1 OR person_2

class PersonaRepository:
    """Synchronous facade — same methods, no await (anyio blocking portal)."""
```

`search_documents` is **always** persona-scoped (per the M:N retrieval rule): it joins `document_personas` so only that persona's linked documents are ranked. `search_faces/bodies/voices` accept an optional `persona_id` filter (else global ANN).

## 7. Builder (`PersonaBuilder` → `PersonaDraft`)

```python
class PersonaDraft(BaseModel):
    persona: PartialPersona
    faces: list[Face] = []
    bodies: list[Body] = []
    voices: list[VoicePrint] = []
    images: list[Image] = []
    audio: list[Audio] = []
    video: list[Video] = []
    documents: list[Document] = []
    accounts: list[Account] = []
    relationships: list[Relationship] = []
    image_face_links: list[tuple[UUID, UUID]] = []   # (image_id, face_id)
    audio_voice_links: list[tuple[UUID, UUID]] = []  # (audio_id, voice_id)
    document_persona_links: list[tuple[UUID, UUID]] = []
```

`PersonaBuilder`:
- `set(**sections)` — merge/validate section dicts; auto-set `<field>_status="real"` for provided scalars (and list status for provided lists). `set_status(section, field, status)` overrides. `missing()` → unset core sections.
- Adders accumulate into the draft and return the model:
  `add_image(img|bytes, *, type, media_type=None, nsfw=0.0, description=None, status="real", origin=None, media_dir=None, extract=False, link_faces=None)`,
  `add_audio(*, data, media_type, type, text=None, status="real", …, extract=False, link_voices=None)`,
  `add_video(...)`, `add_face(*, embedding, status="real")`, `add_body(*, embedding, status="real")`,
  `add_voice(*, embedding, label=None, status="real")`, `add_document(*, content, embedding=None, metadata=None, status="real")`,
  `add_account(*, url, login, password, session_token=None, notes=None)`,
  `add_relationship(*, other_persona_id, relationship, status="gen", notes=None)`.
- `link_image_face(image, face)`, `link_audio_voice(audio, voice)` record link intents.
- Binaries are written to disk immediately via `media/storage.py` (content hash; relative `file_path`), exactly as 2026-06-02.
- `build() -> PersonaDraft`. `repo.save_draft(draft)` persists the whole bundle in one transaction (auto-links every `Document` added through the builder to the draft's persona).

## 8. Extraction seam (`extraction.py`)

Signatures and the `extract=` parameter land now; **implementations are deferred** (raise `NotImplementedError` until the extraction milestone). Artifacts these produce are labelled `status="gen"`.

`AudioSegment` is a small value model defined in `extraction.py` for diarized speech: `{ text: str, speaker: str | None, start_s: float, end_s: float }`. It is an extraction-seam type, not part of the persisted contract.

```python
def extract_faces(image: Image | bytes) -> list[Face]: ...          # ArcFace/FaceNet
def extract_body(image: Image | bytes) -> Body: ...                 # person ReID
def describe_image(image: Image | bytes) -> str: ...                # CLIP/caption
def score_nsfw(media: Image | Audio | bytes) -> float: ...          # NSFW classifier
def transcribe(audio: Audio | bytes) -> list[AudioSegment]: ...     # ASR + diarization (text + speaker turns)
def extract_voice(segment: AudioSegment | bytes) -> VoicePrint: ... # speaker embedding
def embed_text(text: str) -> list[float]: ...                       # document embedding
```

- **Manual:** call a function directly, then attach/persist the result.
- **Automatic:** pass `extract=True` to `add_image`/`add_audio`. The builder runs the relevant functions (image ⇒ `describe_image` + `score_nsfw` + `extract_faces` then `link_image_face`; audio ⇒ `transcribe` + `score_nsfw` + `extract_voice` then `link_audio_voice`), filling `description`/`nsfw`/`text` and creating + linking `Face`/`VoicePrint` rows, all `status="gen"`.
- With no extraction provider configured, `extract=True` raises a clear configuration error.

Extraction-provider configuration (which ASR/face/caption/embedding models, endpoints, keys) is defined in the extraction-milestone spec, not here.

## 9. `Video` (placeholder)

`Video` ships as a standalone media model + `video` table with the `unknown` type added, but **no** face/voice links and no extraction. Future direction (documented, not built): video extraction **composes** the image pipeline (faces per sampled frame ⇒ `image_faces`-style links) and the audio pipeline (voices from the demuxed track ⇒ `audio_voices`-style links), so a video resolves to the personas appearing and speaking in it.

## 10. Config additions

```python
class Config:
    # existing (2026-06-02): database_url, vault_key, media_dir, llm, image, default_locale, log_level
    face_embedding_dim: int = 512        # ArcFace/FaceNet
    body_embedding_dim: int = 2048       # person ReID
    voice_embedding_dim: int = 192       # ECAPA-TDNN
    document_embedding_dim: int = 1536   # text-embedding-3-small
```

Injected only (no env reading). `db/engine.py` builds vector columns from these dims. Changing a dim later is a migration, not a code change.

## 11. Contract impact summary

| Symbol | Change |
|---|---|
| `Status` | **new** — `Literal["real","gen","fake"]` |
| every synthetic section | **adds** `<field>_status` siblings (scalars) / one per list; default-status map §3.1 |
| `Persona` | drops `media`; sections + metadata only |
| `PartialPersona` | drops `media` and `accounts`; sections only |
| `PersonaMedia`, `PersonaImage/Audio/Video` | **removed** |
| `Image`, `Audio`, `Video` | **new** — standalone media (+`unknown` type); `description`/`nsfw` are AI-produced; row `status` |
| `Face`, `Body`, `VoicePrint` | **new** — embedding-vector models (`VoicePrint` = biometric voice; avoids clash with text `Voice`) |
| `Document` | **new** — RAG (content + metadata jsonb + embedding) |
| `Relationship`, `RelationshipType` | **new** — persona↔persona ties |
| `PersonaDraft` | **new** — builder output bundle |
| `MediaOrigin` | kept (provenance), now alongside realism `status` |
| `db/` | **new** tables: `faces`, `bodies`, `voices`, `images`, `audio`, `video`, `documents`, `relationships`, junctions; pgvector columns from Config dims |
| repository | **new** `save_draft`, biometrics/media/document/relationship CRUD, `link_*`, `search_*` (pgvector) |
| `PersonaBuilder` | rebuilt to produce `PersonaDraft`; `set` auto-`real` status; `extract=` seam |
| `extraction.py` | **new** seam (signatures + `extract=`; impls deferred) |
| `Config` | adds four embedding-dim fields |
| dependencies | adds `pgvector>=0.3`; server needs `vector` extension |

Public re-exports (`persona_genesis/__init__.py`, `schema/__init__.py`) add the new symbols and drop the removed ones.

## 12. Lands now vs deferred

**Lands now:** `Status` + `_status` across sections (auto-`real` on caller set); standalone `Image`/`Audio`/`Video`; `Face`/`Body`/`VoicePrint`/`Document`/`Relationship`; `PersonaDraft`; ORM (all tables + junctions + pgvector via Config dims + `CREATE EXTENSION`); repository (persona save/get, `save_draft`, all `add_*`/`get_*`/`link_*`/`search_*`, accounts encrypted, relationships, persona-filtered RAG search); `PersonaBuilder`; the extraction **seam** (signatures + `extract=` param, raising until implemented); Config dim fields; public-API updates.

**Deferred:** all AI extraction *implementations* (ArcFace/ReID/ECAPA, ASR+diarization, CLIP/caption, NSFW, text-embedding); `Video` extraction (§9); extraction-provider configuration; `PersonaGenerator.afill`/`fill`; `create_image`/`create_audio`; CLI.

## 13. Testing strategy

- **Schema round-trips:** sections carry `_status` defaults per §3.1; lists carry one status; `Image`/`Audio`/`Video`/`Face`/`Body`/`VoicePrint`/`Document`/`Relationship` round-trip; no binary in JSON.
- **Status behaviour:** `builder.set(...)` sets caller scalars to `real`; `set_status` overrides; un-annotated defaults are never `real`.
- **Provenance validator:** `MediaOrigin(source="ai_generated")` requires provider+model.
- **Persistence (gated by `PERSONA_GENESIS_TEST_DATABASE_URL`, pgvector-enabled Postgres):** persona `save`/`get` round-trip incl. `_status` in JSONB; `save_draft` persists persona + faces/bodies/voices/images/audio/documents/accounts/relationships + links in one tx; embeddings store + round-trip; `search_*` returns nearest by `<->`; M:N link round-trips (image↔face, audio↔voice, document↔persona); `search_documents` returns only the persona's linked docs; `get_relationships` surfaces a single row for both participants; accounts ciphertext-at-rest / plaintext-on-read; missing `vault_key` raises; sync facade parity.
- **Extraction seam:** each function and `extract=True` raise the documented error/`NotImplementedError` until implemented.

## 14. Follow-up

- Extraction-milestone spec: AI model wiring (face/body/voice embeddings, ASR+diarization, CLIP/caption, NSFW, text-embedding), provider config, and the `extract=True` execution path.
- `Video` extraction composing the image + audio pipelines (§9).
- Alembic migrations (lands-now build uses `create_all`).
- ANN index tuning for the pgvector columns (IVFFlat/HNSW) once data volumes are known.
- Generator/CLI milestones (`afill`, `create_image`/`create_audio`, CLI persistence/RAG commands), referencing this spec for the contract.
