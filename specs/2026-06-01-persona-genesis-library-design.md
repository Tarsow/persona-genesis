# persona-genesis — Standalone Python Library Design

**Date:** 2026-06-01
**Status:** Approved
**Scope:** Standalone Python library that generates highly detailed, coherent personas (structured + narrative + visual). Lives in its own git repo, imported by mimicos-ai as a dependency. Library is pure-generator: no DB, no storage, no infra dependencies.

## 1. Context

Mimicos.ai needs unique, detailed personas — names, addresses, DOBs, user agents, personalities, work histories, appearance descriptions, faces, optional body images, and the ability to render arbitrary in-context images of a persona. Rather than embedding this in the mimicos monorepo, it lives as its own library so it is:

- Reusable outside mimicos (other projects, CLI use, research).
- Independently versioned and testable.
- Forced into a clean public API contract via the dependency boundary.

The mimicos `packages/core/personas/` directory becomes a thin consumer wrapper around this library.

## 2. Locked decisions

| Area | Decision |
|---|---|
| Package name | `persona-genesis` (PyPI), `persona_genesis` (import) |
| Repo | Separate repo (e.g. `github.com/tarsow/persona-genesis`). Not on PyPI in v0.1. Consumed via git URL pin. |
| License | MIT |
| Python | 3.12+ |
| API style | Async-first with sync wrapper (`agenerate` + `generate`) |
| Scope | Pure generator: returns Pydantic `Persona` and `PIL.Image.Image`. No DB, no file I/O except the CLI. |
| Provider model | Provider-agnostic with built-in adapters |
| Determinism | Seeded RNG for structured fields. LLM/image determinism is best-effort. |
| Image format in-memory | `PIL.Image.Image` |
| Local diffusers | `[local-image]` optional extra |

## 3. Public API

### 3.1 Core entry points

```python
from persona_genesis import PersonaGenerator, Config, Persona

gen = PersonaGenerator(config=Config.from_env(), locale="pt_BR")

persona: Persona = await gen.agenerate(
    seed=42,
    constraints={"age_range": (25, 35), "device": "android"},
    include={"face_image", "body_image", "voice_sample"},
)

persona_sync = gen.generate(seed=42, ...)   # thin asyncio.run() wrapper

img: PIL.Image.Image = await gen.agenerate_image(
    persona=persona,
    scene="standing in their home office, soft afternoon light",
    aspect="9:16",
)
```

### 3.2 The `Persona` Pydantic model (contract)

This is the library's most important deliverable — every consumer (mimicos and others) reads from this shape.

```python
class Persona(BaseModel):
    id: UUID
    seed: int | None
    locale: str

    identity: Identity              # full_name, given_name, family_name, gender, dob, nationality
    location: Location              # country, region, city, street, postal_code, timezone
    contact: Contact                # phone format (no real number), email handle
    work: Work                      # occupation, employer, seniority, industry, schedule
    appearance: Appearance          # narrative + structured (hair, eyes, build, height_cm, distinguishing_features)
    personality: Personality        # OCEAN scores + descriptive traits + values + quirks
    voice: Voice                    # writing_style, posting_cadence, typical_topics, sample_paragraph
    device: Device                  # primary_device, os, browser, user_agent, screen_resolution
    backstory: Backstory            # bio, education, key_life_events

    images: PersonaImages = Field(default_factory=PersonaImages)
    # face_image, body_image — each Optional[PIL.Image.Image] (excluded from JSON serialization
    # by default; consumers convert/save explicitly)

    metadata: PersonaMetadata       # generated_at, generator_version, provider_versions
```

Sub-models live in `schema/`. All fields use precise types (`date`, `Decimal`, `Literal` enums where applicable). JSON serialization round-trips losslessly except for image fields.

### 3.3 Provider protocols

```python
class LLMProvider(Protocol):
    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str: ...
    async def acomplete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel: ...

class ImageProvider(Protocol):
    async def agenerate(self, prompt: str, *, aspect: str = "1:1", seed: int | None = None) -> PIL.Image.Image: ...
```

Users can pass custom instances directly: `PersonaGenerator(llm=MyLLM(), image=MyImageGen())`.

## 4. Architecture

```
PersonaGenerator (orchestrator)
        │
        ├── structured layer ── Faker, Polyfactory, fake-useragent (deterministic)
        │       generates: identity, location, contact, work, device
        │
        ├── narrative layer ──► LLMProvider
        │       generates: personality, appearance (text), backstory, voice
        │       inputs structured fields as ground truth
        │
        ├── visual layer ─────► ImageProvider
        │       generates: face_image, body_image, custom images
        │       inputs appearance description + persona context
        │
        └── coherence pass ── validates cross-field consistency; one retry on failure
```

**Generation order** (sequential where dependencies exist, concurrent where independent):

1. Structured layer (deterministic from seed) — single pass.
2. Narrative layer — LLM call(s). Personality, appearance description, backstory, voice can run in one structured-output call or split for clarity.
3. Visual layer — image calls run concurrently when multiple images requested.
4. Coherence pass — runs validators; if any fail, re-runs the offending generator with the violation in the prompt; raises after one retry.

## 5. Repo layout

```
persona-genesis/
├── src/persona_genesis/
│   ├── __init__.py              # re-exports public API
│   ├── schema/
│   │   ├── persona.py           # top-level Persona
│   │   ├── identity.py
│   │   ├── location.py
│   │   ├── contact.py
│   │   ├── work.py
│   │   ├── appearance.py
│   │   ├── personality.py
│   │   ├── voice.py
│   │   ├── device.py
│   │   ├── backstory.py
│   │   ├── images.py            # PersonaImages container
│   │   └── metadata.py
│   ├── generators/
│   │   ├── base.py              # Generator protocol
│   │   ├── structured/
│   │   │   ├── identity.py
│   │   │   ├── location.py
│   │   │   ├── contact.py
│   │   │   ├── work.py
│   │   │   └── device.py        # device + UA pool
│   │   ├── narrative/
│   │   │   ├── personality.py
│   │   │   ├── appearance.py
│   │   │   ├── backstory.py
│   │   │   └── voice.py
│   │   └── visual/
│   │       ├── face.py
│   │       ├── body.py
│   │       └── custom.py
│   ├── providers/
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── anthropic.py
│   │   │   ├── openai.py
│   │   │   └── openai_compat.py # Ollama / OpenRouter / vLLM / LM Studio
│   │   └── image/
│   │       ├── base.py
│   │       ├── replicate.py
│   │       ├── fal.py
│   │       ├── openai_image.py
│   │       └── diffusers_local.py   # [local-image] extra
│   ├── orchestrator.py          # PersonaGenerator
│   ├── coherence.py             # cross-field validators
│   ├── config.py                # Config + Config.from_env()
│   ├── prompts/                 # versioned prompt templates as .md files
│   │   ├── personality.md
│   │   ├── appearance.md
│   │   ├── backstory.md
│   │   ├── voice.md
│   │   ├── face_image.md
│   │   ├── body_image.md
│   │   └── custom_image.md
│   ├── ua_pool.py               # curated UA strings by device+OS+browser
│   ├── exceptions.py            # PersonaGenerationError, CoherenceError, ProviderError
│   └── cli.py                   # `persona-genesis generate ...`
├── tests/
│   ├── unit/
│   ├── integration/             # hits real providers, gated by env vars
│   └── fixtures/
├── examples/
│   ├── basic.py
│   ├── batch_concurrent.py
│   ├── custom_provider.py
│   └── local_llm_ollama.py
├── docs/
├── pyproject.toml               # uv-managed, hatchling backend
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .env.example
├── .gitignore
└── .github/workflows/ci.yml
```

## 6. Configuration

`.env` (read by `Config.from_env()` via `pydantic-settings`):

```
PERSONA_LLM_PROVIDER=anthropic              # anthropic | openai | openai_compat
PERSONA_LLM_API_KEY=...
PERSONA_LLM_MODEL=claude-opus-4-7
PERSONA_LLM_BASE_URL=                       # only for openai_compat (e.g. http://localhost:11434/v1)
PERSONA_LLM_TIMEOUT_S=60
PERSONA_LLM_MAX_RETRIES=2

PERSONA_IMAGE_PROVIDER=fal                  # fal | replicate | openai | diffusers_local
PERSONA_IMAGE_API_KEY=...
PERSONA_IMAGE_MODEL=fal-ai/flux/schnell
PERSONA_IMAGE_TIMEOUT_S=120

PERSONA_DEFAULT_LOCALE=en_US
PERSONA_LOG_LEVEL=INFO
```

Programmatic config:

```python
Config(
    llm=LLMConfig(provider="anthropic", api_key="...", model="claude-opus-4-7"),
    image=ImageConfig(provider="fal", api_key="...", model="fal-ai/flux/schnell"),
    default_locale="pt_BR",
)
```

Explicit constructor args always override `.env`. Missing required keys raise `ConfigError` at `PersonaGenerator` construction, not at generation time.

## 7. Coherence validation

After narrative + visual passes, run validators:

- **Age vs. occupation seniority** — a 22-year-old cannot be a CTO. Lookup table of `(seniority, min_years_experience)`.
- **Locale vs. native-language style** — Brazilian persona's `voice.writing_style` should imply pt-BR habits.
- **Device vs. user agent** — UA string must match device model and OS chosen by structured layer.
- **Appearance text vs. structured fields** — narrative `appearance.description` cannot contradict `appearance.hair_color`, `appearance.height_cm`, etc.
- **Backstory continuity** — events ordered correctly; education completes before first job.

On failure: re-run the failing generator with violations included in the prompt as constraints. One retry max, then raise `CoherenceError`.

## 8. Determinism

- Structured layer: fully deterministic given `seed` (Faker accepts a seed; Polyfactory honors it; UA pool uses seeded RNG).
- Narrative layer: best-effort. Pass `seed` to providers that accept it (OpenAI does, Anthropic does not yet). Cache prompts so the same `(seed, prompt, model_version)` returns the same value for tests.
- Visual layer: provider-dependent. Most diffusion APIs accept a seed. Library passes it through; consumers should not rely on byte-identical images across runs.

For full reproducibility in tests, use the `RecordedProvider` adapter (records outputs to disk on first run, replays on subsequent runs) — ships with the library.

## 9. CLI

```
persona-genesis generate \
    --locale pt_BR \
    --seed 42 \
    --include face_image,body_image \
    --out persona.json \
    --image-dir ./images/
```

Outputs `persona.json` (Pydantic-serialized) and `persona-{id}-face.png` / `persona-{id}-body.png` in `--image-dir`. The CLI is the *only* part of the library that touches the filesystem.

Other commands:

```
persona-genesis batch --count 100 --concurrency 8 --out-dir ./personas/
persona-genesis image --persona persona.json --scene "..." --out custom.png
persona-genesis validate --persona persona.json
```

## 10. Dependencies

**Core (required):**
- `pydantic>=2.6`
- `pydantic-settings>=2.2`
- `faker>=24`
- `polyfactory>=2.15`
- `fake-useragent>=1.5`
- `httpx>=0.27` (for provider HTTP)
- `Pillow>=10`
- `anyio>=4` (sync/async bridge)

**Optional extras:**
- `[anthropic]` → `anthropic>=0.40`
- `[openai]` → `openai>=1.40`
- `[local-image]` → `torch>=2.3`, `diffusers>=0.27`, `transformers>=4.40`, `accelerate>=0.30`
- `[cli]` → `typer>=0.12`, `rich>=13`
- `[all]` → everything above

Default install: only core. Users opt in to providers they actually use.

## 11. Out of scope for v0.1

- Voice/audio synthesis (text writing-style sample only)
- Video generation
- Persona families / relationships (siblings, coworkers, partners)
- Lifecycle simulation (aging, life events over time)
- Multi-image consistency (same face across many scenes) — defer to v0.2 with IP-Adapter / FaceID
- DB / storage adapters
- Streaming / partial generation (every `agenerate` returns a complete Persona)

## 12. Integration with mimicos-ai

mimicos consumes the library via git pin until persona-genesis publishes to PyPI:

```toml
# packages/core/pyproject.toml
[project]
dependencies = [
    "persona-genesis @ git+https://github.com/tarsow/persona-genesis@v0.1.0",
]
```

mimicos's `packages/core/personas/` shrinks to a thin wrapper that:

1. Calls `PersonaGenerator.agenerate()`.
2. Persists the returned `Persona` to Postgres (`personas` table, JSONB column for the bulk).
3. Saves images to object storage or local disk, stores URIs on the persona row.
4. Adds mimicos-specific concerns: linking persona ↔ `accounts` (gmail, instagram), tracking lifecycle state, scheduling activity.

The platform spec (`2026-05-29-mimicos-platform-structure-design.md`) needs a small amendment to reflect this — `core` no longer owns persona *generation*; it owns persona *persistence and lifecycle* and consumes the library for generation. The `Persona` Pydantic schema becomes the library's contract.

## 13. Testing strategy

- **Unit tests** — every generator and provider mocked. Schema round-trip tests for Pydantic.
- **Integration tests** — hit real providers, gated behind env vars (`PERSONA_GENESIS_RUN_INTEGRATION=1`). Cost-budgeted: small fixed number of generations per CI run.
- **Snapshot tests** — `RecordedProvider` captures real provider outputs once; later runs replay. Detects schema drift and prompt regressions without per-run cost.
- **Coherence tests** — explicit cases (22-year-old CTO, locale/UA mismatch) verify validators fire and retry logic works.

CI: GitHub Actions, Python 3.12 + 3.13 matrix, ruff + mypy + pytest, no real providers by default.

## 14. Versioning and release

- Semver from v0.1.0.
- Breaking changes to the `Persona` schema = major bump.
- Provider adapter additions = minor bump.
- Bugfixes = patch bump.
- Changelog kept in `CHANGELOG.md`, Keep-a-Changelog format.
- Git tags = source of truth. mimicos pins to specific tags.

## 15. Follow-up specs

- Initial implementation plan (v0.1 milestone: structured layer + Anthropic LLM + fal images + Pydantic schema + CLI).
- Coherence validator catalog (full list of rules with code references).
- Prompt template specs for personality / appearance / backstory / voice.
- v0.2 spec: multi-image consistency (IP-Adapter / FaceID), persona families.
