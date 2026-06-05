# persona-genesis — Roadmap

Forward-looking design notes for the next initiatives. These are **planning
sketches**, not final specs — each should get a proper brainstorm → spec → plan pass
(per the project workflow) before implementation. Concrete, locked design lives in
`specs/`; this file captures intent, direction, and open questions.

Status legend: 🔭 designed-only · 🚧 in progress · ✅ done.

---

## 1. AI generation (`PersonaGenerator`) 🔭

**Goal.** Generate complete, coherent personas instead of hand-building them. The
original library design (`specs/2026-06-01-persona-genesis-library-design.md`)
specified this; it was deferred while the data layer landed.

**Shape.**
- `PersonaGenerator(config, llm=…, image=…)` with `agenerate(seed, constraints,
  include=…)` (async-first) and a thin `generate()` sync wrapper.
- `afill(builder)` / `fill(builder)` — generate only the sections in
  `builder.missing()`, treating caller-set fields as ground truth, returning a
  complete strict `Persona`.
- Layers: **structured** (Faker/Polyfactory/fake-useragent → identity, location,
  work, device — deterministic from `seed`), **narrative** (LLM → personality,
  appearance text, backstory, voice text), **visual/biometric** (image + embedding
  providers → faces/bodies/voices), and a **coherence pass** (age vs. seniority,
  locale vs. name, UA vs. device, appearance text vs. structured fields) with one
  retry.

**Provenance integration (already in the contract).** Generated fields must set
`_status` per the realism rule already implemented: caller-set → `real`, derived
from real data (address from IP, real geo) → `gen`, LLM narrative → `gen`, AI
embeddings → `gen`, Faker-invented (name/dob/fake phone/email/device) → `fake`. A
generated persona keeps `Contact == Contact()` and `location.street/postal_code`
empty unless an IP is supplied.

**Provider seam.** `LLMProvider` / `ImageProvider` protocols with built-in adapters
(Anthropic, OpenAI, fal, replicate, local diffusers) behind optional extras. Config
already carries `llm`/`image` blocks.

**Open questions.**
- Determinism contract for narrative/visual layers (best-effort; `RecordedProvider`
  for tests?).
- Does `agenerate` persist, or only return the `Persona`/`PersonaDraft` for the
  caller to `save_draft`? (Likely the latter — keep the generator pure.)
- How constraints (`age_range`, `device`, locale) flow into each layer.

---

## 2. Embedding-from-media in the builder 🔭

**Goal.** Today `add_face`, `add_voice`, and `add_document` accept **pre-computed**
embeddings. Allow them to also accept **raw media** and derive the embedding via the
extraction seam (`extraction.py`, currently `NotImplementedError` stubs).

**Target API (additive — keep the pre-computed path).**
```python
b.add_face(image=img)                 # PIL/bytes → store image, run extract_faces → Face(s) + link
b.add_face(embedding=[...])           # unchanged: caller-supplied vector
b.add_voice(audio=data, media_type="audio/wav")   # → transcribe + extract_voice → VoicePrint + link
b.add_document(file=path_or_bytes)    # extract text → embed_text → Document.embedding
b.add_document(content="...", embedding=[...])     # unchanged
```
- `add_face(image=…)` should also store the image as an `Image` row and create the
  `image↔face` link (one call attaches the photo and its biometric).
- `add_voice(audio=…)` stores the `Audio`, transcribes to `text`, and links
  `audio↔voice`.
- Extraction-produced artifacts are tagged `status="gen"`; caller-supplied stay
  `real`.
- The existing `add_image(..., extract=True)` / `add_audio(..., extract=True)` flags
  already model the auto-extract path; unify the two so `add_face(image=…)` and
  `add_image(extract=True)` share one extraction code path.

**Depends on.** The extraction implementations (initiative tied to #1's visual
layer): `extract_faces`, `extract_voice`, `transcribe`, `describe_image`,
`score_nsfw`, `embed_text`, plus extraction-provider config in `Config`.

**Open questions.**
- Sync vs async: extraction may call remote models. The builder is currently sync;
  either add async builder methods (`aadd_face`) or run extraction at `save`/generate
  time rather than in `add_*`.
- Where extraction providers are configured (new `Config.extraction` block:
  face/voice/caption/embedding model + endpoint + key).
- Multiple faces in one image → multiple `Face` rows + links (already supported by
  the schema).

---

## 3. Database deduplication 🔭

**Goal.** Identical binaries and documents should map to a **single row**, shared
across personas — not duplicated on every attach. On-disk storage already dedupes
(content-hash filename: `media/storage.store_media`), so two identical uploads share
one file; the database layer should mirror that.

**Approach.**
- **Media (images/audio/video).** The stored `file_path` is `"<kind>/<sha256>.<ext>"`
  — it already *is* a content key. Add a UNIQUE index on `file_path` per media table
  and make `add_image/add_audio/add_video` (and `save_draft`) **upsert by
  `file_path`**: if a row with that path exists, reuse its id and link, don't insert
  a duplicate. Because media is decoupled (no persona FK) and linked via junctions,
  the same image row can already be linked to many faces/personas — dedup just stops
  duplicate rows.
- **Documents.** Add a `content_hash` column (sha256 of `content`, or of
  `content` + normalized `metadata`), UNIQUE; `add_document` reuses an existing
  document and adds the `document↔persona` link instead of inserting a copy.
- **Embeddings (faces/bodies/voices).** Exact-byte dedup is wrong for vectors
  (near-duplicates differ). Dedup these by their **source media hash** when extracted
  via #2 (same photo → reuse the face row), not by embedding equality. Approximate
  "is this the same person/voice" stays a *search* (`search_faces`), not a dedup.

**Open questions.**
- Dedup scope: global (one row for identical bytes anywhere) vs per-persona. Global
  matches the decoupled/shareable design — confirm that's intended.
- Migration: the lands-now schema uses `create_all`; adding UNIQUE indexes +
  `content_hash` is the first real **Alembic** migration (already a noted follow-up).
- Concurrency: upsert-by-hash needs `INSERT … ON CONFLICT DO NOTHING/UPDATE` (psycopg
  supports it) to be race-safe under concurrent writers.
- Reference counting / GC: when the last link to a deduped media row is removed,
  should the row and on-disk file be deleted? (Probably a separate sweep, not inline.)

---

## Cross-cutting follow-ups (already noted in specs)

- Alembic migrations (replaces `create_all`) — prerequisite for #3.
- pgvector ANN index tuning (IVFFlat/HNSW) once data volumes are known.
- `Video` extraction composing the image (per-frame faces) + audio (track voices)
  pipelines.
- The `get_partial`/`get` round-trip of *partially*-set sections (builder produces
  incomplete strict-model sections; reader currently expects complete sections — use
  `model_construct` on read or relax section validation). See the project memory note.
