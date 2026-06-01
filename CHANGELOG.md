# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project scaffolding: uv + hatchling, `src/` layout, ruff/mypy/pytest, CI.
- `Persona` Pydantic schema and all sub-models (identity, location, contact,
  work, appearance, personality, voice, device, backstory, metadata).
- `Config` / `Config.from_dict()` accepting an injected nested config dict
  (no environment or file reading inside the library).
- Exception hierarchy (`PersonaGenesisError` and subclasses).
- Field-level provenance: `Status` (`real`/`gen`/`fake`) with a sibling
  `<field>_status` on every synthetic-section field (lists carry one status).
- Standalone media models `Image`, `Audio`, `Video` (with an `unknown` type) and
  `MediaOrigin` provenance; binaries are stored on disk, never in JSON/DB.
- Biometric embedding models `Face`, `Body`, `VoicePrint` (vectors as
  `list[float]` in the contract).
- RAG `Document` (content + metadata + embedding) and persona↔persona
  `Relationship` models; `Account` vault entry.
- `PartialPersona` (all-optional working shape) and `PersonaDraft` bundle.
- `PersonaBuilder`: `set`/`set_status`/`missing`, `add_image`/`add_audio`/
  `add_video`, `add_face`/`add_body`/`add_voice`, `add_document`/`add_account`/
  `add_relationship`, link helpers, and `build()` → `PersonaDraft`. Caller-set
  fields are marked `real`. An `extract=` seam runs AI extraction when wired.
- On-disk content-hashed media storage (`media/storage.py`).
- AI extraction seam (`extraction.py`): signatures + `AudioSegment`; impls
  deferred (raise `NotImplementedError`).
- `Config` gains `database_url`, `vault_key`, `media_dir`, and embedding-dim
  fields (`face`/`body`/`voice`/`document`).
- PostgreSQL persistence with `pgvector`: `build_persistence(config)` +
  `create_all`/`drop_all`, an ORM factory whose vector dimensions come from
  `Config`, and `AsyncPersonaRepository` (+ a synchronous `PersonaRepository`
  facade) covering persona `save`/`get`/`get_partial`/`save_draft`, biometric/
  media/document/relationship CRUD, M:N links, persona-scoped pgvector
  similarity search, and Fernet-encrypted account secrets at rest.

### Changed
- `Contact` is real-only: `phone`/`email` default to `None`; `email_handle`
  removed. `Location.street`/`postal_code` are now optional.
- `Persona` is slimmed to synthetic sections only; media/biometrics/accounts are
  separate DB-linked entities.

### Removed
- `PersonaImages` / `Persona.images` (replaced by standalone media entities).
