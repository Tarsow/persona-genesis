# persona-genesis Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay down the project foundation for persona-genesis v0.1.0 — scaffolding, exception hierarchy, complete `Persona` Pydantic schema, configuration system, UA pool, LLM provider abstraction with Anthropic adapter, structured field generators (Faker/Polyfactory/fake-useragent), and CI. Produces a `pip install`-able library where structured generation works standalone and the LLM provider is callable — but persona orchestration (narrative + coherence + end-to-end `generate()`) is deferred to Plan 2.

**Architecture:** Standalone Python 3.12 library with `src/` layout, hatchling build backend, uv-managed dependencies. Pydantic v2 owns the `Persona` contract; pydantic-settings owns `.env` loading; httpx + the official `anthropic` SDK power the first LLM adapter; Faker + Polyfactory + fake-useragent power deterministic structured fields. TDD throughout: write the test, run it red, write minimal code, run it green, commit.

**Tech Stack:** Python 3.12 · uv · hatchling · Pydantic 2.6+ · pydantic-settings 2.2+ · httpx 0.27+ · anthropic 0.40+ · Faker 24+ · Polyfactory 2.15+ · fake-useragent 1.5+ · anyio 4+ · pytest 8+ · pytest-asyncio · ruff · mypy · GitHub Actions.

---

## File Structure

This plan creates a clean `src/` layout with parallel `tests/` mirror. Each schema sub-model, each provider, and each structured generator lives in its own focused module so files stay small and reviewable.

**Modified (rewrites of `uv init` defaults):**
- `pyproject.toml` — full project config, dependencies, dev deps, tool configs
- `.python-version` — bump 3.11 → 3.12
- `README.md` — minimal skeleton (full README is in Plan 2)
- `.gitignore` — add `.env`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`

**Deleted:**
- `main.py` (default `uv init` artifact, no longer needed)

**Created — top-level:**
- `LICENSE` — MIT
- `CHANGELOG.md` — Keep-a-Changelog format
- `.env.example`
- `.github/workflows/ci.yml`

**Created — source tree:**
```
src/persona_genesis/
├── __init__.py                  # public re-exports
├── py.typed                     # PEP 561 marker (empty file)
├── exceptions.py
├── config.py
├── ua_pool.py
├── schema/
│   ├── __init__.py              # re-exports schema models
│   ├── identity.py
│   ├── location.py
│   ├── contact.py
│   ├── work.py
│   ├── appearance.py
│   ├── personality.py
│   ├── voice.py
│   ├── device.py
│   ├── backstory.py
│   ├── images.py
│   ├── metadata.py
│   └── persona.py               # top-level Persona
├── providers/
│   ├── __init__.py
│   └── llm/
│       ├── __init__.py
│       ├── base.py              # LLMProvider Protocol
│       └── anthropic.py
└── generators/
    ├── __init__.py
    ├── base.py                  # Generator Protocol + seeding helpers
    └── structured/
        ├── __init__.py
        ├── identity.py
        ├── location.py
        ├── contact.py
        ├── work.py
        └── device.py
```

**Created — test tree:** mirrors `src/` under `tests/unit/`, plus `tests/conftest.py`.

---

## Task 1: Scaffolding — pyproject.toml, Python version, src layout, tooling

**Files:**
- Modify: `pyproject.toml`
- Modify: `.python-version`
- Delete: `main.py`
- Create: `src/persona_genesis/__init__.py`
- Create: `src/persona_genesis/py.typed`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Modify: `.gitignore`

- [ ] **Step 1.1: Bump Python version**

Replace contents of `.python-version`:
```
3.12
```

- [ ] **Step 1.2: Rewrite pyproject.toml**

Replace entire contents of `pyproject.toml`:
```toml
[project]
name = "persona-genesis"
version = "0.0.1"
description = "Generate detailed, coherent synthetic personas — identity, narrative, and visuals."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.12"
authors = [{ name = "tarsow", email = "tarsowdev@gmail.com" }]
keywords = ["persona", "synthetic-data", "faker", "llm", "test-data"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
]
dependencies = [
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "faker>=24",
    "polyfactory>=2.15",
    "fake-useragent>=1.5",
    "httpx>=0.27",
    "anyio>=4",
    "Pillow>=10",
]

[project.optional-dependencies]
anthropic = ["anthropic>=0.40"]
openai = ["openai>=1.40"]
local-image = [
    "torch>=2.3",
    "diffusers>=0.27",
    "transformers>=4.40",
    "accelerate>=0.30",
]
cli = ["typer>=0.12", "rich>=13"]
all = [
    "anthropic>=0.40",
    "openai>=1.40",
    "typer>=0.12",
    "rich>=13",
]

[project.urls]
Homepage = "https://github.com/tarsow/persona-genesis"
Issues = "https://github.com/tarsow/persona-genesis/issues"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/persona_genesis"]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5",
    "ruff>=0.5",
    "mypy>=1.10",
    "anthropic>=0.40",
    "respx>=0.21",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-ra --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E", "F", "W",       # pycodestyle + pyflakes
    "I",                 # isort
    "B",                 # bugbear
    "UP",                # pyupgrade
    "SIM",               # simplify
    "RUF",               # ruff-specific
]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src/persona_genesis", "tests"]
plugins = ["pydantic.mypy"]

[tool.coverage.run]
source = ["src/persona_genesis"]
branch = true

[tool.coverage.report]
show_missing = true
skip_covered = false
```

- [ ] **Step 1.3: Delete the default scaffold file**

Run:
```bash
rm main.py
```

- [ ] **Step 1.4: Create the src/ skeleton**

Create `src/persona_genesis/__init__.py`:
```python
"""persona-genesis — synthetic persona generation."""

__version__ = "0.0.1"

__all__ = ["__version__"]
```

Create `src/persona_genesis/py.typed` as an empty file:
```bash
touch src/persona_genesis/py.typed
```

- [ ] **Step 1.5: Create the tests/ skeleton**

Create `tests/__init__.py` as an empty file:
```bash
touch tests/__init__.py
```

Create `tests/conftest.py`:
```python
"""Shared pytest fixtures and configuration."""

import pytest


@pytest.fixture
def deterministic_seed() -> int:
    """A fixed seed used across tests that need deterministic generation."""
    return 42
```

- [ ] **Step 1.6: Extend .gitignore**

Append to `.gitignore`:
```
# Project-specific
.env
.env.local
.pytest_cache/
.ruff_cache/
.mypy_cache/
htmlcov/
.coverage
.coverage.*
```

- [ ] **Step 1.7: Sync the environment**

Run:
```bash
uv sync --all-extras
```
Expected: uv installs Python 3.12, creates `.venv/`, resolves dependencies, no errors.

- [ ] **Step 1.8: Verify tooling boots**

Run:
```bash
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q
```
Expected:
- `ruff check`: "All checks passed!"
- `mypy`: "Success: no issues found in N source files"
- `pytest`: "no tests ran" (no tests yet — that's fine, exit 5 is acceptable)

- [ ] **Step 1.9: Commit**

```bash
git add -A
git commit -m "chore: scaffold project (src layout, Python 3.12, tooling)"
```

---

## Task 2: License, CHANGELOG, .env.example, README skeleton

**Files:**
- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `.env.example`
- Modify: `README.md`

- [ ] **Step 2.1: Create LICENSE (MIT)**

Create `LICENSE`:
```
MIT License

Copyright (c) 2026 tarsow

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

- [ ] **Step 2.2: Create CHANGELOG.md**

Create `CHANGELOG.md`:
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project scaffolding (src layout, Python 3.12, hatchling, uv).
```

- [ ] **Step 2.3: Create .env.example**

Create `.env.example`:
```
# LLM provider
PERSONA_LLM_PROVIDER=anthropic              # anthropic | openai | openai_compat
PERSONA_LLM_API_KEY=
PERSONA_LLM_MODEL=claude-opus-4-7
PERSONA_LLM_BASE_URL=                       # only for openai_compat (e.g. http://localhost:11434/v1)
PERSONA_LLM_TIMEOUT_S=60
PERSONA_LLM_MAX_RETRIES=2

# Image provider (used in Plan 3 / v0.2)
PERSONA_IMAGE_PROVIDER=fal                  # fal | replicate | openai | diffusers_local
PERSONA_IMAGE_API_KEY=
PERSONA_IMAGE_MODEL=fal-ai/flux/schnell
PERSONA_IMAGE_TIMEOUT_S=120

# Defaults
PERSONA_DEFAULT_LOCALE=en_US
PERSONA_LOG_LEVEL=INFO
```

- [ ] **Step 2.4: Replace README.md with minimal skeleton**

Replace contents of `README.md`:
```markdown
# persona-genesis

Generate detailed, coherent synthetic personas — identity, narrative, and visuals.

> Status: alpha. v0.1.0 in development.

## Install

```bash
uv add persona-genesis
# or, with optional providers:
uv add "persona-genesis[anthropic]"
```

## Quickstart

See `examples/` (added in v0.1.0).

## License

MIT — see [LICENSE](./LICENSE).
```

- [ ] **Step 2.5: Commit**

```bash
git add LICENSE CHANGELOG.md .env.example README.md
git commit -m "docs: add license, changelog, env example, readme skeleton"
```

---

## Task 3: Exception hierarchy (TDD)

**Files:**
- Create: `src/persona_genesis/exceptions.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_exceptions.py`

- [ ] **Step 3.1: Create the unit-tests directory marker**

```bash
touch tests/unit/__init__.py
```

- [ ] **Step 3.2: Write failing tests**

Create `tests/unit/test_exceptions.py`:
```python
"""Tests for the exception hierarchy."""

import pytest

from persona_genesis.exceptions import (
    CoherenceError,
    ConfigError,
    PersonaGenerationError,
    PersonaGenesisError,
    ProviderError,
)


def test_base_exception_is_subclass_of_exception() -> None:
    assert issubclass(PersonaGenesisError, Exception)


@pytest.mark.parametrize(
    "subclass",
    [PersonaGenerationError, CoherenceError, ProviderError, ConfigError],
)
def test_subclasses_inherit_from_base(subclass: type[Exception]) -> None:
    assert issubclass(subclass, PersonaGenesisError)


def test_coherence_error_carries_violations() -> None:
    err = CoherenceError("age_vs_seniority", violations=["22 < 35 required for senior"])
    assert err.rule == "age_vs_seniority"
    assert err.violations == ["22 < 35 required for senior"]
    assert "age_vs_seniority" in str(err)


def test_provider_error_carries_provider_name() -> None:
    err = ProviderError("anthropic", "timeout")
    assert err.provider == "anthropic"
    assert "anthropic" in str(err)
    assert "timeout" in str(err)
```

- [ ] **Step 3.3: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/unit/test_exceptions.py -v
```
Expected: ImportError / ModuleNotFoundError on `persona_genesis.exceptions`.

- [ ] **Step 3.4: Implement exceptions**

Create `src/persona_genesis/exceptions.py`:
```python
"""Exception hierarchy for persona-genesis."""

from __future__ import annotations


class PersonaGenesisError(Exception):
    """Base class for all persona-genesis errors."""


class ConfigError(PersonaGenesisError):
    """Raised when configuration is missing or invalid."""


class ProviderError(PersonaGenesisError):
    """Raised when an LLM or image provider call fails."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class PersonaGenerationError(PersonaGenesisError):
    """Raised when persona generation fails for reasons other than coherence."""


class CoherenceError(PersonaGenesisError):
    """Raised when generated persona fields violate cross-field coherence rules."""

    def __init__(self, rule: str, violations: list[str]) -> None:
        self.rule = rule
        self.violations = violations
        super().__init__(f"coherence rule '{rule}' violated: {'; '.join(violations)}")
```

- [ ] **Step 3.5: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/unit/test_exceptions.py -v
```
Expected: 6 passed.

Run lint + type check:
```bash
uv run ruff check src/persona_genesis/exceptions.py tests/unit/test_exceptions.py
uv run mypy src/persona_genesis/exceptions.py
```
Expected: both clean.

- [ ] **Step 3.6: Commit**

```bash
git add src/persona_genesis/exceptions.py tests/unit/__init__.py tests/unit/test_exceptions.py
git commit -m "feat: add exception hierarchy"
```

---

## Task 4: Persona schema — Identity sub-model (TDD)

**Files:**
- Create: `src/persona_genesis/schema/__init__.py`
- Create: `src/persona_genesis/schema/identity.py`
- Create: `tests/unit/schema/__init__.py`
- Create: `tests/unit/schema/test_identity.py`

- [ ] **Step 4.1: Create schema package markers**

```bash
touch src/persona_genesis/schema/__init__.py tests/unit/schema/__init__.py
```

- [ ] **Step 4.2: Write failing tests**

Create `tests/unit/schema/test_identity.py`:
```python
"""Tests for the Identity schema model."""

from datetime import date

import pytest
from pydantic import ValidationError

from persona_genesis.schema.identity import Gender, Identity


def test_valid_identity_round_trips() -> None:
    identity = Identity(
        full_name="Ada Lovelace",
        given_name="Ada",
        family_name="Lovelace",
        gender=Gender.FEMALE,
        date_of_birth=date(1815, 12, 10),
        nationality="GB",
    )
    dumped = identity.model_dump_json()
    restored = Identity.model_validate_json(dumped)
    assert restored == identity


def test_age_property_is_correct_for_known_dob() -> None:
    identity = Identity(
        full_name="Test",
        given_name="Test",
        family_name="Person",
        gender=Gender.NON_BINARY,
        date_of_birth=date(2000, 1, 1),
        nationality="US",
    )
    # On any date 2026-01-01 or later, this person is at least 26.
    assert identity.age_on(date(2026, 1, 1)) == 26
    assert identity.age_on(date(2025, 12, 31)) == 25


def test_nationality_must_be_two_letter_iso() -> None:
    with pytest.raises(ValidationError):
        Identity(
            full_name="X",
            given_name="X",
            family_name="X",
            gender=Gender.MALE,
            date_of_birth=date(1990, 1, 1),
            nationality="USA",  # 3 letters — invalid
        )


def test_future_dob_rejected() -> None:
    with pytest.raises(ValidationError):
        Identity(
            full_name="X",
            given_name="X",
            family_name="X",
            gender=Gender.MALE,
            date_of_birth=date(3000, 1, 1),
            nationality="US",
        )
```

- [ ] **Step 4.3: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/unit/schema/test_identity.py -v
```
Expected: ImportError on `persona_genesis.schema.identity`.

- [ ] **Step 4.4: Implement Identity**

Create `src/persona_genesis/schema/identity.py`:
```python
"""Identity sub-model for Persona."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    OTHER = "other"


class Identity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    full_name: str = Field(min_length=1)
    given_name: str = Field(min_length=1)
    family_name: str = Field(min_length=1)
    gender: Gender
    date_of_birth: date
    nationality: str = Field(
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code (e.g. 'US', 'BR').",
    )

    @field_validator("nationality")
    @classmethod
    def _uppercase_nationality(cls, v: str) -> str:
        return v.upper()

    @field_validator("date_of_birth")
    @classmethod
    def _dob_not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return v

    def age_on(self, reference: date) -> int:
        years = reference.year - self.date_of_birth.year
        had_birthday = (reference.month, reference.day) >= (
            self.date_of_birth.month,
            self.date_of_birth.day,
        )
        return years if had_birthday else years - 1
```

- [ ] **Step 4.5: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/unit/schema/test_identity.py -v
uv run ruff check src/persona_genesis/schema tests/unit/schema
uv run mypy src/persona_genesis/schema/identity.py
```
Expected: 4 tests pass; lint + mypy clean.

- [ ] **Step 4.6: Commit**

```bash
git add src/persona_genesis/schema/__init__.py src/persona_genesis/schema/identity.py tests/unit/schema/__init__.py tests/unit/schema/test_identity.py
git commit -m "feat(schema): add Identity sub-model"
```

---

## Task 5: Persona schema — Location, Contact (TDD, batched)

**Files:**
- Create: `src/persona_genesis/schema/location.py`
- Create: `src/persona_genesis/schema/contact.py`
- Create: `tests/unit/schema/test_location.py`
- Create: `tests/unit/schema/test_contact.py`

- [ ] **Step 5.1: Write failing tests for Location**

Create `tests/unit/schema/test_location.py`:
```python
"""Tests for the Location schema model."""

import pytest
from pydantic import ValidationError

from persona_genesis.schema.location import Location


def test_valid_location_round_trips() -> None:
    loc = Location(
        country="BR",
        region="São Paulo",
        city="São Paulo",
        street="Av. Paulista 1000",
        postal_code="01310-100",
        timezone="America/Sao_Paulo",
    )
    restored = Location.model_validate_json(loc.model_dump_json())
    assert restored == loc


def test_country_normalised_to_uppercase() -> None:
    loc = Location(
        country="br",
        region="SP",
        city="São Paulo",
        street="x",
        postal_code="x",
        timezone="America/Sao_Paulo",
    )
    assert loc.country == "BR"


def test_invalid_timezone_rejected() -> None:
    with pytest.raises(ValidationError):
        Location(
            country="US",
            region="CA",
            city="San Francisco",
            street="x",
            postal_code="94000",
            timezone="Not/A_Real_Zone",
        )
```

- [ ] **Step 5.2: Run Location tests to verify they fail**

Run:
```bash
uv run pytest tests/unit/schema/test_location.py -v
```
Expected: ImportError on `persona_genesis.schema.location`.

- [ ] **Step 5.3: Implement Location**

Create `src/persona_genesis/schema/location.py`:
```python
"""Location sub-model for Persona."""

from __future__ import annotations

from zoneinfo import ZoneInfoNotFoundError, available_timezones

from pydantic import BaseModel, ConfigDict, Field, field_validator

_VALID_TIMEZONES = available_timezones()


class Location(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    country: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2.")
    region: str = Field(min_length=1, description="State, province, or region.")
    city: str = Field(min_length=1)
    street: str = Field(min_length=1, description="Street address line.")
    postal_code: str = Field(min_length=1)
    timezone: str = Field(description="IANA timezone, e.g. 'America/Sao_Paulo'.")

    @field_validator("country")
    @classmethod
    def _uppercase_country(cls, v: str) -> str:
        return v.upper()

    @field_validator("timezone")
    @classmethod
    def _valid_iana_timezone(cls, v: str) -> str:
        if v not in _VALID_TIMEZONES:
            raise ValueError(f"unknown IANA timezone: {v}") from ZoneInfoNotFoundError
        return v
```

- [ ] **Step 5.4: Run Location tests to verify they pass**

Run:
```bash
uv run pytest tests/unit/schema/test_location.py -v
```
Expected: 3 passed.

- [ ] **Step 5.5: Write failing tests for Contact**

Create `tests/unit/schema/test_contact.py`:
```python
"""Tests for the Contact schema model."""

import pytest
from pydantic import ValidationError

from persona_genesis.schema.contact import Contact


def test_valid_contact_round_trips() -> None:
    c = Contact(
        email_handle="ada.lovelace",
        phone_country_code="+44",
        phone_local_format="20 #### ####",
    )
    restored = Contact.model_validate_json(c.model_dump_json())
    assert restored == c


def test_email_handle_rejects_at_symbol() -> None:
    with pytest.raises(ValidationError):
        Contact(
            email_handle="user@example.com",
            phone_country_code="+1",
            phone_local_format="### ### ####",
        )


def test_phone_country_code_must_start_with_plus() -> None:
    with pytest.raises(ValidationError):
        Contact(
            email_handle="user",
            phone_country_code="1",
            phone_local_format="### ### ####",
        )
```

- [ ] **Step 5.6: Implement Contact**

Create `src/persona_genesis/schema/contact.py`:
```python
"""Contact sub-model for Persona.

This model intentionally stores a *phone format* (with `#` digit placeholders),
not a real number. Real phone numbers are out of scope for persona generation;
they are provisioned externally per persona by the consumer.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Contact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email_handle: str = Field(
        min_length=1,
        description="Local-part of an email (no '@'). The consumer combines this with a domain.",
    )
    phone_country_code: str = Field(
        pattern=r"^\+\d{1,3}$",
        description="International phone prefix, e.g. '+1', '+55'.",
    )
    phone_local_format: str = Field(
        min_length=1,
        description="Local phone format using '#' as digit placeholder, e.g. '### ### ####'.",
    )

    @field_validator("email_handle")
    @classmethod
    def _no_at_in_handle(cls, v: str) -> str:
        if "@" in v:
            raise ValueError("email_handle must not contain '@'")
        return v
```

- [ ] **Step 5.7: Run all schema tests + lint + mypy**

```bash
uv run pytest tests/unit/schema -v
uv run ruff check src/persona_genesis/schema tests/unit/schema
uv run mypy src/persona_genesis/schema
```
Expected: all green.

- [ ] **Step 5.8: Commit**

```bash
git add src/persona_genesis/schema/location.py src/persona_genesis/schema/contact.py tests/unit/schema/test_location.py tests/unit/schema/test_contact.py
git commit -m "feat(schema): add Location and Contact sub-models"
```

---

## Task 6: Persona schema — Work, Appearance, Personality (TDD, batched)

**Files:**
- Create: `src/persona_genesis/schema/work.py`
- Create: `src/persona_genesis/schema/appearance.py`
- Create: `src/persona_genesis/schema/personality.py`
- Create: `tests/unit/schema/test_work.py`
- Create: `tests/unit/schema/test_appearance.py`
- Create: `tests/unit/schema/test_personality.py`

- [ ] **Step 6.1: Write failing tests for Work**

Create `tests/unit/schema/test_work.py`:
```python
"""Tests for the Work schema model."""

import pytest
from pydantic import ValidationError

from persona_genesis.schema.work import Seniority, Work


def test_valid_work_round_trips() -> None:
    w = Work(
        occupation="Software Engineer",
        employer="Acme Corp",
        seniority=Seniority.MID,
        industry="Technology",
        schedule="Mon-Fri 09:00-18:00 America/Sao_Paulo",
    )
    restored = Work.model_validate_json(w.model_dump_json())
    assert restored == w


def test_seniority_min_years_lookup() -> None:
    assert Seniority.JUNIOR.minimum_years_experience == 0
    assert Seniority.MID.minimum_years_experience == 3
    assert Seniority.SENIOR.minimum_years_experience == 7
    assert Seniority.LEAD.minimum_years_experience == 10
    assert Seniority.EXECUTIVE.minimum_years_experience == 15


def test_occupation_required_non_empty() -> None:
    with pytest.raises(ValidationError):
        Work(
            occupation="",
            employer="X",
            seniority=Seniority.JUNIOR,
            industry="X",
            schedule="X",
        )
```

- [ ] **Step 6.2: Implement Work**

Create `src/persona_genesis/schema/work.py`:
```python
"""Work sub-model for Persona."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Seniority(StrEnum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"

    @property
    def minimum_years_experience(self) -> int:
        return _MIN_YEARS[self]


_MIN_YEARS: dict[Seniority, int] = {
    Seniority.JUNIOR: 0,
    Seniority.MID: 3,
    Seniority.SENIOR: 7,
    Seniority.LEAD: 10,
    Seniority.EXECUTIVE: 15,
}


class Work(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    occupation: str = Field(min_length=1)
    employer: str = Field(min_length=1)
    seniority: Seniority
    industry: str = Field(min_length=1)
    schedule: str = Field(
        min_length=1,
        description="Free-text typical work schedule, e.g. 'Mon-Fri 09:00-18:00 UTC'.",
    )
```

- [ ] **Step 6.3: Write failing tests for Appearance**

Create `tests/unit/schema/test_appearance.py`:
```python
"""Tests for the Appearance schema model."""

import pytest
from pydantic import ValidationError

from persona_genesis.schema.appearance import Appearance, Build, EyeColor, HairColor


def test_valid_appearance_round_trips() -> None:
    a = Appearance(
        height_cm=170,
        build=Build.AVERAGE,
        hair_color=HairColor.BROWN,
        eye_color=EyeColor.BROWN,
        distinguishing_features=["small scar on left cheek"],
        description="Average build, brown hair shoulder-length, warm brown eyes.",
    )
    restored = Appearance.model_validate_json(a.model_dump_json())
    assert restored == a


def test_height_must_be_realistic() -> None:
    with pytest.raises(ValidationError):
        Appearance(
            height_cm=30,  # too short
            build=Build.AVERAGE,
            hair_color=HairColor.BLACK,
            eye_color=EyeColor.BROWN,
            distinguishing_features=[],
            description="x",
        )
    with pytest.raises(ValidationError):
        Appearance(
            height_cm=300,  # too tall
            build=Build.AVERAGE,
            hair_color=HairColor.BLACK,
            eye_color=EyeColor.BROWN,
            distinguishing_features=[],
            description="x",
        )


def test_description_required_non_empty() -> None:
    with pytest.raises(ValidationError):
        Appearance(
            height_cm=170,
            build=Build.AVERAGE,
            hair_color=HairColor.BLACK,
            eye_color=EyeColor.BROWN,
            distinguishing_features=[],
            description="",
        )
```

- [ ] **Step 6.4: Implement Appearance**

Create `src/persona_genesis/schema/appearance.py`:
```python
"""Appearance sub-model for Persona."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Build(StrEnum):
    SLIM = "slim"
    AVERAGE = "average"
    ATHLETIC = "athletic"
    HEAVY = "heavy"


class HairColor(StrEnum):
    BLACK = "black"
    BROWN = "brown"
    BLOND = "blond"
    RED = "red"
    GRAY = "gray"
    WHITE = "white"
    OTHER = "other"


class EyeColor(StrEnum):
    BROWN = "brown"
    BLUE = "blue"
    GREEN = "green"
    HAZEL = "hazel"
    GRAY = "gray"
    AMBER = "amber"
    OTHER = "other"


class Appearance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    height_cm: int = Field(ge=120, le=230)
    build: Build
    hair_color: HairColor
    eye_color: EyeColor
    distinguishing_features: list[str] = Field(default_factory=list)
    description: str = Field(
        min_length=1,
        description="Free-text narrative description of overall appearance.",
    )
```

- [ ] **Step 6.5: Write failing tests for Personality**

Create `tests/unit/schema/test_personality.py`:
```python
"""Tests for the Personality schema model."""

import pytest
from pydantic import ValidationError

from persona_genesis.schema.personality import OceanTraits, Personality


def test_valid_personality_round_trips() -> None:
    p = Personality(
        ocean=OceanTraits(
            openness=0.7,
            conscientiousness=0.6,
            extraversion=0.4,
            agreeableness=0.8,
            neuroticism=0.3,
        ),
        descriptive_traits=["curious", "patient", "analytical"],
        values=["honesty", "learning"],
        quirks=["always carries a paperback novel"],
    )
    restored = Personality.model_validate_json(p.model_dump_json())
    assert restored == p


def test_ocean_scores_clamped_to_unit_interval() -> None:
    with pytest.raises(ValidationError):
        OceanTraits(
            openness=1.5,  # out of range
            conscientiousness=0.5,
            extraversion=0.5,
            agreeableness=0.5,
            neuroticism=0.5,
        )
```

- [ ] **Step 6.6: Implement Personality**

Create `src/persona_genesis/schema/personality.py`:
```python
"""Personality sub-model for Persona (Big-Five / OCEAN + descriptors)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OceanTraits(BaseModel):
    """Big-Five personality dimensions, each in [0.0, 1.0]."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)


class Personality(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ocean: OceanTraits
    descriptive_traits: list[str] = Field(
        default_factory=list,
        description="Short adjectives describing personality (e.g. 'curious', 'patient').",
    )
    values: list[str] = Field(
        default_factory=list,
        description="Things this persona prioritises (e.g. 'family', 'craftsmanship').",
    )
    quirks: list[str] = Field(
        default_factory=list,
        description="Distinctive habits or mannerisms.",
    )
```

- [ ] **Step 6.7: Run all schema tests + lint + mypy**

```bash
uv run pytest tests/unit/schema -v
uv run ruff check src/persona_genesis/schema tests/unit/schema
uv run mypy src/persona_genesis/schema
```
Expected: all green.

- [ ] **Step 6.8: Commit**

```bash
git add src/persona_genesis/schema/work.py src/persona_genesis/schema/appearance.py src/persona_genesis/schema/personality.py tests/unit/schema/test_work.py tests/unit/schema/test_appearance.py tests/unit/schema/test_personality.py
git commit -m "feat(schema): add Work, Appearance, Personality sub-models"
```

---

## Task 7: Persona schema — Voice, Device, Backstory, Images, Metadata (TDD, batched)

**Files:**
- Create: `src/persona_genesis/schema/voice.py`
- Create: `src/persona_genesis/schema/device.py`
- Create: `src/persona_genesis/schema/backstory.py`
- Create: `src/persona_genesis/schema/images.py`
- Create: `src/persona_genesis/schema/metadata.py`
- Create: `tests/unit/schema/test_voice.py`
- Create: `tests/unit/schema/test_device.py`
- Create: `tests/unit/schema/test_backstory.py`
- Create: `tests/unit/schema/test_metadata.py`

- [ ] **Step 7.1: Write failing tests for Voice**

Create `tests/unit/schema/test_voice.py`:
```python
"""Tests for the Voice schema model."""

import pytest
from pydantic import ValidationError

from persona_genesis.schema.voice import PostingCadence, Voice


def test_valid_voice_round_trips() -> None:
    v = Voice(
        writing_style="casual, uses lowercase, sparse punctuation",
        posting_cadence=PostingCadence.DAILY,
        typical_topics=["coffee", "running", "indie games"],
        sample_paragraph="just got back from a 10k. legs are toast but worth it.",
    )
    restored = Voice.model_validate_json(v.model_dump_json())
    assert restored == v


def test_sample_paragraph_required_non_empty() -> None:
    with pytest.raises(ValidationError):
        Voice(
            writing_style="x",
            posting_cadence=PostingCadence.WEEKLY,
            typical_topics=["x"],
            sample_paragraph="",
        )
```

- [ ] **Step 7.2: Implement Voice**

Create `src/persona_genesis/schema/voice.py`:
```python
"""Voice sub-model for Persona — written communication style."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PostingCadence(StrEnum):
    RARE = "rare"             # less than once a week
    WEEKLY = "weekly"
    DAILY = "daily"
    MULTIPLE_DAILY = "multiple_daily"


class Voice(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    writing_style: str = Field(
        min_length=1,
        description="Free-text description of writing tendencies (tone, punctuation, vocabulary).",
    )
    posting_cadence: PostingCadence
    typical_topics: list[str] = Field(default_factory=list)
    sample_paragraph: str = Field(
        min_length=1,
        description="A representative short paragraph in the persona's voice.",
    )
```

- [ ] **Step 7.3: Write failing tests for Device**

Create `tests/unit/schema/test_device.py`:
```python
"""Tests for the Device schema model."""

import pytest
from pydantic import ValidationError

from persona_genesis.schema.device import BrowserFamily, Device, DevicePlatform


def test_valid_device_round_trips() -> None:
    d = Device(
        platform=DevicePlatform.ANDROID,
        device_model="Pixel 8",
        os_version="Android 14",
        browser=BrowserFamily.CHROME,
        browser_version="125.0",
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
        ),
        screen_resolution="1080x2400",
    )
    restored = Device.model_validate_json(d.model_dump_json())
    assert restored == d


def test_screen_resolution_must_match_wxh_pattern() -> None:
    with pytest.raises(ValidationError):
        Device(
            platform=DevicePlatform.IOS,
            device_model="iPhone 15",
            os_version="iOS 17",
            browser=BrowserFamily.SAFARI,
            browser_version="17.0",
            user_agent="Mozilla/5.0 ...",
            screen_resolution="big",
        )
```

- [ ] **Step 7.4: Implement Device**

Create `src/persona_genesis/schema/device.py`:
```python
"""Device sub-model for Persona — hardware/OS/browser used by the persona."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DevicePlatform(StrEnum):
    ANDROID = "android"
    IOS = "ios"
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


class BrowserFamily(StrEnum):
    CHROME = "chrome"
    SAFARI = "safari"
    FIREFOX = "firefox"
    EDGE = "edge"


class Device(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    platform: DevicePlatform
    device_model: str = Field(min_length=1, description="e.g. 'Pixel 8', 'iPhone 15', 'ThinkPad X1'.")
    os_version: str = Field(min_length=1)
    browser: BrowserFamily
    browser_version: str = Field(min_length=1)
    user_agent: str = Field(min_length=1)
    screen_resolution: str = Field(
        pattern=r"^\d{3,5}x\d{3,5}$",
        description="WIDTHxHEIGHT in pixels.",
    )
```

- [ ] **Step 7.5: Write failing tests for Backstory**

Create `tests/unit/schema/test_backstory.py`:
```python
"""Tests for the Backstory schema model."""

from datetime import date

import pytest
from pydantic import ValidationError

from persona_genesis.schema.backstory import Backstory, LifeEvent


def test_valid_backstory_round_trips() -> None:
    b = Backstory(
        bio="Grew up in São Paulo, studied biology, now works as a science writer.",
        education=["BSc Biology, USP, 2010"],
        key_life_events=[
            LifeEvent(year=2010, description="Graduated university."),
            LifeEvent(year=2014, description="Moved to Berlin for first job."),
        ],
    )
    restored = Backstory.model_validate_json(b.model_dump_json())
    assert restored == b


def test_life_events_year_must_be_realistic() -> None:
    with pytest.raises(ValidationError):
        LifeEvent(year=1800, description="x")
    with pytest.raises(ValidationError):
        LifeEvent(year=date.today().year + 50, description="x")


def test_bio_required_non_empty() -> None:
    with pytest.raises(ValidationError):
        Backstory(bio="", education=[], key_life_events=[])
```

- [ ] **Step 7.6: Implement Backstory**

Create `src/persona_genesis/schema/backstory.py`:
```python
"""Backstory sub-model for Persona."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class LifeEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    year: int = Field(ge=1900, le=date.today().year + 1)
    description: str = Field(min_length=1)


class Backstory(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    bio: str = Field(min_length=1, description="Short narrative bio (1-3 paragraphs).")
    education: list[str] = Field(
        default_factory=list,
        description="Education entries, free-text (e.g. 'BSc Biology, USP, 2010').",
    )
    key_life_events: list[LifeEvent] = Field(default_factory=list)
```

- [ ] **Step 7.7: Implement Images and Metadata (no separate tests — covered in Task 8)**

Create `src/persona_genesis/schema/images.py`:
```python
"""Container for generated persona images.

Images are intentionally excluded from default JSON serialization — consumers
decide how to persist binary data (file paths, object storage, base64, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from PIL.Image import Image
else:
    Image = object  # avoid hard import at runtime; populated when Pillow loads it


class PersonaImages(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True,
        extra="forbid",
    )

    face: object | None = Field(
        default=None,
        exclude=True,
        description="Optional face image (PIL.Image.Image). Excluded from JSON dumps.",
    )
    body: object | None = Field(
        default=None,
        exclude=True,
        description="Optional body image (PIL.Image.Image). Excluded from JSON dumps.",
    )
```

Create `src/persona_genesis/schema/metadata.py`:
```python
"""Persona generation metadata — provenance and reproducibility info."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonaMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    generated_at: datetime
    generator_version: str = Field(min_length=1)
    llm_provider: str | None = None
    llm_model: str | None = None
    image_provider: str | None = None
    image_model: str | None = None
    seed: int | None = None
```

- [ ] **Step 7.8: Add a basic Metadata test**

Create `tests/unit/schema/test_metadata.py`:
```python
"""Tests for PersonaMetadata."""

from datetime import datetime, timezone

from persona_genesis.schema.metadata import PersonaMetadata


def test_metadata_round_trips() -> None:
    m = PersonaMetadata(
        generated_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        generator_version="0.0.1",
        llm_provider="anthropic",
        llm_model="claude-opus-4-7",
        seed=42,
    )
    restored = PersonaMetadata.model_validate_json(m.model_dump_json())
    assert restored == m
```

- [ ] **Step 7.9: Run all schema tests + lint + mypy**

```bash
uv run pytest tests/unit/schema -v
uv run ruff check src/persona_genesis/schema tests/unit/schema
uv run mypy src/persona_genesis/schema
```
Expected: all green.

- [ ] **Step 7.10: Commit**

```bash
git add src/persona_genesis/schema/voice.py src/persona_genesis/schema/device.py src/persona_genesis/schema/backstory.py src/persona_genesis/schema/images.py src/persona_genesis/schema/metadata.py tests/unit/schema/test_voice.py tests/unit/schema/test_device.py tests/unit/schema/test_backstory.py tests/unit/schema/test_metadata.py
git commit -m "feat(schema): add Voice, Device, Backstory, Images, Metadata"
```

---

## Task 8: Top-level Persona model + serialization round-trip (TDD)

**Files:**
- Create: `src/persona_genesis/schema/persona.py`
- Modify: `src/persona_genesis/schema/__init__.py`
- Modify: `src/persona_genesis/__init__.py`
- Create: `tests/unit/schema/test_persona.py`

- [ ] **Step 8.1: Write failing tests**

Create `tests/unit/schema/test_persona.py`:
```python
"""Tests for the top-level Persona model and its serialization."""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from persona_genesis.schema.appearance import Appearance, Build, EyeColor, HairColor
from persona_genesis.schema.backstory import Backstory
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.device import BrowserFamily, Device, DevicePlatform
from persona_genesis.schema.identity import Gender, Identity
from persona_genesis.schema.location import Location
from persona_genesis.schema.metadata import PersonaMetadata
from persona_genesis.schema.persona import Persona
from persona_genesis.schema.personality import OceanTraits, Personality
from persona_genesis.schema.voice import PostingCadence, Voice
from persona_genesis.schema.work import Seniority, Work


def _make_persona(persona_id: UUID | None = None) -> Persona:
    return Persona(
        id=persona_id or uuid4(),
        seed=42,
        locale="pt_BR",
        identity=Identity(
            full_name="Ana Souza",
            given_name="Ana",
            family_name="Souza",
            gender=Gender.FEMALE,
            date_of_birth=date(1992, 4, 15),
            nationality="BR",
        ),
        location=Location(
            country="BR",
            region="São Paulo",
            city="São Paulo",
            street="Rua Augusta 1234",
            postal_code="01304-001",
            timezone="America/Sao_Paulo",
        ),
        contact=Contact(
            email_handle="ana.souza",
            phone_country_code="+55",
            phone_local_format="(##) #####-####",
        ),
        work=Work(
            occupation="Science Writer",
            employer="Veja Ciência",
            seniority=Seniority.MID,
            industry="Media",
            schedule="Mon-Fri 09:00-17:00 America/Sao_Paulo",
        ),
        appearance=Appearance(
            height_cm=165,
            build=Build.AVERAGE,
            hair_color=HairColor.BROWN,
            eye_color=EyeColor.BROWN,
            distinguishing_features=["small mole near right eyebrow"],
            description="Shoulder-length brown hair, warm brown eyes, average build.",
        ),
        personality=Personality(
            ocean=OceanTraits(
                openness=0.75,
                conscientiousness=0.60,
                extraversion=0.45,
                agreeableness=0.70,
                neuroticism=0.35,
            ),
            descriptive_traits=["curious", "patient"],
            values=["learning", "honesty"],
            quirks=["carries a paperback everywhere"],
        ),
        voice=Voice(
            writing_style="conversational, occasional Portuguese expressions",
            posting_cadence=PostingCadence.WEEKLY,
            typical_topics=["biology", "books", "running"],
            sample_paragraph="acabei de ler um livro incrível sobre fungos.",
        ),
        device=Device(
            platform=DevicePlatform.ANDROID,
            device_model="Pixel 7",
            os_version="Android 14",
            browser=BrowserFamily.CHROME,
            browser_version="125.0",
            user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 7) ...",
            screen_resolution="1080x2400",
        ),
        backstory=Backstory(
            bio="Grew up in São Paulo, studied biology, became a science writer.",
            education=["BSc Biology, USP, 2014"],
            key_life_events=[],
        ),
        metadata=PersonaMetadata(
            generated_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            generator_version="0.0.1",
            llm_provider="anthropic",
            llm_model="claude-opus-4-7",
            seed=42,
        ),
    )


def test_persona_round_trips_without_images() -> None:
    p = _make_persona()
    dumped = p.model_dump_json()
    restored = Persona.model_validate_json(dumped)
    assert restored == p


def test_persona_id_is_uuid() -> None:
    p = _make_persona(persona_id=UUID("00000000-0000-0000-0000-000000000001"))
    assert p.id == UUID("00000000-0000-0000-0000-000000000001")


def test_persona_default_images_field_is_empty() -> None:
    p = _make_persona()
    assert p.images.face is None
    assert p.images.body is None


def test_persona_top_level_is_re_exported_from_package() -> None:
    from persona_genesis import Persona as TopLevelPersona

    assert TopLevelPersona is Persona
```

- [ ] **Step 8.2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/schema/test_persona.py -v
```
Expected: ImportError on `persona_genesis.schema.persona`.

- [ ] **Step 8.3: Implement top-level Persona**

Create `src/persona_genesis/schema/persona.py`:
```python
"""Top-level Persona model — the public contract of persona-genesis."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    id: UUID
    seed: int | None = None
    locale: str = Field(min_length=2, description="BCP-47 locale tag, e.g. 'en_US', 'pt_BR'.")

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

- [ ] **Step 8.4: Re-export from schema package and top-level**

Replace `src/persona_genesis/schema/__init__.py`:
```python
"""Public schema re-exports."""

from persona_genesis.schema.appearance import Appearance, Build, EyeColor, HairColor
from persona_genesis.schema.backstory import Backstory, LifeEvent
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.device import BrowserFamily, Device, DevicePlatform
from persona_genesis.schema.identity import Gender, Identity
from persona_genesis.schema.images import PersonaImages
from persona_genesis.schema.location import Location
from persona_genesis.schema.metadata import PersonaMetadata
from persona_genesis.schema.persona import Persona
from persona_genesis.schema.personality import OceanTraits, Personality
from persona_genesis.schema.voice import PostingCadence, Voice
from persona_genesis.schema.work import Seniority, Work

__all__ = [
    "Appearance",
    "Backstory",
    "BrowserFamily",
    "Build",
    "Contact",
    "Device",
    "DevicePlatform",
    "EyeColor",
    "Gender",
    "HairColor",
    "Identity",
    "LifeEvent",
    "Location",
    "OceanTraits",
    "Persona",
    "PersonaImages",
    "PersonaMetadata",
    "Personality",
    "PostingCadence",
    "Seniority",
    "Voice",
    "Work",
]
```

Replace `src/persona_genesis/__init__.py`:
```python
"""persona-genesis — synthetic persona generation."""

from persona_genesis.schema import Persona

__version__ = "0.0.1"

__all__ = ["Persona", "__version__"]
```

- [ ] **Step 8.5: Run tests + lint + mypy**

```bash
uv run pytest tests/unit -v
uv run ruff check src tests
uv run mypy src tests
```
Expected: all green.

- [ ] **Step 8.6: Commit**

```bash
git add src/persona_genesis/schema/persona.py src/persona_genesis/schema/__init__.py src/persona_genesis/__init__.py tests/unit/schema/test_persona.py
git commit -m "feat(schema): add top-level Persona model and re-exports"
```

---

## Task 9: Config module (TDD)

**Files:**
- Create: `src/persona_genesis/config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 9.1: Write failing tests**

Create `tests/unit/test_config.py`:
```python
"""Tests for the Config module."""

import pytest

from persona_genesis.config import Config, ImageConfig, LLMConfig, LLMProviderName
from persona_genesis.exceptions import ConfigError


def test_explicit_construction() -> None:
    c = Config(
        llm=LLMConfig(
            provider=LLMProviderName.ANTHROPIC,
            api_key="sk-test",
            model="claude-opus-4-7",
        ),
    )
    assert c.llm.provider is LLMProviderName.ANTHROPIC
    assert c.llm.api_key == "sk-test"
    assert c.default_locale == "en_US"  # default


def test_from_env_reads_anthropic_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSONA_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("PERSONA_LLM_API_KEY", "sk-from-env")
    monkeypatch.setenv("PERSONA_LLM_MODEL", "claude-opus-4-7")
    monkeypatch.setenv("PERSONA_DEFAULT_LOCALE", "pt_BR")
    monkeypatch.delenv("PERSONA_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("PERSONA_IMAGE_PROVIDER", raising=False)
    monkeypatch.delenv("PERSONA_IMAGE_API_KEY", raising=False)
    monkeypatch.delenv("PERSONA_IMAGE_MODEL", raising=False)

    c = Config.from_env()
    assert c.llm.api_key == "sk-from-env"
    assert c.default_locale == "pt_BR"


def test_openai_compat_requires_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSONA_LLM_PROVIDER", "openai_compat")
    monkeypatch.setenv("PERSONA_LLM_API_KEY", "x")
    monkeypatch.setenv("PERSONA_LLM_MODEL", "llama3.1:8b")
    monkeypatch.delenv("PERSONA_LLM_BASE_URL", raising=False)

    with pytest.raises(ConfigError, match="base_url"):
        Config.from_env()


def test_missing_api_key_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSONA_LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("PERSONA_LLM_API_KEY", raising=False)
    monkeypatch.setenv("PERSONA_LLM_MODEL", "claude-opus-4-7")

    with pytest.raises(ConfigError, match="api_key"):
        Config.from_env()


def test_image_config_optional_in_v01_foundation() -> None:
    c = Config(
        llm=LLMConfig(
            provider=LLMProviderName.ANTHROPIC,
            api_key="x",
            model="claude-opus-4-7",
        ),
    )
    assert c.image is None
```

- [ ] **Step 9.2: Run to verify failure**

```bash
uv run pytest tests/unit/test_config.py -v
```
Expected: ImportError on `persona_genesis.config`.

- [ ] **Step 9.3: Implement Config**

Create `src/persona_genesis/config.py`:
```python
"""Configuration models — loadable from .env or constructed directly."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from persona_genesis.exceptions import ConfigError


class LLMProviderName(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OPENAI_COMPAT = "openai_compat"


class ImageProviderName(StrEnum):
    FAL = "fal"
    REPLICATE = "replicate"
    OPENAI = "openai"
    DIFFUSERS_LOCAL = "diffusers_local"


class LLMConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: LLMProviderName
    api_key: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: str | None = None
    timeout_s: int = Field(default=60, ge=1, le=600)
    max_retries: int = Field(default=2, ge=0, le=10)


class ImageConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: ImageProviderName
    api_key: str = Field(min_length=1)
    model: str = Field(min_length=1)
    timeout_s: int = Field(default=120, ge=1, le=600)


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    llm: LLMConfig
    image: ImageConfig | None = None
    default_locale: str = "en_US"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Config:
        """Load Config from environment variables / .env."""
        try:
            env = _EnvSettings()
        except ValidationError as e:
            raise ConfigError(f"invalid PERSONA_* environment configuration: {e}") from e

        if env.llm_provider is LLMProviderName.OPENAI_COMPAT and not env.llm_base_url:
            raise ConfigError("PERSONA_LLM_BASE_URL is required when provider=openai_compat")
        if not env.llm_api_key:
            raise ConfigError("PERSONA_LLM_API_KEY is required")
        if not env.llm_model:
            raise ConfigError("PERSONA_LLM_MODEL is required")

        llm = LLMConfig(
            provider=env.llm_provider,
            api_key=env.llm_api_key,
            model=env.llm_model,
            base_url=env.llm_base_url or None,
            timeout_s=env.llm_timeout_s,
            max_retries=env.llm_max_retries,
        )

        image: ImageConfig | None = None
        if env.image_provider and env.image_api_key and env.image_model:
            image = ImageConfig(
                provider=env.image_provider,
                api_key=env.image_api_key,
                model=env.image_model,
                timeout_s=env.image_timeout_s,
            )

        return cls(
            llm=llm,
            image=image,
            default_locale=env.default_locale,
            log_level=env.log_level,
        )


class _EnvSettings(BaseSettings):
    """Internal pydantic-settings wrapper. Keys map to PERSONA_* env vars."""

    model_config = SettingsConfigDict(
        env_prefix="PERSONA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_provider: LLMProviderName = LLMProviderName.ANTHROPIC
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    llm_timeout_s: int = 60
    llm_max_retries: int = 2

    image_provider: ImageProviderName | None = None
    image_api_key: str = ""
    image_model: str = ""
    image_timeout_s: int = 120

    default_locale: str = "en_US"
    log_level: str = "INFO"
```

- [ ] **Step 9.4: Run tests + lint + mypy**

```bash
uv run pytest tests/unit/test_config.py -v
uv run ruff check src/persona_genesis/config.py tests/unit/test_config.py
uv run mypy src/persona_genesis/config.py
```
Expected: all green.

- [ ] **Step 9.5: Commit**

```bash
git add src/persona_genesis/config.py tests/unit/test_config.py
git commit -m "feat: add Config with .env loading and validation"
```

---

## Task 10: UA pool (TDD)

**Files:**
- Create: `src/persona_genesis/ua_pool.py`
- Create: `tests/unit/test_ua_pool.py`

- [ ] **Step 10.1: Write failing tests**

Create `tests/unit/test_ua_pool.py`:
```python
"""Tests for the curated UA pool."""

import random

from persona_genesis.schema.device import BrowserFamily, DevicePlatform
from persona_genesis.ua_pool import UAEntry, UAPool


def test_pool_has_entries_for_all_platform_browser_combos() -> None:
    pool = UAPool.default()
    for platform in DevicePlatform:
        for browser in BrowserFamily:
            entries = pool.entries_for(platform=platform, browser=browser)
            # Not every combo needs entries (e.g., Safari on Android is empty),
            # but the typical ones must be populated.
            if (platform, browser) in {
                (DevicePlatform.ANDROID, BrowserFamily.CHROME),
                (DevicePlatform.IOS, BrowserFamily.SAFARI),
                (DevicePlatform.WINDOWS, BrowserFamily.CHROME),
                (DevicePlatform.WINDOWS, BrowserFamily.FIREFOX),
                (DevicePlatform.MACOS, BrowserFamily.SAFARI),
                (DevicePlatform.LINUX, BrowserFamily.FIREFOX),
            }:
                assert entries, f"expected entries for {platform}/{browser}"


def test_pool_pick_is_deterministic_with_seeded_rng() -> None:
    pool = UAPool.default()
    rng_a = random.Random(42)
    rng_b = random.Random(42)
    entry_a = pool.pick(platform=DevicePlatform.ANDROID, browser=BrowserFamily.CHROME, rng=rng_a)
    entry_b = pool.pick(platform=DevicePlatform.ANDROID, browser=BrowserFamily.CHROME, rng=rng_b)
    assert entry_a == entry_b


def test_entry_user_agent_string_round_trips() -> None:
    entry = UAEntry(
        platform=DevicePlatform.WINDOWS,
        browser=BrowserFamily.CHROME,
        device_model="Generic PC",
        os_version="Windows 11",
        browser_version="125.0",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
        screen_resolution="1920x1080",
    )
    assert entry.user_agent.startswith("Mozilla/5.0")
```

- [ ] **Step 10.2: Implement UAPool**

Create `src/persona_genesis/ua_pool.py`:
```python
"""Curated User-Agent pool, keyed by (platform, browser).

The default pool is intentionally small but representative — it is a starting
point. Consumers can pass their own UAPool to the generator if they need wider
coverage or freshly-scraped entries.
"""

from __future__ import annotations

import random

from pydantic import BaseModel, ConfigDict, Field

from persona_genesis.schema.device import BrowserFamily, DevicePlatform


class UAEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    platform: DevicePlatform
    browser: BrowserFamily
    device_model: str = Field(min_length=1)
    os_version: str = Field(min_length=1)
    browser_version: str = Field(min_length=1)
    user_agent: str = Field(min_length=1)
    screen_resolution: str = Field(pattern=r"^\d{3,5}x\d{3,5}$")


class UAPool:
    """A pool of UAEntry values, queried by (platform, browser)."""

    def __init__(self, entries: list[UAEntry]) -> None:
        self._entries = entries

    def entries_for(
        self, *, platform: DevicePlatform, browser: BrowserFamily
    ) -> list[UAEntry]:
        return [e for e in self._entries if e.platform is platform and e.browser is browser]

    def pick(
        self,
        *,
        platform: DevicePlatform,
        browser: BrowserFamily,
        rng: random.Random,
    ) -> UAEntry:
        candidates = self.entries_for(platform=platform, browser=browser)
        if not candidates:
            raise LookupError(f"no UA entries for {platform}/{browser}")
        return rng.choice(candidates)

    @classmethod
    def default(cls) -> UAPool:
        return cls(_DEFAULT_ENTRIES)


_DEFAULT_ENTRIES: list[UAEntry] = [
    UAEntry(
        platform=DevicePlatform.ANDROID,
        browser=BrowserFamily.CHROME,
        device_model="Pixel 8",
        os_version="Android 14",
        browser_version="125.0",
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
        ),
        screen_resolution="1080x2400",
    ),
    UAEntry(
        platform=DevicePlatform.ANDROID,
        browser=BrowserFamily.CHROME,
        device_model="Samsung Galaxy S23",
        os_version="Android 14",
        browser_version="125.0",
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
        ),
        screen_resolution="1080x2340",
    ),
    UAEntry(
        platform=DevicePlatform.IOS,
        browser=BrowserFamily.SAFARI,
        device_model="iPhone 15",
        os_version="iOS 17.4",
        browser_version="17.4",
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
        ),
        screen_resolution="1179x2556",
    ),
    UAEntry(
        platform=DevicePlatform.WINDOWS,
        browser=BrowserFamily.CHROME,
        device_model="Generic PC",
        os_version="Windows 11",
        browser_version="125.0",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        screen_resolution="1920x1080",
    ),
    UAEntry(
        platform=DevicePlatform.WINDOWS,
        browser=BrowserFamily.FIREFOX,
        device_model="Generic PC",
        os_version="Windows 11",
        browser_version="125.0",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        screen_resolution="1920x1080",
    ),
    UAEntry(
        platform=DevicePlatform.MACOS,
        browser=BrowserFamily.SAFARI,
        device_model="MacBook Pro 14",
        os_version="macOS 14.4",
        browser_version="17.4",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
        ),
        screen_resolution="3024x1964",
    ),
    UAEntry(
        platform=DevicePlatform.LINUX,
        browser=BrowserFamily.FIREFOX,
        device_model="Generic PC",
        os_version="Ubuntu 24.04",
        browser_version="125.0",
        user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        screen_resolution="1920x1080",
    ),
]
```

- [ ] **Step 10.3: Run tests + lint + mypy**

```bash
uv run pytest tests/unit/test_ua_pool.py -v
uv run ruff check src/persona_genesis/ua_pool.py tests/unit/test_ua_pool.py
uv run mypy src/persona_genesis/ua_pool.py
```
Expected: all green.

- [ ] **Step 10.4: Commit**

```bash
git add src/persona_genesis/ua_pool.py tests/unit/test_ua_pool.py
git commit -m "feat: add curated UA pool with deterministic picking"
```

---

## Task 11: LLM Provider protocol (TDD)

**Files:**
- Create: `src/persona_genesis/providers/__init__.py`
- Create: `src/persona_genesis/providers/llm/__init__.py`
- Create: `src/persona_genesis/providers/llm/base.py`
- Create: `tests/unit/providers/__init__.py`
- Create: `tests/unit/providers/llm/__init__.py`
- Create: `tests/unit/providers/llm/test_base.py`

- [ ] **Step 11.1: Create provider package markers**

```bash
touch src/persona_genesis/providers/__init__.py
touch src/persona_genesis/providers/llm/__init__.py
touch tests/unit/providers/__init__.py
touch tests/unit/providers/llm/__init__.py
```

- [ ] **Step 11.2: Write failing test**

Create `tests/unit/providers/llm/test_base.py`:
```python
"""Tests for the LLMProvider protocol."""

from typing import get_type_hints

from pydantic import BaseModel

from persona_genesis.providers.llm.base import LLMProvider


class _DummyModel(BaseModel):
    answer: str


class _DummyProvider:
    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str:
        return f"sys={system};user={user};temp={temperature}"

    async def acomplete_json(
        self, system: str, user: str, schema: type[BaseModel]
    ) -> BaseModel:
        return schema(answer="ok")


def test_dummy_satisfies_protocol_at_runtime() -> None:
    provider: LLMProvider = _DummyProvider()
    assert provider is not None


def test_protocol_methods_have_expected_hints() -> None:
    hints = get_type_hints(LLMProvider.acomplete)
    assert hints["return"] is str
```

- [ ] **Step 11.3: Implement the protocol**

Create `src/persona_genesis/providers/llm/base.py`:
```python
"""LLMProvider Protocol — adapters must implement these two methods."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class LLMProvider(Protocol):
    """Async LLM provider interface.

    Implementations are constructed with their provider-specific config and
    expose two methods:

    * `acomplete` — free-form text completion.
    * `acomplete_json` — completion constrained to a Pydantic schema (the
      implementation is responsible for using JSON mode / tool-use / function
      calling to make the model return valid JSON for the given schema).
    """

    async def acomplete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.7,
    ) -> str: ...

    async def acomplete_json(
        self,
        system: str,
        user: str,
        schema: type[BaseModel],
    ) -> BaseModel: ...
```

- [ ] **Step 11.4: Run + lint + mypy**

```bash
uv run pytest tests/unit/providers -v
uv run ruff check src/persona_genesis/providers tests/unit/providers
uv run mypy src/persona_genesis/providers
```
Expected: all green.

- [ ] **Step 11.5: Commit**

```bash
git add src/persona_genesis/providers tests/unit/providers
git commit -m "feat(providers): add LLMProvider protocol"
```

---

## Task 12: AnthropicProvider adapter (TDD with respx)

**Files:**
- Create: `src/persona_genesis/providers/llm/anthropic.py`
- Create: `tests/unit/providers/llm/test_anthropic.py`

- [ ] **Step 12.1: Write failing tests**

Create `tests/unit/providers/llm/test_anthropic.py`:
```python
"""Tests for the AnthropicProvider adapter.

We use the official `anthropic` SDK and mock its HTTP layer with respx.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from pydantic import BaseModel

from persona_genesis.exceptions import ProviderError
from persona_genesis.providers.llm.anthropic import AnthropicProvider

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


class _Answer(BaseModel):
    answer: str
    confidence: float


@respx.mock
async def test_acomplete_returns_text() -> None:
    respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-4-7",
                "content": [{"type": "text", "text": "hello world"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 5, "output_tokens": 2},
            },
        )
    )

    provider = AnthropicProvider(api_key="sk-test", model="claude-opus-4-7")
    out = await provider.acomplete(system="be brief", user="hi")
    assert out == "hello world"


@respx.mock
async def test_acomplete_json_parses_into_schema() -> None:
    payload = {"answer": "42", "confidence": 0.9}
    respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_2",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-4-7",
                "content": [{"type": "text", "text": json.dumps(payload)}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 5, "output_tokens": 2},
            },
        )
    )

    provider = AnthropicProvider(api_key="sk-test", model="claude-opus-4-7")
    result = await provider.acomplete_json(system="answer", user="q?", schema=_Answer)
    assert isinstance(result, _Answer)
    assert result.answer == "42"
    assert result.confidence == 0.9


@respx.mock
async def test_acomplete_json_raises_on_invalid_json() -> None:
    respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_3",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-4-7",
                "content": [{"type": "text", "text": "not json"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 5, "output_tokens": 2},
            },
        )
    )

    provider = AnthropicProvider(api_key="sk-test", model="claude-opus-4-7")
    with pytest.raises(ProviderError, match="anthropic"):
        await provider.acomplete_json(system="x", user="x", schema=_Answer)


@respx.mock
async def test_acomplete_raises_provider_error_on_http_failure() -> None:
    respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(500, json={"error": "server"})
    )

    provider = AnthropicProvider(api_key="sk-test", model="claude-opus-4-7")
    with pytest.raises(ProviderError, match="anthropic"):
        await provider.acomplete(system="x", user="x")
```

- [ ] **Step 12.2: Run to verify failure**

```bash
uv run pytest tests/unit/providers/llm/test_anthropic.py -v
```
Expected: ImportError on `persona_genesis.providers.llm.anthropic`.

- [ ] **Step 12.3: Implement AnthropicProvider**

Create `src/persona_genesis/providers/llm/anthropic.py`:
```python
"""Anthropic LLM provider — uses the official `anthropic` SDK over httpx."""

from __future__ import annotations

import json

from anthropic import AsyncAnthropic
from anthropic import APIError as AnthropicAPIError
from pydantic import BaseModel, ValidationError

from persona_genesis.exceptions import ProviderError

_PROVIDER_NAME = "anthropic"
_DEFAULT_MAX_TOKENS = 2048


class AnthropicProvider:
    """LLMProvider implementation backed by the official Anthropic SDK."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        timeout_s: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._client = AsyncAnthropic(
            api_key=api_key,
            timeout=timeout_s,
            max_retries=max_retries,
        )

    async def acomplete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.7,
    ) -> str:
        try:
            msg = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except AnthropicAPIError as e:
            raise ProviderError(_PROVIDER_NAME, str(e)) from e

        return _extract_text(msg)

    async def acomplete_json(
        self,
        system: str,
        user: str,
        schema: type[BaseModel],
    ) -> BaseModel:
        schema_dict = schema.model_json_schema()
        instruction = (
            f"{system}\n\n"
            f"Respond with ONLY a JSON object matching this schema (no prose, "
            f"no code fences):\n{json.dumps(schema_dict)}"
        )
        raw = await self.acomplete(system=instruction, user=user, temperature=0.4)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ProviderError(
                _PROVIDER_NAME,
                f"model did not return valid JSON: {raw[:200]!r}",
            ) from e

        try:
            return schema.model_validate(data)
        except ValidationError as e:
            raise ProviderError(
                _PROVIDER_NAME,
                f"model JSON failed schema validation: {e}",
            ) from e


def _extract_text(message: object) -> str:
    """Pull the concatenated text from an Anthropic Message response."""
    parts: list[str] = []
    for block in getattr(message, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)
```

- [ ] **Step 12.4: Run tests + lint + mypy**

```bash
uv run pytest tests/unit/providers/llm/test_anthropic.py -v
uv run ruff check src/persona_genesis/providers/llm tests/unit/providers/llm
uv run mypy src/persona_genesis/providers/llm
```
Expected: 4 tests pass; lint + mypy clean.

- [ ] **Step 12.5: Commit**

```bash
git add src/persona_genesis/providers/llm/anthropic.py tests/unit/providers/llm/test_anthropic.py
git commit -m "feat(providers): add AnthropicProvider with text + JSON modes"
```

---

## Task 13: Generator base + structured Identity generator (TDD)

**Files:**
- Create: `src/persona_genesis/generators/__init__.py`
- Create: `src/persona_genesis/generators/base.py`
- Create: `src/persona_genesis/generators/structured/__init__.py`
- Create: `src/persona_genesis/generators/structured/identity.py`
- Create: `tests/unit/generators/__init__.py`
- Create: `tests/unit/generators/structured/__init__.py`
- Create: `tests/unit/generators/structured/test_identity.py`

- [ ] **Step 13.1: Create package markers**

```bash
touch src/persona_genesis/generators/__init__.py src/persona_genesis/generators/structured/__init__.py
touch tests/unit/generators/__init__.py tests/unit/generators/structured/__init__.py
```

- [ ] **Step 13.2: Write failing tests for Identity generator**

Create `tests/unit/generators/structured/test_identity.py`:
```python
"""Tests for the structured Identity generator."""

from datetime import date

from persona_genesis.generators.structured.identity import IdentityGenerator
from persona_genesis.schema.identity import Gender


def test_identity_generation_is_deterministic_for_same_seed() -> None:
    gen = IdentityGenerator(locale="en_US")
    a = gen.generate(seed=42)
    b = gen.generate(seed=42)
    assert a == b


def test_different_seeds_yield_different_identities() -> None:
    gen = IdentityGenerator(locale="en_US")
    a = gen.generate(seed=42)
    b = gen.generate(seed=43)
    assert a != b


def test_age_constraint_respected() -> None:
    gen = IdentityGenerator(locale="en_US")
    identity = gen.generate(seed=42, age_range=(30, 35))
    age = identity.age_on(date.today())
    assert 30 <= age <= 35


def test_gender_constraint_respected() -> None:
    gen = IdentityGenerator(locale="en_US")
    identity = gen.generate(seed=42, gender=Gender.FEMALE)
    assert identity.gender is Gender.FEMALE


def test_full_name_is_consistent_with_parts() -> None:
    gen = IdentityGenerator(locale="en_US")
    identity = gen.generate(seed=42)
    assert identity.given_name in identity.full_name
    assert identity.family_name in identity.full_name
```

- [ ] **Step 13.3: Implement Generator base**

Create `src/persona_genesis/generators/base.py`:
```python
"""Shared generator infrastructure: seeded RNG helper."""

from __future__ import annotations

import random


def seeded_rng(seed: int | None) -> random.Random:
    """Return a `random.Random` instance seeded with `seed` (or unseeded if None)."""
    return random.Random(seed)
```

- [ ] **Step 13.4: Implement IdentityGenerator**

Create `src/persona_genesis/generators/structured/identity.py`:
```python
"""Structured Identity generator backed by Faker."""

from __future__ import annotations

from datetime import date, timedelta

from faker import Faker

from persona_genesis.generators.base import seeded_rng
from persona_genesis.schema.identity import Gender, Identity

_LOCALE_TO_COUNTRY: dict[str, str] = {
    "en_US": "US",
    "en_GB": "GB",
    "pt_BR": "BR",
    "es_ES": "ES",
    "de_DE": "DE",
    "fr_FR": "FR",
    "ja_JP": "JP",
}


class IdentityGenerator:
    def __init__(self, *, locale: str = "en_US") -> None:
        self._locale = locale
        self._nationality = _LOCALE_TO_COUNTRY.get(locale, "US")

    def generate(
        self,
        *,
        seed: int | None = None,
        gender: Gender | None = None,
        age_range: tuple[int, int] = (18, 75),
    ) -> Identity:
        rng = seeded_rng(seed)
        faker = Faker(self._locale)
        faker.seed_instance(seed if seed is not None else rng.randint(0, 2**31 - 1))

        chosen_gender = gender or rng.choice(list(Gender))

        if chosen_gender is Gender.MALE:
            given = faker.first_name_male()
            family = faker.last_name()
        elif chosen_gender is Gender.FEMALE:
            given = faker.first_name_female()
            family = faker.last_name()
        else:
            given = faker.first_name()
            family = faker.last_name()

        min_age, max_age = age_range
        age = rng.randint(min_age, max_age)
        today = date.today()
        dob = today.replace(year=today.year - age) - timedelta(days=rng.randint(0, 364))

        return Identity(
            full_name=f"{given} {family}",
            given_name=given,
            family_name=family,
            gender=chosen_gender,
            date_of_birth=dob,
            nationality=self._nationality,
        )
```

- [ ] **Step 13.5: Run tests + lint + mypy**

```bash
uv run pytest tests/unit/generators -v
uv run ruff check src/persona_genesis/generators tests/unit/generators
uv run mypy src/persona_genesis/generators
```
Expected: 5 tests pass; lint + mypy clean.

- [ ] **Step 13.6: Commit**

```bash
git add src/persona_genesis/generators tests/unit/generators
git commit -m "feat(generators): add seeded RNG base + Identity structured generator"
```

---

## Task 14: Structured Location and Contact generators (TDD)

**Files:**
- Create: `src/persona_genesis/generators/structured/location.py`
- Create: `src/persona_genesis/generators/structured/contact.py`
- Create: `tests/unit/generators/structured/test_location.py`
- Create: `tests/unit/generators/structured/test_contact.py`

- [ ] **Step 14.1: Write failing tests for Location**

Create `tests/unit/generators/structured/test_location.py`:
```python
"""Tests for the structured Location generator."""

from persona_genesis.generators.structured.location import LocationGenerator


def test_location_generation_is_deterministic() -> None:
    gen = LocationGenerator(locale="pt_BR")
    a = gen.generate(seed=42)
    b = gen.generate(seed=42)
    assert a == b


def test_location_country_matches_locale() -> None:
    gen = LocationGenerator(locale="pt_BR")
    loc = gen.generate(seed=42)
    assert loc.country == "BR"


def test_location_timezone_is_valid_iana() -> None:
    from zoneinfo import available_timezones

    gen = LocationGenerator(locale="en_US")
    loc = gen.generate(seed=7)
    assert loc.timezone in available_timezones()
```

- [ ] **Step 14.2: Implement LocationGenerator**

Create `src/persona_genesis/generators/structured/location.py`:
```python
"""Structured Location generator backed by Faker, with locale-aware timezones."""

from __future__ import annotations

from faker import Faker

from persona_genesis.generators.base import seeded_rng
from persona_genesis.schema.location import Location

_LOCALE_TO_COUNTRY: dict[str, str] = {
    "en_US": "US",
    "en_GB": "GB",
    "pt_BR": "BR",
    "es_ES": "ES",
    "de_DE": "DE",
    "fr_FR": "FR",
    "ja_JP": "JP",
}

_DEFAULT_TIMEZONES_BY_COUNTRY: dict[str, list[str]] = {
    "US": ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"],
    "GB": ["Europe/London"],
    "BR": ["America/Sao_Paulo", "America/Recife", "America/Manaus"],
    "ES": ["Europe/Madrid"],
    "DE": ["Europe/Berlin"],
    "FR": ["Europe/Paris"],
    "JP": ["Asia/Tokyo"],
}


class LocationGenerator:
    def __init__(self, *, locale: str = "en_US") -> None:
        self._locale = locale
        self._country = _LOCALE_TO_COUNTRY.get(locale, "US")

    def generate(self, *, seed: int | None = None) -> Location:
        rng = seeded_rng(seed)
        faker = Faker(self._locale)
        faker.seed_instance(seed if seed is not None else rng.randint(0, 2**31 - 1))

        tz = rng.choice(_DEFAULT_TIMEZONES_BY_COUNTRY.get(self._country, ["UTC"]))

        return Location(
            country=self._country,
            region=faker.state() if hasattr(faker, "state") else faker.city(),
            city=faker.city(),
            street=faker.street_address(),
            postal_code=faker.postcode(),
            timezone=tz,
        )
```

- [ ] **Step 14.3: Write failing tests for Contact**

Create `tests/unit/generators/structured/test_contact.py`:
```python
"""Tests for the structured Contact generator."""

from persona_genesis.generators.structured.contact import ContactGenerator
from persona_genesis.schema.identity import Gender, Identity


def _identity() -> Identity:
    from datetime import date

    return Identity(
        full_name="Ana Souza",
        given_name="Ana",
        family_name="Souza",
        gender=Gender.FEMALE,
        date_of_birth=date(1992, 4, 15),
        nationality="BR",
    )


def test_email_handle_derived_from_identity() -> None:
    gen = ContactGenerator(locale="pt_BR")
    c = gen.generate(seed=42, identity=_identity())
    assert "ana" in c.email_handle.lower()
    assert "@" not in c.email_handle


def test_phone_country_code_matches_locale() -> None:
    gen = ContactGenerator(locale="pt_BR")
    c = gen.generate(seed=42, identity=_identity())
    assert c.phone_country_code == "+55"


def test_contact_generation_is_deterministic() -> None:
    gen = ContactGenerator(locale="pt_BR")
    a = gen.generate(seed=42, identity=_identity())
    b = gen.generate(seed=42, identity=_identity())
    assert a == b
```

- [ ] **Step 14.4: Implement ContactGenerator**

Create `src/persona_genesis/generators/structured/contact.py`:
```python
"""Structured Contact generator (email handle + phone format)."""

from __future__ import annotations

from persona_genesis.generators.base import seeded_rng
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.identity import Identity

_COUNTRY_TO_PHONE: dict[str, tuple[str, str]] = {
    # country code -> (phone_country_code, local_format)
    "US": ("+1", "(###) ###-####"),
    "GB": ("+44", "#### ######"),
    "BR": ("+55", "(##) #####-####"),
    "ES": ("+34", "### ### ###"),
    "DE": ("+49", "### #######"),
    "FR": ("+33", "# ## ## ## ##"),
    "JP": ("+81", "##-####-####"),
}

_EMAIL_STYLES: tuple[str, ...] = (
    "{given}.{family}",
    "{given}{family}",
    "{given}_{family}",
    "{given_initial}{family}",
    "{given}{family_initial}",
)


class ContactGenerator:
    def __init__(self, *, locale: str = "en_US") -> None:
        self._locale = locale

    def generate(self, *, seed: int | None = None, identity: Identity) -> Contact:
        rng = seeded_rng(seed)
        style = rng.choice(_EMAIL_STYLES)
        suffix = "" if rng.random() < 0.7 else str(rng.randint(1, 999))

        given = _slug(identity.given_name)
        family = _slug(identity.family_name)
        handle = (
            style.format(
                given=given,
                family=family,
                given_initial=given[:1],
                family_initial=family[:1],
            )
            + suffix
        ).lower()

        country = identity.nationality
        phone_cc, phone_local = _COUNTRY_TO_PHONE.get(country, ("+1", "(###) ###-####"))

        return Contact(
            email_handle=handle,
            phone_country_code=phone_cc,
            phone_local_format=phone_local,
        )


def _slug(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())
```

- [ ] **Step 14.5: Run + lint + mypy**

```bash
uv run pytest tests/unit/generators/structured -v
uv run ruff check src/persona_genesis/generators tests/unit/generators
uv run mypy src/persona_genesis/generators
```
Expected: all green.

- [ ] **Step 14.6: Commit**

```bash
git add src/persona_genesis/generators/structured/location.py src/persona_genesis/generators/structured/contact.py tests/unit/generators/structured/test_location.py tests/unit/generators/structured/test_contact.py
git commit -m "feat(generators): add Location and Contact structured generators"
```

---

## Task 15: Structured Work and Device generators (TDD)

**Files:**
- Create: `src/persona_genesis/generators/structured/work.py`
- Create: `src/persona_genesis/generators/structured/device.py`
- Create: `tests/unit/generators/structured/test_work.py`
- Create: `tests/unit/generators/structured/test_device.py`

- [ ] **Step 15.1: Write failing tests for Work**

Create `tests/unit/generators/structured/test_work.py`:
```python
"""Tests for the structured Work generator."""

from datetime import date

from persona_genesis.generators.structured.work import WorkGenerator
from persona_genesis.schema.identity import Gender, Identity
from persona_genesis.schema.work import Seniority


def _identity(age: int) -> Identity:
    today = date.today()
    return Identity(
        full_name="Test Person",
        given_name="Test",
        family_name="Person",
        gender=Gender.NON_BINARY,
        date_of_birth=today.replace(year=today.year - age),
        nationality="US",
    )


def test_seniority_consistent_with_age() -> None:
    gen = WorkGenerator(locale="en_US")
    work = gen.generate(seed=42, identity=_identity(22))
    assert work.seniority.minimum_years_experience <= max(22 - 18, 0)


def test_executive_only_for_old_enough_personas() -> None:
    gen = WorkGenerator(locale="en_US")
    # Repeated seeds — none should produce executive for a 22-year-old
    for seed in range(50):
        work = gen.generate(seed=seed, identity=_identity(22))
        assert work.seniority is not Seniority.EXECUTIVE


def test_work_generation_is_deterministic_for_seed() -> None:
    gen = WorkGenerator(locale="en_US")
    a = gen.generate(seed=42, identity=_identity(35))
    b = gen.generate(seed=42, identity=_identity(35))
    assert a == b
```

- [ ] **Step 15.2: Implement WorkGenerator**

Create `src/persona_genesis/generators/structured/work.py`:
```python
"""Structured Work generator — occupation, employer, age-aware seniority."""

from __future__ import annotations

import random
from datetime import date

from faker import Faker

from persona_genesis.generators.base import seeded_rng
from persona_genesis.schema.identity import Identity
from persona_genesis.schema.work import Seniority, Work

_INDUSTRIES: tuple[str, ...] = (
    "Technology", "Healthcare", "Education", "Finance", "Media",
    "Retail", "Manufacturing", "Hospitality", "Government", "Non-profit",
)


class WorkGenerator:
    def __init__(self, *, locale: str = "en_US") -> None:
        self._locale = locale

    def generate(self, *, seed: int | None = None, identity: Identity) -> Work:
        rng = seeded_rng(seed)
        faker = Faker(self._locale)
        faker.seed_instance(seed if seed is not None else rng.randint(0, 2**31 - 1))

        years_worked = max(identity.age_on(date.today()) - 18, 0)
        seniority = _pick_seniority(years_worked, rng)

        return Work(
            occupation=faker.job(),
            employer=faker.company(),
            seniority=seniority,
            industry=rng.choice(_INDUSTRIES),
            schedule=rng.choice(
                (
                    "Mon-Fri 09:00-17:00",
                    "Mon-Fri 10:00-18:00",
                    "Tue-Sat 11:00-19:00",
                    "Mon-Thu 08:00-18:00 (4-day week)",
                )
            ),
        )


def _pick_seniority(years_worked: int, rng: random.Random) -> Seniority:
    eligible = [s for s in Seniority if s.minimum_years_experience <= years_worked]
    return rng.choice(eligible)
```

- [ ] **Step 15.3: Write failing tests for Device**

Create `tests/unit/generators/structured/test_device.py`:
```python
"""Tests for the structured Device generator."""

from persona_genesis.generators.structured.device import DeviceGenerator
from persona_genesis.schema.device import BrowserFamily, DevicePlatform
from persona_genesis.ua_pool import UAPool


def test_device_generation_is_deterministic() -> None:
    gen = DeviceGenerator(ua_pool=UAPool.default())
    a = gen.generate(seed=42)
    b = gen.generate(seed=42)
    assert a == b


def test_user_agent_matches_chosen_platform_browser() -> None:
    gen = DeviceGenerator(ua_pool=UAPool.default())
    device = gen.generate(
        seed=42,
        platform=DevicePlatform.ANDROID,
        browser=BrowserFamily.CHROME,
    )
    assert device.platform is DevicePlatform.ANDROID
    assert device.browser is BrowserFamily.CHROME
    assert "Android" in device.user_agent
```

- [ ] **Step 15.4: Implement DeviceGenerator**

Create `src/persona_genesis/generators/structured/device.py`:
```python
"""Structured Device generator — picks a UA pool entry deterministically."""

from __future__ import annotations

from persona_genesis.generators.base import seeded_rng
from persona_genesis.schema.device import BrowserFamily, Device, DevicePlatform
from persona_genesis.ua_pool import UAPool

_DEFAULT_PLATFORM_BROWSER_PAIRS: tuple[tuple[DevicePlatform, BrowserFamily], ...] = (
    (DevicePlatform.ANDROID, BrowserFamily.CHROME),
    (DevicePlatform.IOS, BrowserFamily.SAFARI),
    (DevicePlatform.WINDOWS, BrowserFamily.CHROME),
    (DevicePlatform.WINDOWS, BrowserFamily.FIREFOX),
    (DevicePlatform.MACOS, BrowserFamily.SAFARI),
    (DevicePlatform.LINUX, BrowserFamily.FIREFOX),
)


class DeviceGenerator:
    def __init__(self, *, ua_pool: UAPool) -> None:
        self._ua_pool = ua_pool

    def generate(
        self,
        *,
        seed: int | None = None,
        platform: DevicePlatform | None = None,
        browser: BrowserFamily | None = None,
    ) -> Device:
        rng = seeded_rng(seed)

        if platform is None or browser is None:
            platform, browser = rng.choice(_DEFAULT_PLATFORM_BROWSER_PAIRS)

        entry = self._ua_pool.pick(platform=platform, browser=browser, rng=rng)
        return Device(
            platform=entry.platform,
            device_model=entry.device_model,
            os_version=entry.os_version,
            browser=entry.browser,
            browser_version=entry.browser_version,
            user_agent=entry.user_agent,
            screen_resolution=entry.screen_resolution,
        )
```

- [ ] **Step 15.5: Run + lint + mypy**

```bash
uv run pytest tests/unit -v
uv run ruff check src tests
uv run mypy src tests
```
Expected: all green.

- [ ] **Step 15.6: Commit**

```bash
git add src/persona_genesis/generators/structured/work.py src/persona_genesis/generators/structured/device.py tests/unit/generators/structured/test_work.py tests/unit/generators/structured/test_device.py
git commit -m "feat(generators): add Work and Device structured generators"
```

---

## Task 16: CI workflow (GitHub Actions)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 16.1: Create the CI workflow**

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
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Sync dependencies
        run: uv sync --all-extras --dev

      - name: Lint
        run: uv run ruff check src tests

      - name: Type check
        run: uv run mypy src tests

      - name: Test
        run: uv run pytest --cov=persona_genesis --cov-report=term-missing -q
```

- [ ] **Step 16.2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow (ruff, mypy, pytest matrix)"
```

---

## Task 17: Foundation milestone — tag, update CHANGELOG, push

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 17.1: Update CHANGELOG**

Replace the `## [Unreleased]` section in `CHANGELOG.md` with:
```markdown
## [Unreleased]

## [0.0.1] - 2026-06-01

### Added
- Project scaffolding (src layout, Python 3.12, hatchling, uv).
- Exception hierarchy (`PersonaGenesisError`, `ConfigError`, `ProviderError`,
  `PersonaGenerationError`, `CoherenceError`).
- Full `Persona` Pydantic schema with sub-models: `Identity`, `Location`,
  `Contact`, `Work`, `Appearance`, `Personality`, `Voice`, `Device`,
  `Backstory`, `PersonaImages`, `PersonaMetadata`.
- `Config` and `Config.from_env()` with pydantic-settings (`.env` support).
- Curated `UAPool` for deterministic device/browser User-Agent selection.
- `LLMProvider` protocol and `AnthropicProvider` adapter (text + JSON modes).
- Structured generators: `IdentityGenerator`, `LocationGenerator`,
  `ContactGenerator`, `WorkGenerator`, `DeviceGenerator`, all deterministic
  from a seed.
- GitHub Actions CI: ruff + mypy + pytest on Python 3.12 and 3.13.
```

- [ ] **Step 17.2: Run the full test suite one more time**

```bash
uv run pytest --cov=persona_genesis --cov-report=term-missing -v
uv run ruff check src tests
uv run mypy src tests
```
Expected: all green. Coverage should be high on schema, exceptions, config, ua_pool, and structured generators. The Anthropic provider tests mock HTTP via respx, so it should also have meaningful coverage.

- [ ] **Step 17.3: Commit and tag**

```bash
git add CHANGELOG.md
git commit -m "chore: release 0.0.1 (foundation milestone)"
git tag -a v0.0.1 -m "v0.0.1 — foundation milestone: schema, config, providers, structured generators"
```

- [ ] **Step 17.4: (Optional) Push to GitHub when remote is configured**

```bash
# Once the GitHub remote is set up:
# git remote add origin git@github.com:tarsow/persona-genesis.git
# git branch -M main
# git push -u origin main --tags
```

---

## Summary of what this plan delivers

After Task 17, the persona-genesis library has:

- A clean src/ layout, full tooling (ruff, mypy, pytest, CI).
- The complete `Persona` Pydantic contract — every sub-model defined, validated, and round-trip-tested.
- Working configuration via `.env` or constructor.
- A curated UA pool with deterministic selection.
- The `LLMProvider` protocol and a working `AnthropicProvider`.
- Deterministic structured generators for identity, location, contact, work, and device — each independently usable.

What is NOT in this plan (deferred to Plan 2 → v0.1.0):

- Narrative generators (personality, appearance text, backstory, voice).
- Coherence validators.
- The `PersonaGenerator` orchestrator that ties everything together.
- `RecordedProvider` test helper for LLM replay.
- CLI.
- Full README and examples.

What is NOT in this plan (deferred to Plan 3 → v0.2.0):

- `ImageProvider` protocol and fal/replicate/openai-image adapters.
- Face, body, and custom-image generators.
