# persona-genesis Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `persona-genesis` library skeleton — project scaffolding, the complete `Persona` Pydantic schema (the library's public contract), `Config`/`Config.from_env()`, and the exception hierarchy — as an importable, fully type-checked, fully tested package.

**Architecture:** `src/` layout, uv-managed with the hatchling build backend. The schema lives in `src/persona_genesis/schema/` as one file per sub-model, all re-exported from the package root. Config is **injected as a nested dict** and validated via `Config.from_dict()` (plain Pydantic `model_validate`); the library never reads `.env` or touches the filesystem. Producing that dict — from `.env`, a vault, hardcoded values, whatever — is the caller's responsibility and is not enforced. No generators or providers are built here — only the data contract and configuration they will later depend on.

**Tech Stack:** Python 3.12+, Pydantic v2, Pillow, uv, hatchling, ruff, mypy, pytest. GitHub Actions CI (3.12 + 3.13 matrix).

> **Deviation from spec §6:** the spec described `Config.from_env()` reading `PERSONA_*` env vars / `.env` directly. Per updated requirement, the library instead accepts an injected nested config dict (`Config.from_dict()`) and does no env/file reading itself. User instruction takes precedence over the spec here.

---

## File Structure

Created in this plan:

- `pyproject.toml` — project metadata, core deps, optional extras, dev deps, ruff/mypy/pytest config (rewrites the existing stub).
- `.python-version` — pin to `3.12` (rewrites existing `3.11`).
- `LICENSE` — MIT.
- `.github/workflows/ci.yml` — lint + typecheck + test matrix.
- `src/persona_genesis/__init__.py` — re-exports the public API that exists at this stage.
- `src/persona_genesis/exceptions.py` — exception hierarchy.
- `src/persona_genesis/schema/__init__.py` — re-exports every schema model.
- `src/persona_genesis/schema/identity.py`
- `src/persona_genesis/schema/location.py`
- `src/persona_genesis/schema/contact.py`
- `src/persona_genesis/schema/work.py`
- `src/persona_genesis/schema/appearance.py`
- `src/persona_genesis/schema/personality.py`
- `src/persona_genesis/schema/voice.py`
- `src/persona_genesis/schema/device.py`
- `src/persona_genesis/schema/backstory.py`
- `src/persona_genesis/schema/images.py`
- `src/persona_genesis/schema/metadata.py`
- `src/persona_genesis/schema/persona.py` — top-level `Persona`.
- `src/persona_genesis/config.py` — `LLMConfig`, `ImageConfig`, `Config`, `Config.from_dict()` (config is injected as a nested dict; the library never reads `.env` or the filesystem).
- `tests/conftest.py` — shared fixtures (a fully-populated `Persona` factory).
- `tests/unit/test_*.py` — one test module per schema area + config + exceptions.

Deleted in this plan:

- `main.py` — replaced by the package; the `Hello` stub is not part of the design.

---

## Task 1: Project scaffolding (pyproject, layout, tooling)

**Files:**
- Modify: `pyproject.toml`
- Modify: `.python-version`
- Create: `LICENSE`
- Create: `src/persona_genesis/__init__.py`
- Create: `tests/__init__.py`
- Delete: `main.py`

- [ ] **Step 1: Pin Python version**

Overwrite `.python-version` with exactly:

```
3.12
```

- [ ] **Step 2: Write `pyproject.toml`**

Overwrite `pyproject.toml` with:

```toml
[project]
name = "persona-genesis"
version = "0.1.0"
description = "Generate highly detailed, coherent personas (structured + narrative + visual)."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Tarsow", email = "tarsowdev@gmail.com" }]
dependencies = [
    "pydantic>=2.6",
    "faker>=24",
    "polyfactory>=2.15",
    "fake-useragent>=1.5",
    "httpx>=0.27",
    "Pillow>=10",
    "anyio>=4",
]

[project.optional-dependencies]
anthropic = ["anthropic>=0.40"]
openai = ["openai>=1.40"]
local-image = ["torch>=2.3", "diffusers>=0.27", "transformers>=4.40", "accelerate>=0.30"]
cli = ["typer>=0.12", "rich>=13"]
all = [
    "anthropic>=0.40",
    "openai>=1.40",
    "torch>=2.3",
    "diffusers>=0.27",
    "transformers>=4.40",
    "accelerate>=0.30",
    "typer>=0.12",
    "rich>=13",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "ruff>=0.6",
    "mypy>=1.11",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/persona_genesis"]

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
mypy_path = "src"
packages = ["persona_genesis"]

[[tool.mypy.overrides]]
module = ["fake_useragent.*", "polyfactory.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
pythonpath = ["src"]
```

- [ ] **Step 3: Create package and test roots**

Create `src/persona_genesis/__init__.py` with a placeholder version marker (re-exports are added in later tasks):

```python
"""persona-genesis: generate detailed, coherent personas."""

__version__ = "0.1.0"
```

Create empty `tests/__init__.py`:

```python
```

- [ ] **Step 4: Write the MIT LICENSE**

Create `LICENSE`:

```
MIT License

Copyright (c) 2026 Tarsow

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 5: Remove the stub**

```bash
git rm main.py
```

- [ ] **Step 6: Sync the environment**

Run:

```bash
uv sync
```

Expected: uv provisions Python 3.12, creates `.venv`, installs core + dev deps. Do **not** use `--all-extras` here — the `local-image` extra pulls in torch and is unnecessary for the foundation. Optional provider extras are installed in later plans when their code lands.

- [ ] **Step 7: Verify the package imports and tooling runs**

Run:

```bash
uv run python -c "import persona_genesis; print(persona_genesis.__version__)"
uv run ruff check .
uv run mypy
```

Expected: prints `0.1.0`; ruff reports `All checks passed!`; mypy reports `Success: no issues found`.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "chore: scaffold persona-genesis package (pyproject, src layout, tooling, LICENSE)"
```

---

## Task 2: Exception hierarchy

**Files:**
- Create: `src/persona_genesis/exceptions.py`
- Test: `tests/unit/test_exceptions.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_exceptions.py`:

```python
import pytest

from persona_genesis.exceptions import (
    CoherenceError,
    ConfigError,
    PersonaGenerationError,
    PersonaGenesisError,
    ProviderError,
)


@pytest.mark.parametrize(
    "exc",
    [PersonaGenerationError, CoherenceError, ProviderError, ConfigError],
)
def test_all_errors_subclass_base(exc: type[Exception]) -> None:
    assert issubclass(exc, PersonaGenesisError)


def test_base_is_an_exception() -> None:
    assert issubclass(PersonaGenesisError, Exception)
    with pytest.raises(PersonaGenesisError):
        raise CoherenceError("boom")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_exceptions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'persona_genesis.exceptions'`.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/exceptions.py`:

```python
"""Exception hierarchy for persona-genesis."""


class PersonaGenesisError(Exception):
    """Base class for all errors raised by persona-genesis."""


class PersonaGenerationError(PersonaGenesisError):
    """Raised when persona generation fails irrecoverably."""


class CoherenceError(PersonaGenesisError):
    """Raised when cross-field coherence validation fails after retry."""


class ProviderError(PersonaGenesisError):
    """Raised when an LLM or image provider call fails."""


class ConfigError(PersonaGenesisError):
    """Raised when configuration is missing or invalid."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_exceptions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/exceptions.py tests/unit/test_exceptions.py
git commit -m "feat: add exception hierarchy"
```

---

## Task 3: Identity schema

**Files:**
- Create: `src/persona_genesis/schema/__init__.py`
- Create: `src/persona_genesis/schema/identity.py`
- Test: `tests/unit/test_schema_identity.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_identity.py`:

```python
from datetime import date

from persona_genesis.schema.identity import Identity


def test_identity_round_trips() -> None:
    ident = Identity(
        full_name="Ana Souza",
        given_name="Ana",
        family_name="Souza",
        gender="female",
        dob=date(1994, 3, 12),
        nationality="BR",
    )
    dumped = ident.model_dump_json()
    restored = Identity.model_validate_json(dumped)
    assert restored == ident
    assert restored.dob == date(1994, 3, 12)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_identity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'persona_genesis.schema'`.

- [ ] **Step 3: Write the implementation**

Create empty `src/persona_genesis/schema/__init__.py` (populated with re-exports in Task 14):

```python
"""Pydantic schema models — the persona-genesis public contract."""
```

Create `src/persona_genesis/schema/identity.py`:

```python
"""Identity sub-model."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

Gender = Literal["male", "female", "non_binary"]


class Identity(BaseModel):
    full_name: str
    given_name: str
    family_name: str
    gender: Gender
    dob: date
    nationality: str  # ISO 3166-1 alpha-2 country code
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_identity.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/__init__.py src/persona_genesis/schema/identity.py tests/unit/test_schema_identity.py
git commit -m "feat: add Identity schema"
```

---

## Task 4: Location schema

**Files:**
- Create: `src/persona_genesis/schema/location.py`
- Test: `tests/unit/test_schema_location.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_location.py`:

```python
from persona_genesis.schema.location import Location


def test_location_round_trips() -> None:
    loc = Location(
        country="BR",
        region="São Paulo",
        city="Campinas",
        street="Rua das Flores, 123",
        postal_code="13010-000",
        timezone="America/Sao_Paulo",
    )
    restored = Location.model_validate_json(loc.model_dump_json())
    assert restored == loc
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_location.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'persona_genesis.schema.location'`.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/schema/location.py`:

```python
"""Location sub-model."""

from pydantic import BaseModel


class Location(BaseModel):
    country: str  # ISO 3166-1 alpha-2 country code
    region: str  # state / province
    city: str
    street: str
    postal_code: str
    timezone: str  # IANA timezone name, e.g. "America/Sao_Paulo"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_location.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/location.py tests/unit/test_schema_location.py
git commit -m "feat: add Location schema"
```

---

## Task 5: Contact schema

**Files:**
- Create: `src/persona_genesis/schema/contact.py`
- Test: `tests/unit/test_schema_contact.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_contact.py`:

```python
from persona_genesis.schema.contact import Contact


def test_contact_round_trips() -> None:
    contact = Contact(phone="+55 19 90000-0000", email_handle="ana.souza")
    restored = Contact.model_validate_json(contact.model_dump_json())
    assert restored == contact
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_contact.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/schema/contact.py`:

```python
"""Contact sub-model. Holds formatted, non-real contact details only."""

from pydantic import BaseModel


class Contact(BaseModel):
    phone: str  # formatted placeholder, never a real reachable number
    email_handle: str  # local-part only (no domain)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_contact.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/contact.py tests/unit/test_schema_contact.py
git commit -m "feat: add Contact schema"
```

---

## Task 6: Work schema

**Files:**
- Create: `src/persona_genesis/schema/work.py`
- Test: `tests/unit/test_schema_work.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_work.py`:

```python
import pytest
from pydantic import ValidationError

from persona_genesis.schema.work import Work


def test_work_round_trips() -> None:
    work = Work(
        occupation="Backend Engineer",
        employer="Nubank",
        seniority="senior",
        industry="Fintech",
        schedule="full_time",
    )
    restored = Work.model_validate_json(work.model_dump_json())
    assert restored == work


def test_work_rejects_unknown_seniority() -> None:
    with pytest.raises(ValidationError):
        Work(
            occupation="x",
            employer="y",
            seniority="grandmaster",  # type: ignore[arg-type]
            industry="z",
            schedule="full_time",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_work.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/schema/work.py`:

```python
"""Work sub-model."""

from typing import Literal

from pydantic import BaseModel

Seniority = Literal[
    "intern",
    "junior",
    "mid",
    "senior",
    "lead",
    "manager",
    "director",
    "executive",
]
Schedule = Literal["full_time", "part_time", "contract", "freelance", "shift", "remote"]


class Work(BaseModel):
    occupation: str
    employer: str
    seniority: Seniority
    industry: str
    schedule: Schedule
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_work.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/work.py tests/unit/test_schema_work.py
git commit -m "feat: add Work schema"
```

---

## Task 7: Appearance schema

**Files:**
- Create: `src/persona_genesis/schema/appearance.py`
- Test: `tests/unit/test_schema_appearance.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_appearance.py`:

```python
import pytest
from pydantic import ValidationError

from persona_genesis.schema.appearance import Appearance


def test_appearance_round_trips() -> None:
    app = Appearance(
        description="Tall with short dark curly hair and warm brown eyes.",
        hair_color="dark brown",
        hair_style="short curly",
        eye_color="brown",
        build="athletic",
        height_cm=178,
        distinguishing_features=["small scar above left eyebrow"],
    )
    restored = Appearance.model_validate_json(app.model_dump_json())
    assert restored == app


def test_appearance_defaults_features_to_empty_list() -> None:
    app = Appearance(
        description="d",
        hair_color="black",
        hair_style="bald",
        eye_color="black",
        build="average",
        height_cm=170,
    )
    assert app.distinguishing_features == []


def test_appearance_rejects_nonpositive_height() -> None:
    with pytest.raises(ValidationError):
        Appearance(
            description="d",
            hair_color="black",
            hair_style="x",
            eye_color="black",
            build="average",
            height_cm=0,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_appearance.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/schema/appearance.py`:

```python
"""Appearance sub-model: narrative description plus structured attributes."""

from typing import Literal

from pydantic import BaseModel, Field

Build = Literal["slim", "average", "athletic", "muscular", "heavy"]


class Appearance(BaseModel):
    description: str  # narrative; must not contradict the structured fields below
    hair_color: str
    hair_style: str
    eye_color: str
    build: Build
    height_cm: int = Field(gt=0, le=260)
    distinguishing_features: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_appearance.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/appearance.py tests/unit/test_schema_appearance.py
git commit -m "feat: add Appearance schema"
```

---

## Task 8: Personality schema

**Files:**
- Create: `src/persona_genesis/schema/personality.py`
- Test: `tests/unit/test_schema_personality.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_personality.py`:

```python
import pytest
from pydantic import ValidationError

from persona_genesis.schema.personality import OceanScores, Personality


def _ocean() -> OceanScores:
    return OceanScores(
        openness=0.7,
        conscientiousness=0.6,
        extraversion=0.4,
        agreeableness=0.8,
        neuroticism=0.3,
    )


def test_personality_round_trips() -> None:
    p = Personality(
        ocean=_ocean(),
        traits=["curious", "pragmatic"],
        values=["honesty", "craftsmanship"],
        quirks=["always early"],
    )
    restored = Personality.model_validate_json(p.model_dump_json())
    assert restored == p


def test_ocean_scores_bounded_0_1() -> None:
    with pytest.raises(ValidationError):
        OceanScores(
            openness=1.5,
            conscientiousness=0.5,
            extraversion=0.5,
            agreeableness=0.5,
            neuroticism=0.5,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_personality.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/schema/personality.py`:

```python
"""Personality sub-model: OCEAN scores plus descriptive traits."""

from pydantic import BaseModel, Field


class OceanScores(BaseModel):
    """Big Five scores, each normalized to [0, 1]."""

    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)


class Personality(BaseModel):
    ocean: OceanScores
    traits: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    quirks: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_personality.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/personality.py tests/unit/test_schema_personality.py
git commit -m "feat: add Personality schema"
```

---

## Task 9: Voice schema

**Files:**
- Create: `src/persona_genesis/schema/voice.py`
- Test: `tests/unit/test_schema_voice.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_voice.py`:

```python
from persona_genesis.schema.voice import Voice


def test_voice_round_trips() -> None:
    voice = Voice(
        writing_style="casual, lots of emoji, short sentences",
        posting_cadence="2-3 times per day",
        typical_topics=["football", "coding", "cooking"],
        sample_paragraph="Just shipped a new feature, feeling good about it!",
    )
    restored = Voice.model_validate_json(voice.model_dump_json())
    assert restored == voice
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_voice.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/schema/voice.py`:

```python
"""Voice sub-model: how the persona writes and posts online."""

from pydantic import BaseModel, Field


class Voice(BaseModel):
    writing_style: str
    posting_cadence: str
    typical_topics: list[str] = Field(default_factory=list)
    sample_paragraph: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_voice.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/voice.py tests/unit/test_schema_voice.py
git commit -m "feat: add Voice schema"
```

---

## Task 10: Device schema

**Files:**
- Create: `src/persona_genesis/schema/device.py`
- Test: `tests/unit/test_schema_device.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_device.py`:

```python
import pytest
from pydantic import ValidationError

from persona_genesis.schema.device import Device


def test_device_round_trips() -> None:
    device = Device(
        primary_device="smartphone",
        os="android",
        browser="chrome",
        user_agent="Mozilla/5.0 (Linux; Android 14) ... Chrome/124.0 Mobile",
        screen_resolution="1080x2400",
    )
    restored = Device.model_validate_json(device.model_dump_json())
    assert restored == device


def test_device_rejects_unknown_os() -> None:
    with pytest.raises(ValidationError):
        Device(
            primary_device="smartphone",
            os="symbian",  # type: ignore[arg-type]
            browser="chrome",
            user_agent="x",
            screen_resolution="1x1",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_device.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/schema/device.py`:

```python
"""Device sub-model: hardware, OS, browser and the matching user agent."""

from typing import Literal

from pydantic import BaseModel

DeviceType = Literal["desktop", "laptop", "smartphone", "tablet"]
OS = Literal["windows", "macos", "linux", "android", "ios"]
Browser = Literal["chrome", "firefox", "safari", "edge"]


class Device(BaseModel):
    primary_device: DeviceType
    os: OS
    browser: Browser
    user_agent: str
    screen_resolution: str  # "<width>x<height>", e.g. "1920x1080"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_device.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/device.py tests/unit/test_schema_device.py
git commit -m "feat: add Device schema"
```

---

## Task 11: Backstory schema

**Files:**
- Create: `src/persona_genesis/schema/backstory.py`
- Test: `tests/unit/test_schema_backstory.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_backstory.py`:

```python
from persona_genesis.schema.backstory import Backstory, Education, LifeEvent


def test_backstory_round_trips() -> None:
    bs = Backstory(
        bio="Grew up in Campinas, moved to São Paulo for work.",
        education=[
            Education(
                institution="UNICAMP",
                degree="BSc",
                field_of_study="Computer Science",
                start_year=2012,
                end_year=2016,
            )
        ],
        key_life_events=[LifeEvent(year=2016, description="First job as a junior dev")],
    )
    restored = Backstory.model_validate_json(bs.model_dump_json())
    assert restored == bs


def test_education_end_year_is_optional() -> None:
    edu = Education(
        institution="USP",
        degree="MSc",
        field_of_study="AI",
        start_year=2020,
    )
    assert edu.end_year is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_backstory.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/schema/backstory.py`:

```python
"""Backstory sub-model: bio, education history and key life events."""

from pydantic import BaseModel, Field


class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_year: int
    end_year: int | None = None


class LifeEvent(BaseModel):
    year: int
    description: str


class Backstory(BaseModel):
    bio: str
    education: list[Education] = Field(default_factory=list)
    key_life_events: list[LifeEvent] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_backstory.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/backstory.py tests/unit/test_schema_backstory.py
git commit -m "feat: add Backstory schema"
```

---

## Task 12: PersonaImages schema (PIL fields excluded from JSON)

**Files:**
- Create: `src/persona_genesis/schema/images.py`
- Test: `tests/unit/test_schema_images.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_images.py`:

```python
import json

from PIL import Image

from persona_genesis.schema.images import PersonaImages


def test_images_default_to_none() -> None:
    imgs = PersonaImages()
    assert imgs.face_image is None
    assert imgs.body_image is None


def test_images_accept_pil_images() -> None:
    face = Image.new("RGB", (8, 8), "white")
    imgs = PersonaImages(face_image=face)
    assert imgs.face_image is face


def test_images_excluded_from_json_serialization() -> None:
    imgs = PersonaImages(face_image=Image.new("RGB", (8, 8), "white"))
    payload = json.loads(imgs.model_dump_json())
    assert "face_image" not in payload
    assert "body_image" not in payload
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_images.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/schema/images.py`:

```python
"""PersonaImages container.

Image fields hold in-memory ``PIL.Image.Image`` objects and are excluded from
JSON serialization by default — consumers convert/save them explicitly.
"""

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field


class PersonaImages(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    face_image: Image.Image | None = Field(default=None, exclude=True)
    body_image: Image.Image | None = Field(default=None, exclude=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_images.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/images.py tests/unit/test_schema_images.py
git commit -m "feat: add PersonaImages schema with PIL fields excluded from JSON"
```

---

## Task 13: PersonaMetadata schema

**Files:**
- Create: `src/persona_genesis/schema/metadata.py`
- Test: `tests/unit/test_schema_metadata.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_schema_metadata.py`:

```python
from datetime import UTC, datetime

from persona_genesis.schema.metadata import PersonaMetadata


def test_metadata_round_trips() -> None:
    meta = PersonaMetadata(
        generated_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        generator_version="0.1.0",
        provider_versions={"llm": "anthropic:claude-opus-4-7", "image": "fal:flux-schnell"},
    )
    restored = PersonaMetadata.model_validate_json(meta.model_dump_json())
    assert restored == meta


def test_metadata_provider_versions_default_empty() -> None:
    meta = PersonaMetadata(
        generated_at=datetime(2026, 6, 1, tzinfo=UTC),
        generator_version="0.1.0",
    )
    assert meta.provider_versions == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_metadata.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/schema/metadata.py`:

```python
"""PersonaMetadata: provenance for a generated persona."""

from datetime import datetime

from pydantic import BaseModel, Field


class PersonaMetadata(BaseModel):
    generated_at: datetime
    generator_version: str
    provider_versions: dict[str, str] = Field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_schema_metadata.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/schema/metadata.py tests/unit/test_schema_metadata.py
git commit -m "feat: add PersonaMetadata schema"
```

---

## Task 14: Persona top-level schema + schema package re-exports

**Files:**
- Create: `src/persona_genesis/schema/persona.py`
- Modify: `src/persona_genesis/schema/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/unit/test_schema_persona.py`

- [ ] **Step 1: Write the shared fixture**

Create `tests/conftest.py` (a fully-populated `Persona` reused by later tests):

```python
from datetime import UTC, date, datetime

import pytest

from persona_genesis.schema import (
    Appearance,
    Backstory,
    Contact,
    Device,
    Education,
    Identity,
    LifeEvent,
    Location,
    OceanScores,
    Persona,
    PersonaMetadata,
    Personality,
    Voice,
    Work,
)


@pytest.fixture
def sample_persona() -> Persona:
    return Persona(
        seed=42,
        locale="pt_BR",
        identity=Identity(
            full_name="Ana Souza",
            given_name="Ana",
            family_name="Souza",
            gender="female",
            dob=date(1994, 3, 12),
            nationality="BR",
        ),
        location=Location(
            country="BR",
            region="São Paulo",
            city="Campinas",
            street="Rua das Flores, 123",
            postal_code="13010-000",
            timezone="America/Sao_Paulo",
        ),
        contact=Contact(phone="+55 19 90000-0000", email_handle="ana.souza"),
        work=Work(
            occupation="Backend Engineer",
            employer="Nubank",
            seniority="senior",
            industry="Fintech",
            schedule="full_time",
        ),
        appearance=Appearance(
            description="Tall with short dark curly hair and warm brown eyes.",
            hair_color="dark brown",
            hair_style="short curly",
            eye_color="brown",
            build="athletic",
            height_cm=178,
            distinguishing_features=["small scar above left eyebrow"],
        ),
        personality=Personality(
            ocean=OceanScores(
                openness=0.7,
                conscientiousness=0.6,
                extraversion=0.4,
                agreeableness=0.8,
                neuroticism=0.3,
            ),
            traits=["curious", "pragmatic"],
            values=["honesty", "craftsmanship"],
            quirks=["always early"],
        ),
        voice=Voice(
            writing_style="casual, short sentences",
            posting_cadence="2-3 times per day",
            typical_topics=["coding", "cooking"],
            sample_paragraph="Just shipped a new feature, feeling good about it!",
        ),
        device=Device(
            primary_device="smartphone",
            os="android",
            browser="chrome",
            user_agent="Mozilla/5.0 (Linux; Android 14) Chrome/124.0 Mobile",
            screen_resolution="1080x2400",
        ),
        backstory=Backstory(
            bio="Grew up in Campinas, moved to São Paulo for work.",
            education=[
                Education(
                    institution="UNICAMP",
                    degree="BSc",
                    field_of_study="Computer Science",
                    start_year=2012,
                    end_year=2016,
                )
            ],
            key_life_events=[LifeEvent(year=2016, description="First job as a junior dev")],
        ),
        metadata=PersonaMetadata(
            generated_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            generator_version="0.1.0",
        ),
    )
```

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_schema_persona.py`:

```python
import json
from uuid import UUID

from PIL import Image

from persona_genesis.schema import Persona


def test_persona_has_generated_uuid_and_default_images(sample_persona: Persona) -> None:
    assert isinstance(sample_persona.id, UUID)
    assert sample_persona.images.face_image is None


def test_persona_round_trips_without_images(sample_persona: Persona) -> None:
    restored = Persona.model_validate_json(sample_persona.model_dump_json())
    assert restored == sample_persona


def test_persona_json_excludes_images_even_when_present(sample_persona: Persona) -> None:
    sample_persona.images.face_image = Image.new("RGB", (8, 8), "white")
    payload = json.loads(sample_persona.model_dump_json())
    assert payload["images"] == {}
    assert payload["seed"] == 42
    assert payload["locale"] == "pt_BR"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_schema_persona.py -v`
Expected: FAIL — `ImportError: cannot import name 'Persona' from 'persona_genesis.schema'`.

- [ ] **Step 4: Write the Persona model**

Create `src/persona_genesis/schema/persona.py`:

```python
"""Top-level Persona model — the persona-genesis public contract."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from persona_genesis.schema.appearance import Appearance
from persona_genesis.schema.backstory import Backstory
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.device import Device
from persona_genesis.schema.identity import Identity
from persona_genesis.schema.images import PersonaImages
from persona_genesis.schema.location import Location
from persona_genesis.schema.metadata import PersonaMetadata
from persona_genesis.schema.personality import Personality
from persona_genesis.schema.voice import Voice
from persona_genesis.schema.work import Work


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

    images: PersonaImages = Field(default_factory=PersonaImages)
    metadata: PersonaMetadata
```

- [ ] **Step 5: Populate the schema package re-exports**

Overwrite `src/persona_genesis/schema/__init__.py`:

```python
"""Pydantic schema models — the persona-genesis public contract."""

from persona_genesis.schema.appearance import Appearance, Build
from persona_genesis.schema.backstory import Backstory, Education, LifeEvent
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.device import Browser, Device, DeviceType, OS
from persona_genesis.schema.identity import Gender, Identity
from persona_genesis.schema.images import PersonaImages
from persona_genesis.schema.location import Location
from persona_genesis.schema.metadata import PersonaMetadata
from persona_genesis.schema.personality import OceanScores, Personality
from persona_genesis.schema.persona import Persona
from persona_genesis.schema.voice import Voice
from persona_genesis.schema.work import Schedule, Seniority, Work

__all__ = [
    "Appearance",
    "Backstory",
    "Browser",
    "Build",
    "Contact",
    "Device",
    "DeviceType",
    "Education",
    "Gender",
    "Identity",
    "LifeEvent",
    "Location",
    "OS",
    "OceanScores",
    "Persona",
    "PersonaImages",
    "PersonaMetadata",
    "Personality",
    "Schedule",
    "Seniority",
    "Voice",
    "Work",
]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_schema_persona.py -v`
Expected: PASS (all three tests).

- [ ] **Step 7: Commit**

```bash
git add src/persona_genesis/schema/persona.py src/persona_genesis/schema/__init__.py tests/conftest.py tests/unit/test_schema_persona.py
git commit -m "feat: add top-level Persona model and schema re-exports"
```

---

## Task 15: Config and Config.from_dict()

Config is injected as a nested dict and validated with plain Pydantic. The
library does **not** read `.env`, environment variables, or any file — building
the dict is the caller's responsibility. Unknown keys (top-level and nested) are
silently ignored; malformed values raise `ConfigError`.

**Files:**
- Create: `src/persona_genesis/config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_config.py`:

```python
import pytest

from persona_genesis.config import Config, ImageConfig, LLMConfig
from persona_genesis.exceptions import ConfigError


def test_defaults_match_spec() -> None:
    cfg = Config()
    assert cfg.llm.provider == "anthropic"
    assert cfg.llm.model == "claude-opus-4-7"
    assert cfg.image.provider == "fal"
    assert cfg.image.model == "fal-ai/flux/schnell"
    assert cfg.default_locale == "en_US"


def test_explicit_construction() -> None:
    cfg = Config(
        llm=LLMConfig(provider="openai", api_key="sk-x", model="gpt-4o"),
        image=ImageConfig(provider="replicate", api_key="r8-x"),
        default_locale="pt_BR",
    )
    assert cfg.llm.provider == "openai"
    assert cfg.default_locale == "pt_BR"


def test_from_dict_reads_nested_keys() -> None:
    cfg = Config.from_dict(
        {
            "llm": {
                "provider": "openai",
                "api_key": "sk-fromdict",
                "model": "gpt-4o",
                "timeout_s": 30,
            },
            "image": {"provider": "fal", "api_key": "fal-key"},
            "default_locale": "pt_BR",
        }
    )
    assert cfg.llm.provider == "openai"
    assert cfg.llm.api_key == "sk-fromdict"
    assert cfg.llm.model == "gpt-4o"
    assert cfg.llm.timeout_s == 30
    assert cfg.image.provider == "fal"
    assert cfg.image.api_key == "fal-key"
    assert cfg.default_locale == "pt_BR"


def test_from_dict_empty_uses_defaults() -> None:
    cfg = Config.from_dict({})
    assert cfg.llm.provider == "anthropic"
    assert cfg.image.provider == "fal"
    assert cfg.default_locale == "en_US"


def test_from_dict_ignores_unknown_keys() -> None:
    cfg = Config.from_dict(
        {
            "llm": {"provider": "openai", "unknown_nested": "ignored"},
            "totally_unknown": {"x": 1},
        }
    )
    assert cfg.llm.provider == "openai"
    assert not hasattr(cfg, "totally_unknown")


def test_from_dict_raises_config_error_on_bad_value() -> None:
    with pytest.raises(ConfigError):
        Config.from_dict({"llm": {"timeout_s": "not-an-int"}})


def test_from_dict_raises_config_error_on_bad_provider() -> None:
    with pytest.raises(ConfigError):
        Config.from_dict({"llm": {"provider": "not-a-provider"}})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'persona_genesis.config'`.

- [ ] **Step 3: Write the implementation**

Create `src/persona_genesis/config.py`. There is no env/file reading: `from_dict`
is a thin, validating wrapper over `model_validate` that converts Pydantic's
`ValidationError` into the library's `ConfigError`. Sub-models use
`extra="ignore"` so unknown nested keys are dropped rather than rejected.

```python
"""Configuration models. Config is injected as a nested dict; the library never
reads environment variables or files itself."""

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from persona_genesis.exceptions import ConfigError

LLMProviderName = Literal["anthropic", "openai", "openai_compat"]
ImageProviderName = Literal["fal", "replicate", "openai", "diffusers_local"]


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: LLMProviderName = "anthropic"
    api_key: str | None = None
    model: str = "claude-opus-4-7"
    base_url: str | None = None  # only used by openai_compat
    timeout_s: int = 60
    max_retries: int = 2


class ImageConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: ImageProviderName = "fal"
    api_key: str | None = None
    model: str = "fal-ai/flux/schnell"
    timeout_s: int = 120


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    llm: LLMConfig = Field(default_factory=LLMConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    default_locale: str = "en_US"
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Config":
        """Validate an injected nested config dict into a Config.

        Known keys are read; unknown keys (top-level and nested) are ignored.
        Building this dict — from .env, a secrets manager, literals, etc. — is the
        caller's responsibility and is not enforced by the library.
        """
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise ConfigError(f"Invalid persona-genesis configuration: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: PASS (all seven tests).

- [ ] **Step 5: Commit**

```bash
git add src/persona_genesis/config.py tests/unit/test_config.py
git commit -m "feat: add Config and Config.from_dict() (injected nested config, no env reading)"
```

---

## Task 16: Public API re-exports + package smoke test

**Files:**
- Modify: `src/persona_genesis/__init__.py`
- Test: `tests/unit/test_public_api.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_public_api.py`:

```python
import persona_genesis


def test_public_api_exposes_contract() -> None:
    from persona_genesis import Config, Persona

    assert persona_genesis.__version__ == "0.1.0"
    assert Persona.__name__ == "Persona"
    assert Config().default_locale == "en_US"


def test_exceptions_are_reachable_from_root() -> None:
    from persona_genesis import (
        CoherenceError,
        ConfigError,
        PersonaGenerationError,
        PersonaGenesisError,
        ProviderError,
    )

    for exc in (PersonaGenerationError, CoherenceError, ProviderError, ConfigError):
        assert issubclass(exc, PersonaGenesisError)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_public_api.py -v`
Expected: FAIL — `ImportError: cannot import name 'Config' from 'persona_genesis'`.

- [ ] **Step 3: Write the implementation**

Overwrite `src/persona_genesis/__init__.py`. (`PersonaGenerator` is intentionally absent — it lands in a later plan; the docstring notes this.)

```python
"""persona-genesis: generate detailed, coherent personas.

Public API at this stage exposes the data contract (`Persona` + sub-models),
configuration (`Config`), and the exception hierarchy. The `PersonaGenerator`
orchestrator is added in a subsequent milestone.
"""

from persona_genesis.config import Config, ImageConfig, LLMConfig
from persona_genesis.exceptions import (
    CoherenceError,
    ConfigError,
    PersonaGenerationError,
    PersonaGenesisError,
    ProviderError,
)
from persona_genesis.schema import (
    Appearance,
    Backstory,
    Contact,
    Device,
    Education,
    Identity,
    LifeEvent,
    Location,
    OceanScores,
    Persona,
    PersonaImages,
    PersonaMetadata,
    Personality,
    Voice,
    Work,
)

__version__ = "0.1.0"

__all__ = [
    "Appearance",
    "Backstory",
    "CoherenceError",
    "Config",
    "ConfigError",
    "Contact",
    "Device",
    "Education",
    "Identity",
    "ImageConfig",
    "LLMConfig",
    "LifeEvent",
    "Location",
    "OceanScores",
    "Persona",
    "PersonaGenerationError",
    "PersonaGenesisError",
    "PersonaImages",
    "PersonaMetadata",
    "Personality",
    "ProviderError",
    "Voice",
    "Work",
    "__version__",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_public_api.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full quality gate**

Run:

```bash
uv run ruff check .
uv run mypy
uv run pytest
```

Expected: ruff `All checks passed!`; mypy `Success: no issues found`; pytest all green.

- [ ] **Step 6: Commit**

```bash
git add src/persona_genesis/__init__.py tests/unit/test_public_api.py
git commit -m "feat: re-export public API (Persona, Config, exceptions) from package root"
```

---

## Task 17: README and CI workflow

**Files:**
- Modify: `README.md`
- Create: `.github/workflows/ci.yml`
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write the README**

Overwrite `README.md`:

```markdown
# persona-genesis

Generate highly detailed, coherent personas — structured identity, narrative
personality/backstory, and (in later milestones) visual face/body images — as a
pure-generator Python library.

> **Status:** v0.1 foundation. This milestone ships the `Persona` data contract,
> configuration, and the exception hierarchy. Generators and providers land in
> subsequent milestones.

## Install

```bash
uv add "persona-genesis @ git+https://github.com/tarsow/persona-genesis"
```

Provider integrations are opt-in extras: `[anthropic]`, `[openai]`,
`[local-image]`, `[cli]`, `[all]`.

## The contract

```python
from persona_genesis import Persona, Config

# Persona is a Pydantic model. JSON round-trips losslessly; image fields are
# excluded from serialization and handled separately by the consumer.

# Config is injected as a nested dict — the library never reads .env or the
# environment itself. Build the dict however you like (literals, a secrets
# manager, or transformed from your own .env loader — your choice).
cfg = Config.from_dict({
    "llm": {"provider": "anthropic", "api_key": "...", "model": "claude-opus-4-7"},
    "image": {"provider": "fal", "api_key": "...", "model": "fal-ai/flux/schnell"},
    "default_locale": "pt_BR",
})
```

See `specs/` for the full design and `docs/superpowers/plans/` for the
implementation plan.

## Development

```bash
uv sync
uv run ruff check .
uv run mypy
uv run pytest
```

## License

MIT — see [LICENSE](LICENSE).
```

- [ ] **Step 2: Write the CHANGELOG**

Create `CHANGELOG.md`:

```markdown
# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project scaffolding: uv + hatchling, `src/` layout, ruff/mypy/pytest, CI.
- `Persona` Pydantic schema and all sub-models (identity, location, contact,
  work, appearance, personality, voice, device, backstory, images, metadata).
- `Config` / `Config.from_dict()` accepting an injected nested config dict
  (no environment or file reading inside the library).
- Exception hierarchy (`PersonaGenesisError` and subclasses).
```

- [ ] **Step 3: Write the CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Sync dependencies
        run: uv sync
      - name: Ruff
        run: uv run ruff check .
      - name: Mypy
        run: uv run mypy
      - name: Pytest
        run: uv run pytest
```

- [ ] **Step 4: Verify the quality gate one final time**

Run:

```bash
uv run ruff check .
uv run mypy
uv run pytest
```

Expected: all three pass.

- [ ] **Step 5: Commit**

```bash
git add README.md CHANGELOG.md .github/workflows/ci.yml
git commit -m "docs: add README, CHANGELOG and CI workflow"
```

---

## Self-Review Notes

**Spec coverage (foundation slice):**
- §3.2 `Persona` model + all sub-models → Tasks 3–14. ✅
- §3.2 image fields excluded from JSON → Task 12, Task 14 Step 2. ✅
- §5 repo layout (`schema/`, `config.py`, `exceptions.py`, `pyproject.toml`, `README`, `LICENSE`, `CHANGELOG`, `.github/workflows/ci.yml`) → Tasks 1, 2, 15, 16, 17. ✅
- §6 `Config` + programmatic config → Task 15. **Deviation (per user instruction):** `Config.from_env()` / `.env` reading is replaced by `Config.from_dict()` taking an injected nested dict. The library does no env/file I/O; `pydantic-settings` and `.env.example` are dropped. The caller owns any `.env`→dict transformation.
- §6 `ConfigError` on bad config → Task 15 (validation-time, via `from_dict`). Missing-required-key checks at `PersonaGenerator` construction are deferred to the orchestrator plan, per spec wording ("not at generation time"). Noted.
- §10 dependencies + extras → Task 1 `pyproject.toml`. ✅
- §13 schema round-trip tests → every schema task. ✅
- §14 SemVer + CHANGELOG (Keep a Changelog) → Task 17. ✅

**Deferred to later plans (intentionally out of this foundation slice):** structured/narrative/visual generators, provider adapters, `PersonaGenerator` orchestrator, coherence validators, prompts, `ua_pool.py`, CLI, `RecordedProvider`, integration/snapshot tests. The `__init__` docstring and README both flag that `PersonaGenerator` is not yet present.

**Type consistency check:** sub-model class names and field names used in `tests/conftest.py` and `Persona` match their defining tasks exactly (`OceanScores`, `Education`, `LifeEvent`, `PersonaImages`, etc.). Enum `Literal` names (`Gender`, `Seniority`, `Schedule`, `Build`, `DeviceType`, `OS`, `Browser`) are exported once from `schema/__init__.py`.

**Placeholder scan:** no TBD/TODO/"handle edge cases" placeholders; every code step contains complete code.
```