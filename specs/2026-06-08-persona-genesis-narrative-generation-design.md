# persona-genesis — Narrative Generation Layer (LLM)

**Date:** 2026-06-08
**Status:** Approved
**Phase:** Roadmap Phase 2 (`docs/roadmap.md`)
**Builds on:** `specs/2026-06-06` (PersonaGenerator + structured layer), `specs/2026-06-01`
(narrative-layer concept), `specs/2026-06-04` (`_status` provenance, section models).

## 1. Context

Phase 1 made `PersonaGenerator.generate_structured()` fill `identity`/`location`/`work`/
`device`. Phase 2 adds the **LLM-driven narrative layer** — `personality`, `appearance`,
`backstory`, `voice` — so `agenerate()` returns a complete strict `Persona`. The primary
provider is **DeepSeek** (cheapest), reached through a generic OpenAI-compatible adapter.

## 2. Provider layer

### 2.1 `OpenAICompatProvider` (`providers/openai_compat.py`)

Raw `httpx` client for the OpenAI-compatible `/chat/completions` API (no SDK
dependency). Works with DeepSeek, OpenAI, Ollama, OpenRouter, vLLM via `base_url`.

```python
class OpenAICompatProvider:
    def __init__(self, *, api_key: str, model: str = "deepseek-chat",
                 base_url: str = "https://api.deepseek.com", timeout_s: int = 60,
                 max_retries: int = 2, http_client: "httpx.AsyncClient | None" = None) -> None: ...

    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str: ...
    async def acomplete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel: ...
```

- `acomplete`: `POST {base_url}/chat/completions` with `messages=[{system},{user}]`,
  `model`, `temperature`; returns `choices[0].message.content`.
- `acomplete_json`: same call with `response_format={"type": "json_object"}` and the
  target JSON schema (`schema.model_json_schema()`) appended to the system prompt;
  parses the returned content as JSON and `schema.model_validate`s it. On
  `JSONDecodeError`/`ValidationError`, re-requests (appending a "your last output was
  invalid, return valid JSON matching the schema" note) up to `max_retries`, then
  raises `ProviderError`. Non-2xx responses and timeouts raise `ProviderError`.
- `http_client` is injectable so tests pass an `httpx.AsyncClient(transport=httpx.MockTransport(...))`;
  when `None`, a client is created per request with `timeout_s`.

### 2.2 `FakeLLMProvider` (`providers/fake_llm.py`)

Offline test/dev double implementing `LLMProvider`.

```python
class FakeLLMProvider:
    def __init__(self, *, payloads: list[BaseModel | dict] | None = None, text: str = "ok") -> None: ...
    async def acomplete(self, system, user, *, temperature=0.7) -> str: ...        # -> text
    async def acomplete_json(self, system, user, schema) -> BaseModel: ...          # -> next payload
```

`acomplete_json` returns successive entries from `payloads` (the last entry repeats),
so a test can pass `[incoherent, coherent]` to exercise the coherence retry, or
`[incoherent, incoherent]` to force `CoherenceError`. A dict entry is
`schema.model_validate`d.

### 2.3 `build_llm_provider(config)` + Config

`build_llm_provider(config: Config) -> LLMProvider` constructs `OpenAICompatProvider`
for providers `deepseek`/`openai`/`openai_compat` (default `base_url`:
`https://api.deepseek.com` for deepseek, `https://api.openai.com/v1` for openai;
`openai_compat` requires `config.llm.base_url`). Missing `api_key`/`base_url` →
`ConfigError`. `anthropic` → `ConfigError` ("not yet implemented") — deferred.

`LLMProviderName` gains `"deepseek"`. **`LLMConfig` defaults change** to
`provider="deepseek"`, `model="deepseek-chat"` (reflecting the current focus); the two
existing `test_config` assertions about the old defaults are updated.

## 3. Narrative generation

### 3.1 `NarrativePayload` (`generators/narrative/payload.py`)

The LLM's output schema — section *content* only, **no `_status`**:

```python
class PersonalityPayload(BaseModel):
    ocean: OceanScores
    traits: list[str]; values: list[str]; quirks: list[str]

class AppearancePayload(BaseModel):
    description: str
    hair_color: str; hair_style: str; eye_color: str
    build: Build; height_cm: int = Field(gt=0, le=260)
    distinguishing_features: list[str]

class BackstoryPayload(BaseModel):
    bio: str; education: list[Education]; key_life_events: list[LifeEvent]

class VoicePayload(BaseModel):
    writing_style: str; posting_cadence: str
    typical_topics: list[str]; sample_paragraph: str

class NarrativePayload(BaseModel):
    personality: PersonalityPayload
    appearance: AppearancePayload
    backstory: BackstoryPayload
    voice: VoicePayload
```

`OceanScores`, `Education`, `LifeEvent`, `Build` are reused from the schema (they carry
no `_status`).

### 3.2 `NarrativeGenerator` (`generators/narrative/narrative.py`)

```python
class NarrativeGenerator:
    def __init__(self, llm: LLMProvider) -> None: ...
    async def generate(self, partial: PartialPersona, *, violations: list[str] | None = None
                       ) -> dict[str, Any]: ...   # {"personality","appearance","backstory","voice"}
```

- System prompt = `prompts/narrative.md` (bundled, loaded via `importlib.resources`).
- User prompt = the structured ground truth (`identity`, `location`, `work`, `device`,
  `locale`, age) rendered compactly, plus, when retrying, the `violations` to fix.
- Calls `llm.acomplete_json(system, user, NarrativePayload)`.
- Maps the payload → section models with **`status="gen"` on every field** — notably
  overriding `Appearance`'s structured-field defaults (`fake` → `gen`), since the LLM
  generated them.

The prompt instructs the model to keep `appearance.description` consistent with the
structured appearance fields and `voice` consistent with `locale` (fuzzy coherence is
prompt-enforced, not validated — §4).

### 3.3 Prompt asset

`src/persona_genesis/prompts/narrative.md` — a versioned system prompt, bundled in the
wheel (hatch force-include, like `data/`).

## 4. Coherence (`coherence.py`)

Deterministic validators returning a list of human-readable violation strings:

```python
def check_persona(persona: Persona) -> list[str]: ...
```

- **Age vs seniority:** `MIN_YEARS_EXPERIENCE[work.seniority] <= max(0, age - 22)`
  (`MIN_YEARS_EXPERIENCE` is promoted from `generators/work.py` to a shared public map
  and reused by both the work generator and this check).
- **Backstory chronology:** each `Education.start_year <= end_year` (when `end_year`
  set); every education/life-event year within `[dob.year, current_year]`; life-event
  years non-decreasing.

Fuzzy semantic coherence (appearance text ↔ structured fields, voice ↔ locale) is
**not** validated here — it is steered by the prompt. No extra LLM critique call.

## 5. `agenerate()` / `generate()`

```python
async def agenerate(self, seed: int, locale: str | None = None, *,
                    constraints: StructuredConstraints | None = None,
                    include: set[str] | None = None) -> Persona:
    if self._llm is None:
        raise ConfigError("an LLM provider is required to generate narrative sections")
    partial = self.generate_structured(seed, locale, constraints=constraints)
    narrative = NarrativeGenerator(self._llm)
    violations: list[str] | None = None
    for _ in range(2):                       # initial attempt + one retry
        sections = await narrative.generate(partial, violations=violations)
        persona = self._assemble(partial, sections)
        violations = check_persona(persona)
        if not violations:
            return persona
    raise CoherenceError("narrative", violations or [])
```

- `_assemble(partial, sections)` builds a strict `Persona` from the structured partial
  (`id`, `seed`, `locale`, `identity`, `location`, `contact`, `work`, `device`) + the
  four narrative sections + a `PersonaMetadata` (`generated_at=now(UTC)`,
  `generator_version=__version__`, `provider_versions={"llm": <model>}`). `contact`
  stays `Contact()` (real-only).
- `generate(...)` is the sync wrapper (`anyio.run` of `agenerate`).
- `include=` (face/body images) remains a Phase-3 no-op (ignored for now).

## 6. Public API

Re-export `OpenAICompatProvider`, `FakeLLMProvider`, and `build_llm_provider`.
`PersonaGenerator`, `LLMProvider`, `CoherenceError`, `ConfigError`, `ProviderError`
are already exported.

## 7. Tiered, cost-controlled testing (`--level`)

`conftest.py` adds a `--level` option (int, **default 0**) and registers a
`@pytest.mark.llm(level=N)` marker; `pytest_collection_modifyitems` **skips** any test
whose required level exceeds the chosen `--level`.

- **Level 0** (default; what CI runs): no network. The provider (`httpx.MockTransport`),
  `NarrativeGenerator` + `FakeLLMProvider`, coherence, and `agenerate()` (via
  `FakeLLMProvider`) are fully exercised. Costs nothing.
- **Level 1** (`@pytest.mark.llm(level=1)`): one tiny real DeepSeek `acomplete` "ping"
  proving the live adapter works. Minimal tokens.
- **Level 2** (`@pytest.mark.llm(level=2)`): one or two full real `agenerate()` runs
  end-to-end through DeepSeek. Bounded, reasonable cost.

The DeepSeek key is read **only in the test harness** (the library never reads env):
`conftest.py` loads `.env` and reads `DEEPSEEK_API_KEY`. A `deepseek_config` /
`llm_provider` fixture builds a real `OpenAICompatProvider`; if the key is absent,
level ≥ 1 tests **skip** with a clear message even when `--level` is set. The library
itself remains injected-config-only.

## 8. Testing strategy (detail)

- **Provider (level 0):** `acomplete` returns content; `acomplete_json` parses
  `json_object` content into the schema; malformed JSON triggers retry then
  `ProviderError`; non-2xx → `ProviderError` — all via `httpx.MockTransport`.
- **NarrativeGenerator (level 0):** with `FakeLLMProvider`, maps a payload → sections
  with `status="gen"` (including appearance structured fields).
- **Coherence (level 0):** detects backstory chronology + age/seniority violations;
  a clean persona yields `[]`.
- **agenerate (level 0):** `FakeLLMProvider([coherent])` → complete `Persona` with
  narrative `status="gen"` and `contact == Contact()`; `FakeLLMProvider([incoherent,
  coherent])` → succeeds on retry; `[incoherent, incoherent]` → `CoherenceError`;
  no `llm` → `ConfigError`; sync `generate()` matches `agenerate()`.
- **build_llm_provider (level 0):** deepseek/openai/openai_compat → `OpenAICompatProvider`
  with correct base_url; missing key/base_url → `ConfigError`; anthropic → `ConfigError`.
- **Live (gated):** level 1 ping; level 2 full `agenerate()` returns a valid `Persona`.

## 9. Dependencies, layout, lands-now vs deferred

- No new runtime dependencies (`httpx`/`anyio` already core).
- New files: `providers/openai_compat.py`, `providers/fake_llm.py`,
  `providers/factory.py` (`build_llm_provider`), `generators/narrative/{__init__,payload,narrative}.py`,
  `prompts/narrative.md`, `coherence.py`; modified `orchestrator.py`, `config.py`,
  `generators/work.py` (expose `MIN_YEARS_EXPERIENCE`), `__init__.py`, `conftest.py`.

**Now:** OpenAI-compatible (DeepSeek) adapter + fake provider + factory, narrative
payload/generator + prompt, coherence pass, working `agenerate()`/`generate()`, tiered
testing.

**Deferred:** Anthropic adapter, visual/biometric generation (`include=` images,
Phase 3), `RecordedProvider` snapshot tests, additional coherence rules, prompt-template
versioning beyond a single `narrative.md`.

## 10. Follow-up

Phase 3 (visual/biometric) wires `ImageProvider` and the `include=` image path; later
phases per `docs/roadmap.md`.
