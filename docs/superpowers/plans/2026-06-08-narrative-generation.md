# Narrative Generation Layer — Implementation Plan (Phase 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `specs/2026-06-08-persona-genesis-narrative-generation-design.md`: an OpenAI-compatible (DeepSeek) LLM adapter, a fake provider, a combined narrative generator (personality/appearance/backstory/voice), a deterministic coherence pass, and a working `agenerate()`/`generate()` returning a complete `Persona`, plus cost-tiered tests via `--level`.

**Architecture:** `OpenAICompatProvider` (raw httpx) and `FakeLLMProvider` implement the existing `LLMProvider` protocol. `NarrativeGenerator` builds a prompt from the structured `PartialPersona`, calls `acomplete_json` for one `NarrativePayload`, and maps it to section models (`status="gen"`). `coherence.check_persona` runs deterministic validators. `PersonaGenerator.agenerate` composes structured → narrative → coherence (one retry) → `Persona`. Tests are tiered: level 0 offline (fake provider + `httpx.MockTransport`), levels 1–2 hit real DeepSeek (key from `.env`, test-only). TDD throughout.

**Tech Stack:** Python 3.12 · Pydantic 2 · httpx · anyio · pytest · pytest-asyncio · DeepSeek (OpenAI-compatible).

---

## Conventions

- Commit messages end with the body (no `Co-Authored-By`).
- `uv run` for everything; mypy strict on `src` and `tests`.
- The library never reads env/`.env`; only `tests/conftest.py` reads `DEEPSEEK_API_KEY`.
- Existing symbols: `LLMProvider` (`persona_genesis.providers.llm`), `Config`/`LLMConfig` (`persona_genesis.config`), `PersonaGenerator` (`persona_genesis.orchestrator`), section models + `Persona`/`PartialPersona`/`Contact`/`PersonaMetadata` (`persona_genesis.schema.*`), `ConfigError`/`ProviderError`/`CoherenceError` (`persona_genesis.exceptions`). `ProviderError(provider: str, message: str)`; `CoherenceError(rule: str, violations: list[str])`.

## File structure

```
src/persona_genesis/
  providers/openai_compat.py   # OpenAICompatProvider (httpx)
  providers/fake_llm.py        # FakeLLMProvider
  providers/factory.py         # build_llm_provider(config)
  generators/narrative/__init__.py
  generators/narrative/payload.py     # NarrativePayload + sub-payloads
  generators/narrative/narrative.py   # NarrativeGenerator
  prompts/__init__.py  prompts/narrative.md
  coherence.py                 # check_persona
  generators/work.py           # expose MIN_YEARS_EXPERIENCE (rename _MIN_YEARS)
  orchestrator.py              # agenerate/generate/_assemble
  config.py                    # add "deepseek"; default to deepseek
  __init__.py                  # re-exports
tests/conftest.py              # --level option + llm marker + .env + fixtures
tests/integration/test_llm_live.py   # level 1/2 gated
```

---

## Task 1: Config — DeepSeek provider + defaults

**Files:** Modify `src/persona_genesis/config.py`, `tests/unit/test_config.py`

- [ ] **Step 1.1: Update Config tests** — in `tests/unit/test_config.py`, change the default-provider assertions. In `test_defaults_match_spec` replace the llm provider/model assertions with:
```python
    assert cfg.llm.provider == "deepseek"
    assert cfg.llm.model == "deepseek-chat"
```
and in `test_from_dict_empty_uses_defaults` replace `assert cfg.llm.provider == "anthropic"` with:
```python
    assert cfg.llm.provider == "deepseek"
```

- [ ] **Step 1.2: Run** `uv run pytest tests/unit/test_config.py -q` → fails.

- [ ] **Step 1.3: Implement** — in `src/persona_genesis/config.py`:
  - change `LLMProviderName` to `Literal["anthropic", "openai", "openai_compat", "deepseek"]`.
  - in `LLMConfig`, change the defaults to `provider: LLMProviderName = "deepseek"` and `model: str = "deepseek-chat"`.

- [ ] **Step 1.4: Run + commit**
```bash
uv run pytest tests/unit/test_config.py -q
uv run mypy src/persona_genesis/config.py
git add src/persona_genesis/config.py tests/unit/test_config.py
git commit -m "feat(config): add deepseek provider and default to it"
```

---

## Task 2: OpenAICompatProvider (httpx)

**Files:** Create `src/persona_genesis/providers/openai_compat.py`, `tests/unit/test_openai_compat.py`

- [ ] **Step 2.1: Write failing tests** — `tests/unit/test_openai_compat.py`:
```python
import httpx
import pytest
from pydantic import BaseModel

from persona_genesis.exceptions import ProviderError
from persona_genesis.providers.openai_compat import OpenAICompatProvider


def _provider(handler: object, **kw: object) -> OpenAICompatProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
    return OpenAICompatProvider(api_key="k", http_client=client, **kw)  # type: ignore[arg-type]


async def test_acomplete_returns_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "pong"}}]})

    assert await _provider(handler).acomplete("s", "u") == "pong"


async def test_acomplete_json_parses_schema() -> None:
    class Out(BaseModel):
        x: int

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"x": 7}'}}]})

    out = await _provider(handler).acomplete_json("s", "u", Out)
    assert isinstance(out, Out) and out.x == 7


async def test_acomplete_json_retries_then_raises() -> None:
    class Out(BaseModel):
        x: int

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    with pytest.raises(ProviderError):
        await _provider(handler, max_retries=2).acomplete_json("s", "u", Out)
    assert calls["n"] == 3  # initial + 2 retries


async def test_http_error_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(ProviderError):
        await _provider(handler).acomplete("s", "u")
```

- [ ] **Step 2.2: Run** → ImportError.

- [ ] **Step 2.3: Implement** — `src/persona_genesis/providers/openai_compat.py`:
```python
"""OpenAI-compatible chat-completions provider (raw httpx). Default target: DeepSeek.
Works with OpenAI, Ollama, OpenRouter, vLLM via base_url."""

import json
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from persona_genesis.exceptions import ProviderError

_LABEL = "openai_compat"


class OpenAICompatProvider:
    def __init__(
        self, *, api_key: str, model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com", timeout_s: int = 60,
        max_retries: int = 2, http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._client = http_client

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        client = self._client or httpx.AsyncClient(timeout=self._timeout_s)
        try:
            resp = await client.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderError(_LABEL, f"request failed: {exc}") from exc
        finally:
            if self._client is None:
                await client.aclose()
        if resp.status_code >= 400:
            raise ProviderError(_LABEL, f"HTTP {resp.status_code}: {resp.text}")
        data: dict[str, Any] = resp.json()
        return data

    def _content(self, data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(_LABEL, f"unexpected response shape: {data}") from exc
        if not isinstance(content, str):
            raise ProviderError(_LABEL, "response content was not a string")
        return content

    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str:
        data = await self._post({
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
        })
        return self._content(data)

    async def acomplete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        sys = (
            f"{system}\n\nRespond ONLY with a single JSON object matching this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        last_err = ""
        for attempt in range(self._max_retries + 1):
            u = user if attempt == 0 else (
                f"{user}\n\nYour previous response was invalid ({last_err}). "
                "Return ONLY valid JSON matching the schema."
            )
            data = await self._post({
                "model": self.model,
                "messages": [{"role": "system", "content": sys}, {"role": "user", "content": u}],
                "response_format": {"type": "json_object"},
            })
            content = self._content(data)
            try:
                return schema.model_validate(json.loads(content))
            except (json.JSONDecodeError, ValidationError) as exc:
                last_err = str(exc)[:200]
        raise ProviderError(_LABEL, f"no valid JSON after {self._max_retries + 1} attempts: {last_err}")
```

- [ ] **Step 2.4: Run + mypy + commit**
```bash
uv run pytest tests/unit/test_openai_compat.py -q
uv run mypy src/persona_genesis/providers/openai_compat.py
git add src/persona_genesis/providers/openai_compat.py tests/unit/test_openai_compat.py
git commit -m "feat(providers): add OpenAICompatProvider (httpx, DeepSeek default)"
```

---

## Task 3: FakeLLMProvider

**Files:** Create `src/persona_genesis/providers/fake_llm.py`, `tests/unit/test_fake_llm.py`

- [ ] **Step 3.1: Write failing tests** — `tests/unit/test_fake_llm.py`:
```python
from pydantic import BaseModel

from persona_genesis.providers.fake_llm import FakeLLMProvider


class _Out(BaseModel):
    x: int


async def test_acomplete_returns_text() -> None:
    assert await FakeLLMProvider(text="hi").acomplete("s", "u") == "hi"


async def test_acomplete_json_returns_payloads_in_order() -> None:
    p = FakeLLMProvider(payloads=[{"x": 1}, _Out(x=2)])
    a = await p.acomplete_json("s", "u", _Out)
    b = await p.acomplete_json("s", "u", _Out)
    c = await p.acomplete_json("s", "u", _Out)  # last repeats
    assert (a.x, b.x, c.x) == (1, 2, 2)
```

- [ ] **Step 3.2: Run** → ImportError.

- [ ] **Step 3.3: Implement** — `src/persona_genesis/providers/fake_llm.py`:
```python
"""Offline LLMProvider double for tests and dev (no network)."""

from pydantic import BaseModel


class FakeLLMProvider:
    def __init__(self, *, payloads: list[BaseModel | dict] | None = None, text: str = "ok") -> None:
        self.model = "fake"
        self._payloads = list(payloads or [])
        self._text = text
        self._i = 0

    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str:
        return self._text

    async def acomplete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        if not self._payloads:
            raise ValueError("FakeLLMProvider has no payloads configured")
        item = self._payloads[min(self._i, len(self._payloads) - 1)]
        self._i += 1
        return item if isinstance(item, schema) else schema.model_validate(item)
```

- [ ] **Step 3.4: Run + mypy + commit**
```bash
uv run pytest tests/unit/test_fake_llm.py -q
uv run mypy src/persona_genesis/providers/fake_llm.py
git add src/persona_genesis/providers/fake_llm.py tests/unit/test_fake_llm.py
git commit -m "feat(providers): add FakeLLMProvider"
```

---

## Task 4: build_llm_provider factory

**Files:** Create `src/persona_genesis/providers/factory.py`, `tests/unit/test_provider_factory.py`

- [ ] **Step 4.1: Write failing tests** — `tests/unit/test_provider_factory.py`:
```python
import pytest

from persona_genesis.config import Config
from persona_genesis.exceptions import ConfigError
from persona_genesis.providers.factory import build_llm_provider
from persona_genesis.providers.openai_compat import OpenAICompatProvider


def test_deepseek_default_base_url() -> None:
    cfg = Config.from_dict({"llm": {"provider": "deepseek", "api_key": "k"}})
    p = build_llm_provider(cfg)
    assert isinstance(p, OpenAICompatProvider)
    assert p.model == "deepseek-chat"


def test_missing_api_key_raises() -> None:
    cfg = Config.from_dict({"llm": {"provider": "deepseek", "api_key": None}})
    with pytest.raises(ConfigError):
        build_llm_provider(cfg)


def test_anthropic_not_supported() -> None:
    cfg = Config.from_dict({"llm": {"provider": "anthropic", "api_key": "k"}})
    with pytest.raises(ConfigError):
        build_llm_provider(cfg)


def test_openai_compat_requires_base_url() -> None:
    cfg = Config.from_dict({"llm": {"provider": "openai_compat", "api_key": "k"}})
    with pytest.raises(ConfigError):
        build_llm_provider(cfg)
```

- [ ] **Step 4.2: Run** → ImportError.

- [ ] **Step 4.3: Implement** — `src/persona_genesis/providers/factory.py`:
```python
"""Build an LLMProvider from Config (no env reading; values come from Config)."""

from persona_genesis.config import Config
from persona_genesis.exceptions import ConfigError
from persona_genesis.providers.llm import LLMProvider
from persona_genesis.providers.openai_compat import OpenAICompatProvider

_DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com/v1",
}


def build_llm_provider(config: Config) -> LLMProvider:
    llm = config.llm
    if llm.provider in ("deepseek", "openai", "openai_compat"):
        base_url = llm.base_url or _DEFAULT_BASE_URLS.get(llm.provider)
        if not base_url:
            raise ConfigError("base_url is required for the openai_compat provider")
        if not llm.api_key:
            raise ConfigError("api_key is required for the LLM provider")
        return OpenAICompatProvider(
            api_key=llm.api_key, model=llm.model, base_url=base_url,
            timeout_s=llm.timeout_s, max_retries=llm.max_retries,
        )
    raise ConfigError(f"LLM provider {llm.provider!r} is not yet supported")
```

- [ ] **Step 4.4: Run + mypy + commit**
```bash
uv run pytest tests/unit/test_provider_factory.py -q
uv run mypy src/persona_genesis/providers/factory.py
git add src/persona_genesis/providers/factory.py tests/unit/test_provider_factory.py
git commit -m "feat(providers): add build_llm_provider factory"
```

---

## Task 5: Coherence validators

**Files:** Modify `src/persona_genesis/generators/work.py`; Create `src/persona_genesis/coherence.py`, `tests/unit/test_coherence.py`

- [ ] **Step 5.1: Expose `MIN_YEARS_EXPERIENCE`** — in `src/persona_genesis/generators/work.py`, rename the private `_MIN_YEARS` to a public `MIN_YEARS_EXPERIENCE` (same contents and type annotation) and update the one reference inside `generate_work` from `_MIN_YEARS` to `MIN_YEARS_EXPERIENCE`. Run `uv run pytest tests/unit/test_gen_work.py -q` to confirm still green.

- [ ] **Step 5.2: Write failing tests** — `tests/unit/test_coherence.py`:
```python
from persona_genesis.coherence import check_persona
from persona_genesis.schema.backstory import Backstory, Education, LifeEvent


def test_clean_persona_has_no_violations(sample_persona) -> None:  # type: ignore[no-untyped-def]
    assert check_persona(sample_persona) == []


def test_education_start_after_end_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    bad = sample_persona.model_copy(update={
        "backstory": Backstory(
            bio="x",
            education=[Education(institution="U", degree="BSc", field_of_study="CS",
                                 start_year=2016, end_year=2012)],
        )
    })
    assert any("start" in v for v in check_persona(bad))


def test_life_events_out_of_order_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    bad = sample_persona.model_copy(update={
        "backstory": Backstory(
            bio="x",
            key_life_events=[LifeEvent(year=2020, description="b"),
                             LifeEvent(year=2010, description="a")],
        )
    })
    assert any("chronological" in v for v in check_persona(bad))
```
(`sample_persona` is the existing conftest fixture: born 1994, senior backend engineer, education 2012–2016 — coherent.)

- [ ] **Step 5.3: Run** → ImportError.

- [ ] **Step 5.4: Implement** — `src/persona_genesis/coherence.py`:
```python
"""Deterministic cross-field coherence checks. Returns human-readable violations."""

from datetime import date

from persona_genesis.generators.work import MIN_YEARS_EXPERIENCE
from persona_genesis.schema.persona import Persona


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def check_persona(persona: Persona) -> list[str]:
    violations: list[str] = []
    age = _age(persona.identity.dob)
    needed = MIN_YEARS_EXPERIENCE[persona.work.seniority]
    if needed > max(0, age - 22):
        violations.append(
            f"seniority '{persona.work.seniority}' needs ~{needed}y experience but age {age} allows {max(0, age - 22)}y"
        )
    birth_year = persona.identity.dob.year
    this_year = date.today().year
    for e in persona.backstory.education:
        if e.end_year is not None and e.start_year > e.end_year:
            violations.append(f"education start_year {e.start_year} after end_year {e.end_year}")
        if not (birth_year <= e.start_year <= this_year):
            violations.append(f"education start_year {e.start_year} outside [{birth_year}, {this_year}]")
        if e.end_year is not None and not (birth_year <= e.end_year <= this_year):
            violations.append(f"education end_year {e.end_year} outside [{birth_year}, {this_year}]")
    years = [le.year for le in persona.backstory.key_life_events]
    if years != sorted(years):
        violations.append("life events are not in chronological order")
    for y in years:
        if not (birth_year <= y <= this_year):
            violations.append(f"life event year {y} outside [{birth_year}, {this_year}]")
    return violations
```

- [ ] **Step 5.5: Run + mypy + commit**
```bash
uv run pytest tests/unit/test_coherence.py tests/unit/test_gen_work.py -q
uv run mypy src/persona_genesis/coherence.py src/persona_genesis/generators/work.py
git add src/persona_genesis/generators/work.py src/persona_genesis/coherence.py tests/unit/test_coherence.py
git commit -m "feat: add deterministic coherence checks (backstory chronology, age vs seniority)"
```

---

## Task 6: NarrativePayload

**Files:** Create `src/persona_genesis/generators/narrative/__init__.py`, `generators/narrative/payload.py`, `tests/unit/test_narrative_payload.py`

- [ ] **Step 6.1: Write failing test** — `tests/unit/test_narrative_payload.py`:
```python
from persona_genesis.generators.narrative.payload import NarrativePayload


def test_payload_round_trips_and_has_no_status_fields() -> None:
    data = {
        "personality": {"ocean": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                                   "agreeableness": 0.5, "neuroticism": 0.5},
                        "traits": ["curious"], "values": ["honesty"], "quirks": ["hums"]},
        "appearance": {"description": "tall", "hair_color": "brown", "hair_style": "short",
                       "eye_color": "brown", "build": "average", "height_cm": 175,
                       "distinguishing_features": []},
        "backstory": {"bio": "b", "education": [], "key_life_events": []},
        "voice": {"writing_style": "casual", "posting_cadence": "daily",
                  "typical_topics": ["t"], "sample_paragraph": "p"},
    }
    p = NarrativePayload.model_validate(data)
    assert NarrativePayload.model_validate_json(p.model_dump_json()) == p
    assert "description_status" not in p.appearance.model_fields
```

- [ ] **Step 6.2: Run** → ImportError.

- [ ] **Step 6.3: Implement** — `generators/narrative/__init__.py`:
```python
"""LLM narrative generation (personality, appearance, backstory, voice)."""
```
`generators/narrative/payload.py`:
```python
"""The LLM's output schema — section content only, no _status fields."""

from pydantic import BaseModel, Field

from persona_genesis.schema.appearance import Build
from persona_genesis.schema.backstory import Education, LifeEvent
from persona_genesis.schema.personality import OceanScores


class PersonalityPayload(BaseModel):
    ocean: OceanScores
    traits: list[str]
    values: list[str]
    quirks: list[str]


class AppearancePayload(BaseModel):
    description: str
    hair_color: str
    hair_style: str
    eye_color: str
    build: Build
    height_cm: int = Field(gt=0, le=260)
    distinguishing_features: list[str]


class BackstoryPayload(BaseModel):
    bio: str
    education: list[Education]
    key_life_events: list[LifeEvent]


class VoicePayload(BaseModel):
    writing_style: str
    posting_cadence: str
    typical_topics: list[str]
    sample_paragraph: str


class NarrativePayload(BaseModel):
    personality: PersonalityPayload
    appearance: AppearancePayload
    backstory: BackstoryPayload
    voice: VoicePayload
```

- [ ] **Step 6.4: Run + mypy + commit**
```bash
uv run pytest tests/unit/test_narrative_payload.py -q
uv run mypy src/persona_genesis/generators/narrative/payload.py
git add src/persona_genesis/generators/narrative/__init__.py src/persona_genesis/generators/narrative/payload.py tests/unit/test_narrative_payload.py
git commit -m "feat(narrative): add NarrativePayload LLM output schema"
```

---

## Task 7: Prompt asset + NarrativeGenerator

**Files:** Create `src/persona_genesis/prompts/__init__.py`, `prompts/narrative.md`, `generators/narrative/narrative.py`, `tests/unit/test_narrative_generator.py`; Modify `pyproject.toml`

- [ ] **Step 7.1: Write failing test** — `tests/unit/test_narrative_generator.py`:
```python
from datetime import date

from persona_genesis.generators.narrative.narrative import NarrativeGenerator
from persona_genesis.generators.narrative.payload import NarrativePayload
from persona_genesis.providers.fake_llm import FakeLLMProvider
from persona_genesis.schema.identity import Identity
from persona_genesis.schema.location import Location
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.work import Work


def _payload() -> NarrativePayload:
    return NarrativePayload.model_validate({
        "personality": {"ocean": {"openness": 0.6, "conscientiousness": 0.6, "extraversion": 0.4,
                                   "agreeableness": 0.7, "neuroticism": 0.3},
                        "traits": ["curious"], "values": ["honesty"], "quirks": ["hums"]},
        "appearance": {"description": "tall with short brown hair", "hair_color": "brown",
                       "hair_style": "short", "eye_color": "brown", "build": "average",
                       "height_cm": 178, "distinguishing_features": ["freckles"]},
        "backstory": {"bio": "grew up coding", "education": [], "key_life_events": []},
        "voice": {"writing_style": "casual", "posting_cadence": "daily",
                  "typical_topics": ["code"], "sample_paragraph": "shipped a feature today"},
    })


def _partial() -> PartialPersona:
    return PartialPersona(
        seed=1, locale="en_US",
        identity=Identity(full_name="Sam Lee", given_name="Sam", family_name="Lee",
                          gender="non_binary", dob=date(1994, 1, 1), nationality="US"),
        location=Location(country="US", region="California", city="San Francisco",
                          timezone="America/Los_Angeles"),
        work=Work(occupation="Engineer", employer="Acme", seniority="senior",
                  industry="Technology", schedule="full_time"),
    )


async def test_generate_maps_payload_with_gen_status() -> None:
    gen = NarrativeGenerator(FakeLLMProvider(payloads=[_payload()]))
    sections = await gen.generate(_partial())
    assert set(sections) == {"personality", "appearance", "backstory", "voice"}
    assert sections["appearance"].hair_color == "brown"
    assert sections["appearance"].hair_color_status == "gen"     # overrides the 'fake' default
    assert sections["personality"].traits_status == "gen"
    assert sections["voice"].writing_style_status == "gen"
    assert sections["backstory"].bio_status == "gen"
```

- [ ] **Step 7.2: Run** → ImportError.

- [ ] **Step 7.3: Create the prompt** — `src/persona_genesis/prompts/__init__.py`:
```python
"""Bundled prompt templates."""
```
`src/persona_genesis/prompts/narrative.md`:
```markdown
You generate realistic, internally consistent persona narrative for a synthetic but
plausible person. You are given fixed ground-truth facts (name, age, gender, locale,
location, occupation). Invent the personality, appearance, backstory, and writing
voice so they fit those facts.

Rules:
- Keep the appearance `description` consistent with the structured appearance fields
  you choose (hair_color, hair_style, eye_color, build, height_cm).
- Make the writing `voice` (style, sample_paragraph, topics) fit the person's locale,
  age, and occupation.
- Backstory must be chronologically consistent: education and life-event years fall
  between the person's birth year and the current year, education start_year is not
  after end_year, and life events are listed in chronological order. The occupation's
  seniority must be plausible for the person's age.
- Be specific and human; avoid clichés and contradictions.

Respond ONLY with a single JSON object matching the provided schema. Do not include
any commentary outside the JSON.
```

- [ ] **Step 7.4: Implement the generator** — `generators/narrative/narrative.py`:
```python
"""Build the narrative prompt, call the LLM for a NarrativePayload, map to sections."""

from datetime import date
from functools import lru_cache
from importlib.resources import files
from typing import Any

from persona_genesis.generators.narrative.payload import NarrativePayload
from persona_genesis.providers.llm import LLMProvider
from persona_genesis.schema.appearance import Appearance
from persona_genesis.schema.backstory import Backstory
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.personality import Personality
from persona_genesis.schema.voice import Voice


@lru_cache
def _system_prompt() -> str:
    return (files("persona_genesis.prompts") / "narrative.md").read_text(encoding="utf-8")


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _user_prompt(partial: PartialPersona, violations: list[str] | None) -> str:
    i, loc, w = partial.identity, partial.location, partial.work
    assert i is not None and loc is not None and w is not None
    lines = [
        "Generate personality, appearance, backstory, and voice for this person:",
        f"Locale: {partial.locale}",
        f"Name: {i.full_name}; gender: {i.gender}; age: {_age(i.dob)}; nationality: {i.nationality}",
        f"Location: {loc.city}, {loc.region}, {loc.country}",
        f"Work: {w.occupation} ({w.seniority}) at {w.employer}; industry {w.industry}",
    ]
    if violations:
        lines.append("Fix these problems from your previous attempt: " + "; ".join(violations))
    return "\n".join(lines)


def _map(payload: NarrativePayload) -> dict[str, Any]:
    pe, ap, bs, vo = payload.personality, payload.appearance, payload.backstory, payload.voice
    return {
        "personality": Personality(
            ocean=pe.ocean, ocean_status="gen", traits=pe.traits, traits_status="gen",
            values=pe.values, values_status="gen", quirks=pe.quirks, quirks_status="gen",
        ),
        "appearance": Appearance(
            description=ap.description, description_status="gen",
            hair_color=ap.hair_color, hair_color_status="gen",
            hair_style=ap.hair_style, hair_style_status="gen",
            eye_color=ap.eye_color, eye_color_status="gen",
            build=ap.build, build_status="gen",
            height_cm=ap.height_cm, height_cm_status="gen",
            distinguishing_features=ap.distinguishing_features, distinguishing_features_status="gen",
        ),
        "voice": Voice(
            writing_style=vo.writing_style, writing_style_status="gen",
            posting_cadence=vo.posting_cadence, posting_cadence_status="gen",
            typical_topics=vo.typical_topics, typical_topics_status="gen",
            sample_paragraph=vo.sample_paragraph, sample_paragraph_status="gen",
        ),
        "backstory": Backstory(
            bio=bs.bio, bio_status="gen", education=bs.education, education_status="gen",
            key_life_events=bs.key_life_events, key_life_events_status="gen",
        ),
    }


class NarrativeGenerator:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def generate(
        self, partial: PartialPersona, *, violations: list[str] | None = None
    ) -> dict[str, Any]:
        payload = await self._llm.acomplete_json(
            _system_prompt(), _user_prompt(partial, violations), NarrativePayload
        )
        assert isinstance(payload, NarrativePayload)
        return _map(payload)
```

- [ ] **Step 7.5: Bundle the prompt** — in `pyproject.toml`, under the existing `[tool.hatch.build.targets.wheel.force-include]` block add a line:
```toml
"src/persona_genesis/prompts" = "persona_genesis/prompts"
```

- [ ] **Step 7.6: Run + mypy + commit**
```bash
uv run pytest tests/unit/test_narrative_generator.py -q
uv run mypy src/persona_genesis/generators/narrative/narrative.py
git add src/persona_genesis/prompts src/persona_genesis/generators/narrative/narrative.py pyproject.toml tests/unit/test_narrative_generator.py
git commit -m "feat(narrative): add NarrativeGenerator + bundled prompt"
```

---

## Task 8: agenerate / generate

**Files:** Modify `src/persona_genesis/orchestrator.py`, `tests/unit/test_orchestrator.py`

- [ ] **Step 8.1: Write failing tests** — append to `tests/unit/test_orchestrator.py`:
```python
def _narrative_payload(*, edu_start: int = 2012, edu_end: int = 2016):  # type: ignore[no-untyped-def]
    from persona_genesis.generators.narrative.payload import NarrativePayload

    return NarrativePayload.model_validate({
        "personality": {"ocean": {"openness": 0.6, "conscientiousness": 0.6, "extraversion": 0.4,
                                   "agreeableness": 0.7, "neuroticism": 0.3},
                        "traits": ["curious"], "values": ["honesty"], "quirks": ["hums"]},
        "appearance": {"description": "tall", "hair_color": "brown", "hair_style": "short",
                       "eye_color": "brown", "build": "average", "height_cm": 178,
                       "distinguishing_features": []},
        "backstory": {"bio": "b",
                      "education": [{"institution": "U", "degree": "BSc", "field_of_study": "CS",
                                     "start_year": edu_start, "end_year": edu_end}],
                      "key_life_events": []},
        "voice": {"writing_style": "casual", "posting_cadence": "daily",
                  "typical_topics": ["code"], "sample_paragraph": "p"},
    })


async def test_agenerate_returns_complete_persona() -> None:
    from persona_genesis.providers.fake_llm import FakeLLMProvider
    from persona_genesis.schema.contact import Contact
    from persona_genesis.schema.persona import Persona

    gen = PersonaGenerator(Config(), llm=FakeLLMProvider(payloads=[_narrative_payload()]))
    p = await gen.agenerate(seed=42, locale="en_US")
    assert isinstance(p, Persona)
    assert p.personality.traits_status == "gen"
    assert p.appearance.hair_color_status == "gen"
    assert p.contact == Contact()
    assert p.metadata.provider_versions["llm"] == "fake"


async def test_agenerate_retries_then_succeeds() -> None:
    from persona_genesis.providers.fake_llm import FakeLLMProvider

    bad = _narrative_payload(edu_start=2016, edu_end=2012)   # start after end -> violation
    good = _narrative_payload()
    gen = PersonaGenerator(Config(), llm=FakeLLMProvider(payloads=[bad, good]))
    p = await gen.agenerate(seed=42, locale="en_US")
    assert p.backstory.education[0].start_year == 2012


async def test_agenerate_raises_coherence_after_retry() -> None:
    import pytest

    from persona_genesis.exceptions import CoherenceError
    from persona_genesis.providers.fake_llm import FakeLLMProvider

    bad = _narrative_payload(edu_start=2016, edu_end=2012)
    gen = PersonaGenerator(Config(), llm=FakeLLMProvider(payloads=[bad, bad]))
    with pytest.raises(CoherenceError):
        await gen.agenerate(seed=42, locale="en_US")


def test_sync_generate_matches() -> None:
    from persona_genesis.providers.fake_llm import FakeLLMProvider
    from persona_genesis.schema.persona import Persona

    gen = PersonaGenerator(Config(), llm=FakeLLMProvider(payloads=[_narrative_payload()]))
    p = gen.generate(seed=42, locale="en_US")
    assert isinstance(p, Persona)
```
(Keep the existing `test_agenerate_requires_llm` — `generate()` with no llm must still raise `ConfigError`.)

- [ ] **Step 8.2: Run** → fails (agenerate not implemented / returns nothing).

- [ ] **Step 8.3: Implement** — replace the `generate`/`agenerate` methods in `src/persona_genesis/orchestrator.py` with the following (keep `__init__`, `_resolve_locale`, `generate_structured`, `agenerate_structured`, `fill_structured`, `afill_structured`). Add the needed imports at the top: `from datetime import UTC, datetime`, `from typing import Any`, `from persona_genesis.coherence import check_persona`, `from persona_genesis.exceptions import CoherenceError`, `from persona_genesis.generators.narrative.narrative import NarrativeGenerator`, `from persona_genesis.schema.metadata import PersonaMetadata`, `from persona_genesis.schema.persona import Persona`:
```python
    def _assemble(self, partial: PartialPersona, sections: dict[str, Any]) -> Persona:
        from persona_genesis import __version__

        model = getattr(self._llm, "model", type(self._llm).__name__)
        return Persona(
            id=partial.id, seed=partial.seed, locale=partial.locale,
            identity=partial.identity, location=partial.location,
            contact=partial.contact or Contact(), work=partial.work, device=partial.device,
            personality=sections["personality"], appearance=sections["appearance"],
            voice=sections["voice"], backstory=sections["backstory"],
            metadata=PersonaMetadata(
                generated_at=datetime.now(tz=UTC),
                generator_version=__version__,
                provider_versions={"llm": str(model)},
            ),
        )

    async def agenerate(
        self, seed: int, locale: str | None = None, *,
        constraints: StructuredConstraints | None = None,
        include: set[str] | None = None,
    ) -> Persona:
        if self._llm is None:
            raise ConfigError("an LLM provider is required to generate narrative sections")
        partial = self.generate_structured(seed, locale, constraints=constraints)
        narrative = NarrativeGenerator(self._llm)
        violations: list[str] | None = None
        for _ in range(2):
            sections = await narrative.generate(partial, violations=violations)
            persona = self._assemble(partial, sections)
            violations = check_persona(persona)
            if not violations:
                return persona
        raise CoherenceError("narrative", violations or [])

    def generate(
        self, seed: int, locale: str | None = None, *,
        constraints: StructuredConstraints | None = None,
        include: set[str] | None = None,
    ) -> Persona:
        import anyio

        return anyio.run(
            lambda: self.agenerate(seed, locale, constraints=constraints, include=include)
        )
```
Notes:
- The old `generate`/`agenerate` (which unconditionally raised) are replaced. `generate()` now delegates to `agenerate()` via `anyio.run`, so with no `llm` it still raises `ConfigError` (preserving `test_agenerate_requires_llm`).
- `Contact` is already imported in `orchestrator.py` from Phase 1; if not, add `from persona_genesis.schema.contact import Contact`.

- [ ] **Step 8.4: Run + mypy + commit**
```bash
uv run pytest tests/unit/test_orchestrator.py -q
uv run mypy src/persona_genesis/orchestrator.py
git add src/persona_genesis/orchestrator.py tests/unit/test_orchestrator.py
git commit -m "feat: implement agenerate()/generate() (structured + narrative + coherence)"
```

---

## Task 9: Public re-exports

**Files:** Modify `src/persona_genesis/__init__.py`, `tests/unit/test_public_api.py`

- [ ] **Step 9.1: Add failing test** — append to `tests/unit/test_public_api.py`:
```python
def test_llm_provider_symbols_exported() -> None:
    from persona_genesis import (
        FakeLLMProvider,
        OpenAICompatProvider,
        build_llm_provider,
    )

    assert OpenAICompatProvider.__name__ == "OpenAICompatProvider"
    assert FakeLLMProvider.__name__ == "FakeLLMProvider"
    assert callable(build_llm_provider)
```

- [ ] **Step 9.2: Run** → ImportError.

- [ ] **Step 9.3: Implement** — in `src/persona_genesis/__init__.py`, add imports:
```python
from persona_genesis.providers.factory import build_llm_provider
from persona_genesis.providers.fake_llm import FakeLLMProvider
from persona_genesis.providers.openai_compat import OpenAICompatProvider
```
and add to `__all__` (keep sorted): `"FakeLLMProvider"`, `"OpenAICompatProvider"`, `"build_llm_provider"`.

- [ ] **Step 9.4: Run + commit**
```bash
uv run pytest tests/unit/test_public_api.py -q
git add src/persona_genesis/__init__.py tests/unit/test_public_api.py
git commit -m "feat: export OpenAICompatProvider, FakeLLMProvider, build_llm_provider"
```

---

## Task 10: Tiered testing (`--level`) + live tests

**Files:** Modify `tests/conftest.py`; Create `tests/integration/test_llm_live.py`

- [ ] **Step 10.1: Add the option, marker, skip logic, and DeepSeek fixtures** — append to `tests/conftest.py`:
```python
from pathlib import Path


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--level", action="store", type=int, default=0,
        help="API cost tier: 0 offline (default), 1 minimal real API, 2 full real API",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "llm(level): requires API cost --level >= the given value")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_level = int(config.getoption("--level"))
    for item in items:
        marker = item.get_closest_marker("llm")
        if marker is None:
            continue
        required = int(marker.kwargs.get("level", marker.args[0] if marker.args else 1))
        if required > run_level:
            item.add_marker(
                pytest.mark.skip(reason=f"needs --level {required} (running at {run_level})")
            )


def _dotenv() -> dict[str, str]:
    env = Path(__file__).resolve().parent.parent / ".env"
    out: dict[str, str] = {}
    if not env.exists():
        return out
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


@pytest.fixture(scope="session")
def deepseek_api_key() -> str:
    key = _dotenv().get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        pytest.skip("DEEPSEEK_API_KEY not set (add it to .env)")
    return key


@pytest.fixture
def live_llm(deepseek_api_key: str) -> object:
    from persona_genesis.providers.openai_compat import OpenAICompatProvider

    return OpenAICompatProvider(api_key=deepseek_api_key)
```
(`import os` and `import pytest` already exist in conftest from earlier work — do not duplicate; add `from pathlib import Path` only if not already imported.)

- [ ] **Step 10.2: Write the gated live tests** — `tests/integration/test_llm_live.py`:
```python
import pytest

from persona_genesis.config import Config
from persona_genesis.orchestrator import PersonaGenerator
from persona_genesis.providers.openai_compat import OpenAICompatProvider
from persona_genesis.schema.persona import Persona


@pytest.mark.llm(level=1)
async def test_deepseek_ping(live_llm: OpenAICompatProvider) -> None:
    out = await live_llm.acomplete("You are terse.", "Reply with exactly one word: pong")
    assert isinstance(out, str) and out.strip()


@pytest.mark.llm(level=2)
async def test_deepseek_full_agenerate(deepseek_api_key: str) -> None:
    llm = OpenAICompatProvider(api_key=deepseek_api_key)
    gen = PersonaGenerator(Config(), llm=llm)
    persona = await gen.agenerate(seed=1, locale="en_US")
    assert isinstance(persona, Persona)
    assert persona.backstory.bio
    assert persona.personality.traits
```

- [ ] **Step 10.3: Verify the tiers**
```bash
uv run pytest tests/integration/test_llm_live.py -q                 # level 0 default -> 2 skipped
uv run pytest tests/integration/test_llm_live.py -q --level 1       # ping runs (or skips if no key)
```
Expected: default run shows both live tests **skipped**; with `--level 1` the ping runs if `DEEPSEEK_API_KEY` is in `.env` (else skips with the key message). (Do not run `--level 2` here unless you want to spend tokens.)

- [ ] **Step 10.4: Commit**
```bash
git add tests/conftest.py tests/integration/test_llm_live.py
git commit -m "test: cost-tiered LLM testing via --level (0 offline, 1 ping, 2 full)"
```

---

## Task 11: Full gate + docs

**Files:** Modify `CHANGELOG.md`, `docs/roadmap.md`

- [ ] **Step 11.1: Full gate**
```bash
uv run pytest -q                                   # all offline tests pass; live tests skip
uv run ruff check src tests
uv run mypy src/persona_genesis tests
```
Expected: green. Fix any lint/type issues (wrap long lines, add `assert x is not None` narrowing, etc.).

- [ ] **Step 11.2: CHANGELOG** — under `## [Unreleased] / ### Added`, add: narrative generation via an OpenAI-compatible (DeepSeek) `OpenAICompatProvider` + `FakeLLMProvider` + `build_llm_provider`; `PersonaGenerator.agenerate()`/`generate()` now produce a complete `Persona` (personality/appearance/backstory/voice, `status="gen"`) with a deterministic coherence pass (backstory chronology, age vs seniority) and one retry; cost-tiered tests via `--level`. Note: default `LLMConfig` provider is now `deepseek`.

- [ ] **Step 11.3: Roadmap** — in `docs/roadmap.md`, change the Phase 2 marker to ✅ and the Phase 3 marker to 🔭.

- [ ] **Step 11.4: Commit**
```bash
git add CHANGELOG.md docs/roadmap.md
git commit -m "docs: changelog + roadmap for the narrative generation layer"
```

---

## Self-Review (against the spec)

**Spec coverage:** §2.1 OpenAICompatProvider → Task 2. §2.2 FakeLLMProvider → Task 3. §2.3 build_llm_provider + Config deepseek → Tasks 1, 4. §3.1 NarrativePayload → Task 6. §3.2 NarrativeGenerator → Task 7. §3.3 prompt asset → Task 7. §4 coherence (+ MIN_YEARS_EXPERIENCE) → Task 5. §5 agenerate/generate/_assemble → Task 8. §6 re-exports → Task 9. §7 tiered testing → Task 10. §8 test detail → Tasks 2–10. §9 layout/deferred → all.

**Placeholder scan:** none — every step has complete code.

**Type consistency:** `OpenAICompatProvider(api_key, model, base_url, timeout_s, max_retries, http_client)` and its `.model` attribute are used identically in the factory and `_assemble`. `FakeLLMProvider(payloads=, text=)` and `.model="fake"` match the orchestrator tests. `NarrativePayload` sub-fields match `_map`'s reads. `check_persona(persona) -> list[str]` and `MIN_YEARS_EXPERIENCE` are consistent between `coherence.py` and `work.py`. `agenerate`/`generate` signatures match the Phase 1 ones (constraints/include kwargs).

**Note:** `generate()` now delegates to `agenerate()` via `anyio.run`; the no-LLM `ConfigError` path is preserved.
