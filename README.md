# persona-genesis

Build detailed, coherent synthetic personas — identity, location, work, personality,
voice, device, backstory — together with decoupled, shareable media (images, audio,
video), biometric embeddings (faces, bodies, voiceprints), an encrypted account
vault, a relationship graph, and a per-persona RAG document store. Persistable to
PostgreSQL with `pgvector`.

> **Status: alpha (v0.1, `feat/foundation`).** The data contract, builder, on-disk
> media storage, and the full PostgreSQL + pgvector persistence layer are
> implemented and tested. Automatic AI generation and AI extraction are designed as
> seams but **not yet wired** — you supply fields and embeddings yourself for now.
> See [Roadmap](#roadmap).

## Key ideas

- **Decoupled entities.** A `Persona` is just its synthetic sections. Images/audio
  are standalone; faces/bodies/voices are embedding vectors that link back to a
  persona; an image can contain many faces, audio can carry many voices, and a
  document can belong to many personas (RAG).
- **Field-level provenance.** Every field carries a sibling `<field>_status` of
  `real` (caller-supplied), `gen` (generated but basically real), or `fake`
  (random, only looks real). You always know how real any value is.
- **Real-only by default.** `Contact` (phone/email) and the precise address are
  never fabricated — they stay empty unless you supply them.
- **Binaries on disk, metadata in the DB.** Attached media is content-hashed to
  disk; the database and JSON store only a `file_path` + metadata (never bytes).
- **Encrypted vault.** Account credentials are Fernet-encrypted at rest and
  returned as plaintext in memory for automation.
- **DB-free contract.** The Pydantic models never import SQLAlchemy; a separate
  `db/` layer maps them to/from rows.

## Install

Not on PyPI yet — install from git (Python 3.12+):

```bash
uv add "persona-genesis @ git+https://github.com/tarsow/persona-genesis@feat/foundation"
# or:  pip install "git+https://github.com/tarsow/persona-genesis@feat/foundation"
```

The persistence stack (SQLAlchemy 2, psycopg 3, pgvector, cryptography) ships in the
core install. For persistence you also need a PostgreSQL server with the `pgvector`
extension available.

## Quickstart — build a persona in memory (no database)

```python
from persona_genesis import PersonaBuilder

b = PersonaBuilder(locale="pt_BR", seed=42, media_dir="/tmp/media")
b.set(identity={"full_name": "Ana Souza", "given_name": "Ana", "family_name": "Souza",
                "gender": "female", "dob": "1994-03-12", "nationality": "BR"})
b.set(contact={"email": "ana@example.com"})        # caller-owned → status "real"
b.add_face(embedding=[0.1] * 512)                  # vector from your own face model
b.add_account(url="https://mail.example.com", login="ana", password="s3cret")
b.add_document(content="Attended PyCon 2026", embedding=[0.0] * 1536)

draft = b.build()                                  # a PersonaDraft bundle
assert draft.persona.identity.given_name_status == "real"
print(draft.persona.model_dump_json())             # JSON-serializable contract
```

## Quickstart — generate a persona (offline, deterministic)

The **structured layer** fills `identity`/`location`/`work`/`device` with real,
coherent, reproducible data — no API key required — and `generate_structured` returns
a `PartialPersona`. The **narrative layer** adds personality/appearance/backstory/voice
via an LLM; `agenerate()`/`generate()` return a complete `Persona`:

```python
from persona_genesis import Config, OpenAICompatProvider, PersonaGenerator

llm = OpenAICompatProvider(api_key="sk-...")        # DeepSeek by default
gen = PersonaGenerator(Config(), llm=llm)
persona = await gen.agenerate(seed=42, locale="pt_BR")   # full Persona; one coherence retry
```

```python
from persona_genesis import Config, PersonaGenerator, StructuredConstraints

gen = PersonaGenerator(Config())
p = gen.generate_structured(seed=42, locale="pt_BR",
                            constraints=StructuredConstraints(age_range=(28, 35), gender="female"))

print(p.identity.full_name, p.identity.dob, f"[{p.identity.full_name_status}]")  # ... [fake]
print(p.location.city, p.location.region, p.location.timezone, f"[{p.location.country_status}]")  # real, coherent [gen]
print(p.work.occupation, "@", p.work.employer, p.work.seniority)  # age-coherent seniority
print(p.device.primary_device, p.device.os, p.device.user_agent)  # coherent UA
assert p.contact.phone is None and p.contact.email is None        # real-only, never fabricated
```

Pass an `ip` constraint (with a `GeoIP2Locator` built from a caller-supplied
GeoLite2-City `.mmdb`) to derive the location from a real IP. `fill_structured(builder)`
generates only the structured sections a builder is missing, leaving caller-set
fields untouched.

## Quickstart — persist to PostgreSQL + pgvector

Enable the extension once on your database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

```python
import anyio
from persona_genesis import Config, PersonaBuilder
from persona_genesis.db.crypto import generate_vault_key
from persona_genesis.db.engine import build_persistence, create_all
from persona_genesis.db.repository import AsyncPersonaRepository

config = Config(
    database_url="postgresql+psycopg://user:pw@localhost:5432/persona",
    vault_key=generate_vault_key(),   # ⚠️ persist this — losing it loses the encrypted secrets
    media_dir="/srv/persona-genesis/media",
    face_embedding_dim=512,           # must match your face model's output dimension
)

async def main() -> None:
    p = build_persistence(config)
    await create_all(p)               # creates tables + enables pgvector
    repo = AsyncPersonaRepository(p.session_factory, p.registry, vault_key=config.vault_key)

    b = PersonaBuilder(locale="pt_BR", media_dir=config.media_dir)
    b.set(identity={"full_name": "Ana Souza", "given_name": "Ana", "family_name": "Souza",
                    "gender": "female", "dob": "1994-03-12", "nationality": "BR"})
    b.add_face(embedding=[0.1] * 512)
    b.add_account(url="https://mail.example.com", login="ana", password="s3cret")

    pid = await repo.save_draft(b.build())             # persona + face + account, one tx
    accounts = await repo.get_accounts(pid)            # secrets decrypted in memory
    print(accounts[0].password)                        # "s3cret" (ciphertext at rest)
    similar = await repo.search_faces([0.1] * 512, k=5)  # pgvector similarity search

anyio.run(main)
```

Synchronous callers use the same method names without `await`:

```python
from persona_genesis.db.repository import PersonaRepository

with PersonaRepository(p.session_factory, p.registry, vault_key=config.vault_key) as repo:
    pid = repo.save_draft(draft)
    repo.get_accounts(pid)
```

## Repository API

`AsyncPersonaRepository` (and the synchronous `PersonaRepository` facade) provide:

| Area | Methods |
|---|---|
| Personas | `save`, `get`, `get_partial`, `save_draft` |
| Biometrics | `add_face/body/voice`, `get_faces/bodies/voices`, `search_faces/bodies/voices` (pgvector) |
| Media + links | `add_image/audio`, `link_image_face`, `link_audio_voice`, `get_images_for_persona`, `get_audio_for_persona`, `get_faces_for_image` |
| RAG | `add_document`, `link_document_persona`, `get_documents`, `search_documents(..., persona_id=...)` |
| Vault | `add_account`, `get_accounts` (encrypted at rest, plaintext in memory) |
| Relationships | `add_relationship`, `get_relationships` |

## Configuration

`Config` is **injected** — the library never reads the environment or a `.env`
itself. Build it from literals, a secrets manager, or your own loader:

```python
from persona_genesis import Config

config = Config.from_dict({
    "database_url": "postgresql+psycopg://user:pw@host/db",
    "vault_key": "<fernet-key>",
    "media_dir": "/srv/persona-genesis/media",
    "face_embedding_dim": 512, "body_embedding_dim": 2048,
    "voice_embedding_dim": 192, "document_embedding_dim": 1536,
    "llm": {"provider": "anthropic", "api_key": "...", "model": "claude-opus-4-7"},
})
```

Embedding lengths you pass must match the corresponding `*_embedding_dim`.

## Status & limitations

**Implemented:** the full Pydantic contract with `_status` provenance, real-only
Contact/Location, standalone `Image`/`Audio`/`Video`, biometric `Face`/`Body`/
`VoicePrint`, RAG `Document`, `Relationship`, `Account` vault, `PartialPersona`,
`PersonaDraft`, `PersonaBuilder`, content-hashed media storage, the PostgreSQL +
pgvector persistence layer (async + sync, vector search, encrypted vault), the
**structured generation layer** (`PersonaGenerator.generate_structured`/
`fill_structured` for identity/location/work/device, with GeoIP IP→location), and the
**narrative generation layer** — `agenerate()`/`generate()` produce a complete
`Persona` (personality/appearance/backstory/voice) via an OpenAI-compatible
`OpenAICompatProvider` (DeepSeek default), with a deterministic coherence pass and a
`FakeLLMProvider` for offline use.

**Not yet built (see [Roadmap](#roadmap)):**
- **Visual & biometric generation** — image/biometric generation behind the
  `ImageProvider` protocol (face/body images + embeddings). Narrative generation
  works today with an LLM provider; `agenerate()` raises only if no `llm` is given.
- **AI extraction** — `extraction.extract_faces/transcribe/describe_image/embed_text/…`
  exist as a fixed seam but raise `NotImplementedError`. So embeddings, transcripts,
  descriptions, and NSFW scores are caller-supplied today.
- **CLI.**

One caveat: if you `set()` a section only partially, it persists, but reading the
persona back via `get`/`get_partial` currently expects complete sections — set the
full section, or read the related entities (faces/accounts/documents), which always
round-trip.

## Roadmap

Phased plan in [`docs/roadmap.md`](docs/roadmap.md). Done: Phase 0 (foundation),
Phase 1 (structured generation), Phase 2 (narrative/LLM generation). Next:

1. **Visual & biometric generation (Phase 3)** — face/body images + embeddings behind
   an `ImageProvider`.
2. **AI extraction (Phase 4)** — implement the extraction seam and
   `add_face(image=…)`/`add_voice(audio=…)`/`add_document(file=…)`.
3. **Database deduplication (Phase 5)** — dedupe media/documents by content hash.

## Development

```bash
uv sync
uv run ruff check src tests
uv run mypy src/persona_genesis tests
uv run pytest                                   # unit tests; persistence tests skip

# run the persistence integration tests against a real DB:
export PERSONA_GENESIS_TEST_DATABASE_URL="postgresql+psycopg://user:pw@localhost:5432/persona_genesis_test"
uv run pytest tests/integration
```

The design lives in `specs/`; implementation plans in `docs/superpowers/plans/`.

## License

MIT — see [LICENSE](LICENSE).
