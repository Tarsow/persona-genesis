# persona-genesis — Roadmap

The phased plan from the current foundation to a full persona generator. Each phase
produces working, tested software on its own. Concrete, locked design lives in
`specs/`; this file is the map and the forward-looking intent.

**Status legend:** ✅ done · 🚧 in progress · 🔭 designed/next · ⏳ planned · 🔒 blocked
on external setup (API keys / models / data files).

---

## Phase 0 — Foundation ✅

The DB-free contract and the persistence layer. Shipped on `master`.

- Pydantic contract with field-level `_status` provenance (`real`/`gen`/`fake`);
  real-only `Contact`/`Location`.
- Decoupled entities: standalone `Image`/`Audio`/`Video`; biometric `Face`/`Body`/
  `VoicePrint`; RAG `Document`; `Relationship`; `Account` vault.
- `PartialPersona`, `PersonaDraft`, `PersonaBuilder`; content-hashed media storage.
- PostgreSQL + `pgvector` persistence: ORM factory (dims from `Config`), engine,
  async + sync repository, Fernet-encrypted vault — integration-tested on a live DB.
- AI extraction **seam** (`extraction.py`) — signatures only, `NotImplementedError`.

Specs: `2026-06-01`, `2026-06-02`, `2026-06-04`. Plans: `docs/superpowers/plans/`.

---

## Phase 1 — Structured generation ✅ (offline, no external API)

The deterministic, offline half of AI generation. Spec:
`specs/2026-06-06-persona-genesis-structured-generation-design.md`.

- `PersonaGenerator(config, *, geolocator=None, llm=None, image=None)`.
  - `agenerate_structured(seed, locale=None, *, constraints=None) -> PartialPersona`
    (+ sync `generate_structured`) — fills `identity`, `location`, `work`, `device`;
    leaves `contact = Contact()` and narrative sections `None`.
  - `afill_structured(builder)` (+ sync) — generate only the structured sections in
    `builder.missing()`, never overwriting caller-set fields.
  - `agenerate(...) -> Persona` exists but raises `ConfigError` until an LLM provider
    is wired (Phase 2).
- Section generators: `identity` (Faker, locale-aware), `location` (bundled real-city
  dataset, or GeoIP from an `ip` constraint), `work` (curated occupation→industry +
  Faker employer + age-coherent seniority), `device` (curated `ua_pool` profile).
- Bundled data assets: `data/locations/<locale>.json`, `data/ua_pool.json`,
  `data/occupations.json`.
- GeoIP: `GeoLocator` protocol + `GeoIP2Locator` (caller supplies the GeoLite2
  `.mmdb` via `Config.geoip_database_path`; `geoip2` is the `[geoip]` extra).
- `LLMProvider` / `ImageProvider` **protocols** defined as the Phase 2/3 seam (no
  adapters yet).
- Deterministic from `seed`; coherence by construction (age → eligible seniority).

---

## Phase 2 — Narrative layer (LLM) ✅ (DeepSeek; verified live 2026-06-10)

Generate `personality`, `appearance` (text), `backstory`, `voice` (text) from an LLM,
feeding the structured fields as ground truth.

- ✅ Narrative generators behind `LLMProvider`; `agenerate()`/`generate()` return a
  complete strict `Persona`. Verified end-to-end against DeepSeek (live `--level 2`
  test green; narrative coherent with structured ground truth).
- ✅ **Coherence pass**: backstory chronology, age vs. seniority — one retry on
  violation, else `CoherenceError`. *(Remaining checks below are deferred follow-ups.)*
- ✅ Narrative fields tagged `status="gen"`.
- ✅ openai-compat adapter (`OpenAICompatProvider`, raw httpx, DeepSeek default) +
  `FakeLLMProvider` + `build_llm_provider(config)` factory; cost-tiered live tests
  (`pytest --level 0/1/2`).
- ✅ **`RecordedProvider`** — record-once / replay LLM exchanges to a JSON cassette;
  the full `agenerate()` path is snapshot-tested offline, deterministically, at
  `--level 0` with no per-run API cost (committed cassette recorded live for
  `seed=1`/`en_US`).
- ✅ Further coherence checks: UA vs. device (user agent must carry the OS/browser
  token) and appearance text vs. structured fields (hair/eye colour contradiction,
  explicit `NNN cm` height mismatch, build-word vs. `build`) — conservative, zero
  false positives across live seeds/locales.
- ⏳ Coherence: locale vs. name/voice — deferred; reliable detection needs a
  name-origin dataset / language detection, not deterministic string logic.
- ⏳ Fix: life-event years anchor a year before `dob.year` because the prompt passes
  `age`, not the birth year — `agenerate` retries spuriously. Add `born: {dob.year}`
  to the prompt (and re-record the cassette).
- 🔒 Additional provider adapters: Anthropic, OpenAI, other openai-compat backends
  (Ollama/vLLM/OpenRouter) behind optional extras. *Blocked on respective API keys
  to verify.*

## Phase 3 — Visual & biometric generation 🔭 🔒 (next; needs an image provider)

Generate face/body imagery and their embeddings behind `ImageProvider`.

- Visual layer: face image (and optional body image) from the appearance description;
  saved to disk with an `ai_generated` `MediaOrigin`; `Face`/`Body` embeddings
  recorded. `create_image()` (reference-conditioned) per the 2026-06-02 design.
- Image adapters: fal, replicate, OpenAI images, local diffusers (`[local-image]`).
  *Blocked on provider credentials.*

## Phase 4 — AI extraction ⏳ 🔒

Implement the `extraction.py` stubs and the embedding-from-media builder API.

- `extract_faces` (ArcFace/FaceNet), `extract_body` (person-ReID), `extract_voice`
  (ECAPA-TDNN), `transcribe` (ASR + diarization), `describe_image` (CLIP/caption),
  `score_nsfw`, `embed_text`.
- Builder embedding-from-media (roadmap item formerly #2): `add_face(image=…)`,
  `add_voice(audio=…)`, `add_document(file=…)` derive embeddings via the seam, store
  the source media, and create the links; unify with the existing `extract=True`
  path. Extraction artifacts tagged `status="gen"`.
- Extraction-provider config block in `Config`. *Blocked on models.*

## Phase 5 — Database deduplication ⏳

Identical binaries/documents map to a single shared row (on-disk storage already
content-hashes).

- Media: UNIQUE index on `file_path` (already `<kind>/<sha256>.<ext>`); `add_image/
  audio/video` and `save_draft` upsert-by-hash (`INSERT … ON CONFLICT`) and just add
  links. Shared across personas via the existing junctions.
- Documents: a `content_hash` column + UNIQUE; reuse the existing document, add the
  `document↔persona` link.
- Embeddings: dedupe by *source media hash* (same photo → reuse the `Face` row), not
  by vector equality (near-duplicates differ; similarity stays a `search`).
- Open: global vs per-persona scope (global matches the decoupled design); GC of
  orphaned rows/files; first real Alembic migration.

## Phase 6 — CLI ⏳

`persona-genesis generate / batch / image / validate` wrapping the generator,
repository, and media save. The CLI is the only filesystem-touching surface beyond
media storage.

---

## Cross-cutting follow-ups

- **Alembic migrations** (replace `create_all`) — prerequisite for Phase 5.
- **Video extraction** composing the image (per-frame faces) + audio (track voices)
  pipelines.
- **Partial-section round-trip**: builder produces incomplete strict-model sections;
  `get`/`get_partial` currently expect complete sections — read with `model_construct`
  or relax section validation. (See project memory note.)
- **pgvector ANN index tuning** (IVFFlat/HNSW) once data volumes are known.

---

## Dependency order

```
Phase 0 (done)
   └─ Phase 1  structured generation        (offline, now)
        └─ Phase 2  narrative (LLM)          (needs LLM key)
             └─ Phase 3  visual/biometric    (needs image key)
   └─ Phase 4  AI extraction                 (needs models; enables builder add_*(media=…))
   └─ Phase 5  DB dedup                      (needs Alembic)
   └─ Phase 6  CLI                           (after generator usable)
```
