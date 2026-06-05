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
`PersonaDraft`, `PersonaBuilder`, content-hashed media storage, and the PostgreSQL +
pgvector persistence layer (async + sync, vector search, encrypted vault).

**Not yet built (see [Roadmap](#roadmap)):**
- **AI generation** — `PersonaGenerator` (structured/narrative/visual layers) is not
  implemented; you supply fields and embeddings yourself.
- **AI extraction** — `extraction.extract_faces/transcribe/describe_image/embed_text/…`
  exist as a fixed seam but raise `NotImplementedError`. So embeddings, transcripts,
  descriptions, and NSFW scores are caller-supplied today.
- **CLI.**

One caveat: if you `set()` a section only partially, it persists, but reading the
persona back via `get`/`get_partial` currently expects complete sections — set the
full section, or read the related entities (faces/accounts/documents), which always
round-trip.

## Roadmap

Planned, designed in [`docs/roadmap.md`](docs/roadmap.md):

1. **AI generation** — implement `PersonaGenerator.agenerate()`/`generate()` and the
   structured + narrative + visual layers with a coherence pass, producing
   `gen`/`fake`-tagged fields.
2. **Embedding-from-media** — let `add_face(image=…)`, `add_voice(audio=…)`, and
   `add_document(file=…)` extract embeddings from raw media via the extraction seam,
   not just accept pre-computed vectors.
3. **Database deduplication** — dedupe images, audio, video, and documents in the DB
   by content hash so identical binaries map to a single row (shared across personas).

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
