# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `RecordedProvider` (`LLMProvider`): record-once / replay LLM exchanges to a JSON
  cassette, keyed on a hash of `(kind, system, user, schema)`. With an `upstream` it
  records on a cassette miss and persists; without one it replays only and raises
  `ProviderError` on a miss. Enables an offline, deterministic snapshot test of the
  full `agenerate()` path (committed cassette recorded live against DeepSeek) that
  runs at `--level 0` with no API cost. Exported from the package root.
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
- Narrative generation (LLM): `PersonaGenerator.agenerate()`/`generate()` now produce a
  complete `Persona` — personality, appearance, backstory, and voice (`status="gen"`) —
  via an OpenAI-compatible `OpenAICompatProvider` (raw httpx; **DeepSeek** default),
  with a `FakeLLMProvider` for offline use and a `build_llm_provider(config)` factory.
  A deterministic coherence pass (backstory chronology, age vs seniority) retries once
  before raising `CoherenceError`. The default `LLMConfig` provider is now `deepseek`.
  Cost-tiered tests via `pytest --level` (0 offline, 1 minimal ping, 2 full).
- Structured generation (offline, deterministic): `PersonaGenerator` with
  `generate_structured`/`agenerate_structured` and `fill_structured`/
  `afill_structured`, filling `identity`/`location`/`work`/`device` (contact stays
  empty) from Faker + bundled real datasets (cities, `ua_pool`, occupations), with
  age-coherent seniority and coherent device profiles. IP→location via a `GeoLocator`
  protocol + `GeoIP2Locator` (`[geoip]` extra, `Config.geoip_database_path`).
  `LLMProvider`/`ImageProvider` protocols define the narrative/visual seam;
  `generate()`/`agenerate()` raise `ConfigError` until an LLM provider is wired.
- PostgreSQL persistence with `pgvector`: `build_persistence(config)` +
  `create_all`/`drop_all`, an ORM factory whose vector dimensions come from
  `Config`, and `AsyncPersonaRepository` (+ a synchronous `PersonaRepository`
  facade) covering persona `save`/`get`/`get_partial`/`save_draft`, biometric/
  media/document/relationship CRUD, M:N links, persona-scoped pgvector
  similarity search, and Fernet-encrypted account secrets at rest.

### Fixed
- Narrative backstory off-by-one: the prompt now states the exact birth year
  (`born: YYYY (age N)`) instead of age alone. Previously the model anchored early
  life events to `current_year - age`, which can be `dob.year - 1`, tripping the
  birth-year coherence check and forcing `agenerate` to retry (or fail). Verified
  across five live DeepSeek seeds/locales — first-attempt violations dropped from
  4/5 to 0/5. (Snapshot cassette re-recorded for the new prompt.)

### Changed
- `Contact` is real-only: `phone`/`email` default to `None`; `email_handle`
  removed. `Location.street`/`postal_code` are now optional.
- `Persona` is slimmed to synthetic sections only; media/biometrics/accounts are
  separate DB-linked entities.

### Removed
- `PersonaImages` / `Persona.images` (replaced by standalone media entities).
