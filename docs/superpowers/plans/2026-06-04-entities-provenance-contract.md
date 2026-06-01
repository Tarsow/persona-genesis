# Decoupled Entities, Provenance & Builder — Contract Layer (Plan 1 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the DB-free contract layer of `specs/2026-06-04-persona-genesis-entities-embeddings-rag-provenance-design.md`: the `Status` provenance type with `_status` siblings across every synthetic section, realism-honest `Contact`/`Location`, standalone `Image`/`Audio`/`Video` + biometric `Face`/`Body`/`VoicePrint` + `Document` + `Relationship` models, a slimmed `Persona`/`PartialPersona`, on-disk media storage, the `extraction.py` seam, `PersonaBuilder` → `PersonaDraft`, and `Config` embedding-dim fields.

**Architecture:** Pure Pydantic v2 models (the DB-free public contract) plus a synchronous `PersonaBuilder` that writes attached binaries to disk via a content-hash and accumulates a `PersonaDraft` bundle. No SQLAlchemy/Postgres here — persistence is Plan 2. TDD throughout (test → red → implement → green → commit).

**Tech Stack:** Python 3.12 · Pydantic 2.6+ · Pillow · hashlib · pytest. (No new dependencies — DB/crypto/pgvector deps land in Plan 2.)

---

## Conventions (read first)

- Schema models are **plain** `pydantic.BaseModel` with terse field comments (no `frozen`, no `extra="forbid"`). Match the existing style.
- Existing field names are fixed: `Identity.dob`, `Gender = Literal["male","female","non_binary"]`, `OceanScores`, `Work.schedule: Schedule`, `Device.primary_device/os/browser`, `Appearance.hair_color/hair_style/eye_color/build/height_cm/distinguishing_features`, `Voice.writing_style/posting_cadence/typical_topics/sample_paragraph`, `Backstory.bio/education/key_life_events`. Do not rename.
- Tests are flat under `tests/unit/` as `test_<name>.py`.
- Commit messages end with the body (no `Co-Authored-By` trailer).
- The biometric voice model is named `Voice` inside `schema/biometrics.py` but **re-exported as `VoicePrint`** everywhere public, to avoid clashing with the text-section `schema.voice.Voice`. To keep this unambiguous, define the class **as `VoicePrint` directly** in `biometrics.py` (simplest — no aliasing).

## File Structure

**Created — source:**
```
src/persona_genesis/
├── schema/
│   ├── status.py        # Status = Literal["real","gen","fake"]
│   ├── media.py         # MediaOrigin, Image, Audio, Video
│   ├── biometrics.py    # Face, Body, VoicePrint
│   ├── document.py      # Document
│   ├── relationship.py  # RelationshipType, Relationship
│   ├── account.py       # Account (vault entry)
│   ├── partial.py       # PartialPersona
│   └── draft.py         # PersonaDraft
├── media/
│   ├── __init__.py
│   └── storage.py       # content-hashed on-disk writer
├── extraction.py        # AI extraction seam (signatures; impls deferred)
└── builder.py           # PersonaBuilder -> PersonaDraft
```

**Modified — source:**
```
schema/identity.py, location.py, contact.py, work.py, appearance.py,
personality.py, voice.py, device.py, backstory.py   # add <field>_status siblings
schema/persona.py            # drop images; sections + metadata only
schema/__init__.py           # re-exports
config.py                    # dims + database_url/vault_key/media_dir
__init__.py                  # public re-exports
```

**Deleted:** `schema/images.py`, `tests/unit/test_schema_images.py`.

**Created — tests:** `test_status.py`, `test_schema_media.py`, `test_schema_biometrics.py`, `test_schema_document.py`, `test_schema_relationship.py`, `test_schema_account.py`, `test_schema_partial.py`, `test_schema_draft.py`, `test_media_storage.py`, `test_extraction.py`, `test_builder.py`. Modified: `test_schema_contact.py`, `test_schema_location.py`, `test_schema_identity.py`(if present)/new status tests, `test_schema_persona.py`, `test_config.py`, `test_public_api.py`, `conftest.py`.

---

## Task 1: `Status` provenance type

**Files:**
- Create: `src/persona_genesis/schema/status.py`
- Create: `tests/unit/test_status.py`

- [ ] **Step 1.1: Write the failing test**

Create `tests/unit/test_status.py`:
```python
from typing import get_args

from persona_genesis.schema.status import Status


def test_status_has_three_values() -> None:
    assert set(get_args(Status)) == {"real", "gen", "fake"}
```

- [ ] **Step 1.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_status.py -q`
Expected: ImportError on `persona_genesis.schema.status`.

- [ ] **Step 1.3: Implement**

Create `src/persona_genesis/schema/status.py`:
```python
"""Field-level realism provenance.

- ``real`` — value supplied by the caller.
- ``gen``  — generated but basically real (derived from real data, LLM narrative,
  or an AI embedding/description).
- ``fake`` — randomly generated, only looks real (Faker-invented, sampled).
"""

from typing import Literal

Status = Literal["real", "gen", "fake"]
```

- [ ] **Step 1.4: Run to verify pass**

Run: `uv run pytest tests/unit/test_status.py -q && uv run mypy src/persona_genesis/schema/status.py`
Expected: 1 passed; mypy clean.

- [ ] **Step 1.5: Commit**

```bash
git add src/persona_genesis/schema/status.py tests/unit/test_status.py
git commit -m "feat(schema): add Status provenance type (real/gen/fake)"
```

---

## Task 2: Realism Contact/Location + `_status` siblings

**Files:**
- Modify: `src/persona_genesis/schema/contact.py`
- Modify: `src/persona_genesis/schema/location.py`
- Modify: `tests/unit/test_schema_contact.py`
- Modify: `tests/unit/test_schema_location.py`

- [ ] **Step 2.1: Rewrite Contact tests (failing)**

Replace `tests/unit/test_schema_contact.py`:
```python
from persona_genesis.schema.contact import Contact


def test_contact_defaults_to_empty_with_fake_status() -> None:
    c = Contact()
    assert c.phone is None
    assert c.email is None
    assert c.phone_status == "fake"
    assert c.email_status == "fake"


def test_contact_round_trips() -> None:
    c = Contact(phone="+55 19 90000-0000", email="me@x.com", phone_status="real", email_status="real")
    restored = Contact.model_validate_json(c.model_dump_json())
    assert restored == c


def test_contact_has_no_email_handle() -> None:
    assert "email_handle" not in Contact.model_fields
```

- [ ] **Step 2.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_schema_contact.py -q`
Expected: fails (current Contact requires phone/email_handle).

- [ ] **Step 2.3: Implement Contact**

Replace `src/persona_genesis/schema/contact.py`:
```python
"""Contact sub-model. Real-only: populated only from caller-supplied, owned data."""

from persona_genesis.schema.status import Status


from pydantic import BaseModel


class Contact(BaseModel):
    phone: str | None = None  # real-only
    phone_status: Status = "fake"
    email: str | None = None  # real-only
    email_status: Status = "fake"
```

- [ ] **Step 2.4: Rewrite Location tests (failing)**

Replace `tests/unit/test_schema_location.py`:
```python
from persona_genesis.schema.location import Location


def test_location_precise_address_optional_with_gen_status() -> None:
    loc = Location(country="BR", region="SP", city="Campinas", timezone="America/Sao_Paulo")
    assert loc.street is None
    assert loc.postal_code is None
    assert loc.country_status == "gen"
    assert loc.street_status == "gen"


def test_location_round_trips() -> None:
    loc = Location(
        country="BR", region="SP", city="Campinas",
        street="Rua das Flores, 123", postal_code="13010-000",
        timezone="America/Sao_Paulo",
    )
    restored = Location.model_validate_json(loc.model_dump_json())
    assert restored == loc
```

- [ ] **Step 2.5: Implement Location**

Replace `src/persona_genesis/schema/location.py`:
```python
"""Location sub-model. Coarse fields auto-generated; precise address (real, from IP) optional."""

from pydantic import BaseModel

from persona_genesis.schema.status import Status


class Location(BaseModel):
    country: str
    country_status: Status = "gen"
    region: str
    region_status: Status = "gen"
    city: str
    city_status: Status = "gen"
    timezone: str
    timezone_status: Status = "gen"
    street: str | None = None
    street_status: Status = "gen"
    postal_code: str | None = None
    postal_code_status: Status = "gen"
```

- [ ] **Step 2.6: Run + lint**

Run:
```bash
uv run pytest tests/unit/test_schema_contact.py tests/unit/test_schema_location.py -q
uv run ruff check src/persona_genesis/schema
```
Expected: green. (Note: `conftest.py` still uses `email_handle` and will break other tests — fixed in Task 9. Run only these two files for now.)

- [ ] **Step 2.7: Commit**

```bash
git add src/persona_genesis/schema/contact.py src/persona_genesis/schema/location.py tests/unit/test_schema_contact.py tests/unit/test_schema_location.py
git commit -m "feat(schema): real-only Contact/Location with _status siblings"
```

---

## Task 3: `_status` on Identity, Work, Device

**Files:**
- Modify: `src/persona_genesis/schema/identity.py`, `work.py`, `device.py`
- Create: `tests/unit/test_schema_status_fields.py`

- [ ] **Step 3.1: Write the failing test**

Create `tests/unit/test_schema_status_fields.py`:
```python
from datetime import date

from persona_genesis.schema.device import Device
from persona_genesis.schema.identity import Identity
from persona_genesis.schema.work import Work


def test_identity_status_defaults_fake() -> None:
    i = Identity(full_name="A B", given_name="A", family_name="B", gender="female",
                 dob=date(1994, 3, 12), nationality="BR")
    assert i.full_name_status == "fake"
    assert i.dob_status == "fake"
    assert i.nationality_status == "fake"


def test_work_status_defaults_fake() -> None:
    w = Work(occupation="Engineer", employer="X", seniority="senior", industry="Tech",
             schedule="full_time")
    assert w.occupation_status == "fake"
    assert w.seniority_status == "fake"


def test_device_status_defaults_fake() -> None:
    d = Device(primary_device="smartphone", os="android", browser="chrome",
               user_agent="UA", screen_resolution="1080x2400")
    assert d.user_agent_status == "fake"
    assert d.os_status == "fake"
```

- [ ] **Step 3.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_schema_status_fields.py -q`
Expected: AttributeError (no status fields yet).

- [ ] **Step 3.3: Implement Identity**

Replace `src/persona_genesis/schema/identity.py`:
```python
"""Identity sub-model."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from persona_genesis.schema.status import Status

Gender = Literal["male", "female", "non_binary"]


class Identity(BaseModel):
    full_name: str
    full_name_status: Status = "fake"
    given_name: str
    given_name_status: Status = "fake"
    family_name: str
    family_name_status: Status = "fake"
    gender: Gender
    gender_status: Status = "fake"
    dob: date
    dob_status: Status = "fake"
    nationality: str  # ISO 3166-1 alpha-2
    nationality_status: Status = "fake"
```

- [ ] **Step 3.4: Implement Work**

Replace the `Work` class body in `src/persona_genesis/schema/work.py` (keep the `Seniority`/`Schedule` Literals and add the import):
```python
"""Work sub-model."""

from typing import Literal

from pydantic import BaseModel

from persona_genesis.schema.status import Status

Seniority = Literal[
    "intern", "junior", "mid", "senior", "lead", "manager", "director", "executive",
]
Schedule = Literal["full_time", "part_time", "contract", "freelance", "shift", "remote"]


class Work(BaseModel):
    occupation: str
    occupation_status: Status = "fake"
    employer: str
    employer_status: Status = "fake"
    seniority: Seniority
    seniority_status: Status = "fake"
    industry: str
    industry_status: Status = "fake"
    schedule: Schedule
    schedule_status: Status = "fake"
```

- [ ] **Step 3.5: Implement Device**

Replace the `Device` class in `src/persona_genesis/schema/device.py` (keep the Literals, add import):
```python
"""Device sub-model: hardware, OS, browser and the matching user agent."""

from typing import Literal

from pydantic import BaseModel

from persona_genesis.schema.status import Status

DeviceType = Literal["desktop", "laptop", "smartphone", "tablet"]
OS = Literal["windows", "macos", "linux", "android", "ios"]
Browser = Literal["chrome", "firefox", "safari", "edge"]


class Device(BaseModel):
    primary_device: DeviceType
    primary_device_status: Status = "fake"
    os: OS
    os_status: Status = "fake"
    browser: Browser
    browser_status: Status = "fake"
    user_agent: str
    user_agent_status: Status = "fake"
    screen_resolution: str  # "<width>x<height>"
    screen_resolution_status: Status = "fake"
```

- [ ] **Step 3.6: Run to verify pass**

Run: `uv run pytest tests/unit/test_schema_status_fields.py -q && uv run mypy src/persona_genesis/schema/identity.py src/persona_genesis/schema/work.py src/persona_genesis/schema/device.py`
Expected: 3 passed; mypy clean.

- [ ] **Step 3.7: Commit**

```bash
git add src/persona_genesis/schema/identity.py src/persona_genesis/schema/work.py src/persona_genesis/schema/device.py tests/unit/test_schema_status_fields.py
git commit -m "feat(schema): add _status siblings to Identity, Work, Device"
```

---

## Task 4: `_status` on Appearance, Personality, Voice, Backstory

**Files:**
- Modify: `src/persona_genesis/schema/appearance.py`, `personality.py`, `voice.py`, `backstory.py`
- Modify: `tests/unit/test_schema_status_fields.py`

- [ ] **Step 4.1: Append failing tests**

Append to `tests/unit/test_schema_status_fields.py`:
```python
def test_appearance_status_mix() -> None:
    from persona_genesis.schema.appearance import Appearance

    a = Appearance(description="d", hair_color="brown", hair_style="short",
                   eye_color="brown", build="average", height_cm=170)
    assert a.description_status == "gen"
    assert a.hair_color_status == "fake"
    assert a.distinguishing_features_status == "fake"


def test_personality_voice_backstory_status_gen() -> None:
    from persona_genesis.schema.backstory import Backstory
    from persona_genesis.schema.personality import OceanScores, Personality
    from persona_genesis.schema.voice import Voice

    p = Personality(ocean=OceanScores(openness=0.5, conscientiousness=0.5,
                    extraversion=0.5, agreeableness=0.5, neuroticism=0.5))
    assert p.ocean_status == "gen"
    assert p.traits_status == "gen"

    v = Voice(writing_style="x", posting_cadence="daily", sample_paragraph="y")
    assert v.writing_style_status == "gen"
    assert v.typical_topics_status == "gen"

    b = Backstory(bio="x")
    assert b.bio_status == "gen"
    assert b.education_status == "gen"
```

- [ ] **Step 4.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_schema_status_fields.py -q`
Expected: new tests fail (AttributeError).

- [ ] **Step 4.3: Implement Appearance**

Replace `src/persona_genesis/schema/appearance.py`:
```python
"""Appearance sub-model: narrative description plus structured attributes."""

from typing import Literal

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status

Build = Literal["slim", "average", "athletic", "muscular", "heavy"]


class Appearance(BaseModel):
    description: str
    description_status: Status = "gen"
    hair_color: str
    hair_color_status: Status = "fake"
    hair_style: str
    hair_style_status: Status = "fake"
    eye_color: str
    eye_color_status: Status = "fake"
    build: Build
    build_status: Status = "fake"
    height_cm: int = Field(gt=0, le=260)
    height_cm_status: Status = "fake"
    distinguishing_features: list[str] = Field(default_factory=list)
    distinguishing_features_status: Status = "fake"
```

- [ ] **Step 4.4: Implement Personality**

Replace the `Personality` class in `src/persona_genesis/schema/personality.py` (keep `OceanScores`, add import):
```python
"""Personality sub-model: OCEAN scores plus descriptive traits."""

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status


class OceanScores(BaseModel):
    """Big Five scores, each normalized to [0, 1]."""

    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)


class Personality(BaseModel):
    ocean: OceanScores
    ocean_status: Status = "gen"
    traits: list[str] = Field(default_factory=list)
    traits_status: Status = "gen"
    values: list[str] = Field(default_factory=list)
    values_status: Status = "gen"
    quirks: list[str] = Field(default_factory=list)
    quirks_status: Status = "gen"
```

- [ ] **Step 4.5: Implement Voice**

Replace `src/persona_genesis/schema/voice.py`:
```python
"""Voice sub-model: how the persona writes and posts online."""

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status


class Voice(BaseModel):
    writing_style: str
    writing_style_status: Status = "gen"
    posting_cadence: str
    posting_cadence_status: Status = "gen"
    typical_topics: list[str] = Field(default_factory=list)
    typical_topics_status: Status = "gen"
    sample_paragraph: str
    sample_paragraph_status: Status = "gen"
```

- [ ] **Step 4.6: Implement Backstory**

Replace the `Backstory` class in `src/persona_genesis/schema/backstory.py` (keep `Education`/`LifeEvent`, add import):
```python
"""Backstory sub-model: bio, education history and key life events."""

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status


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
    bio_status: Status = "gen"
    education: list[Education] = Field(default_factory=list)
    education_status: Status = "gen"
    key_life_events: list[LifeEvent] = Field(default_factory=list)
    key_life_events_status: Status = "gen"
```

- [ ] **Step 4.7: Run + lint + mypy**

Run:
```bash
uv run pytest tests/unit/test_schema_status_fields.py -q
uv run ruff check src/persona_genesis/schema
uv run mypy src/persona_genesis/schema/appearance.py src/persona_genesis/schema/personality.py src/persona_genesis/schema/voice.py src/persona_genesis/schema/backstory.py
```
Expected: all green.

- [ ] **Step 4.8: Commit**

```bash
git add src/persona_genesis/schema/appearance.py src/persona_genesis/schema/personality.py src/persona_genesis/schema/voice.py src/persona_genesis/schema/backstory.py tests/unit/test_schema_status_fields.py
git commit -m "feat(schema): add _status siblings to Appearance, Personality, Voice, Backstory"
```

---

## Task 5: On-disk media storage

**Files:**
- Create: `src/persona_genesis/media/__init__.py`, `src/persona_genesis/media/storage.py`
- Create: `tests/unit/test_media_storage.py`

- [ ] **Step 5.1: Write the failing tests**

Create `tests/unit/test_media_storage.py`:
```python
from pathlib import Path

from persona_genesis.media.storage import extension_for, store_media


def test_extension_for() -> None:
    assert extension_for("image/png") == ".png"
    assert extension_for("audio/wav") == ".wav"
    assert extension_for("video/mp4") == ".mp4"
    assert extension_for("application/x-weird") == ".bin"


def test_store_media_hashed_and_deduped(tmp_path: Path) -> None:
    a = store_media(b"hello", kind="image", media_type="image/png", media_dir=tmp_path)
    b = store_media(b"hello", kind="image", media_type="image/png", media_dir=tmp_path)
    assert a == b
    assert a.startswith("image/") and a.endswith(".png")
    assert (tmp_path / a).read_bytes() == b"hello"


def test_store_media_per_kind_subdir(tmp_path: Path) -> None:
    vid = store_media(b"x", kind="video", media_type="video/mp4", media_dir=tmp_path)
    assert vid.split("/")[0] == "video"
    assert (tmp_path / "video").is_dir()
```

- [ ] **Step 5.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_media_storage.py -q`
Expected: ImportError.

- [ ] **Step 5.3: Implement**

Create `src/persona_genesis/media/__init__.py`:
```python
"""On-disk media storage (binaries live on disk, never in the DB or JSON)."""
```

Create `src/persona_genesis/media/storage.py`:
```python
"""Content-hashed media writer: media_dir/<kind>/<sha256-hex><ext>."""

import hashlib
from pathlib import Path

_EXTENSIONS: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}
_FALLBACK_EXT = ".bin"


def extension_for(media_type: str) -> str:
    return _EXTENSIONS.get(media_type.lower().strip(), _FALLBACK_EXT)


def store_media(data: bytes, *, kind: str, media_type: str, media_dir: str | Path) -> str:
    digest = hashlib.sha256(data).hexdigest()
    rel = f"{kind}/{digest}{extension_for(media_type)}"
    dest = Path(media_dir) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return rel
```

- [ ] **Step 5.4: Run + mypy**

Run: `uv run pytest tests/unit/test_media_storage.py -q && uv run mypy src/persona_genesis/media`
Expected: 3 passed; mypy clean.

- [ ] **Step 5.5: Commit**

```bash
git add src/persona_genesis/media tests/unit/test_media_storage.py
git commit -m "feat(media): add content-hashed on-disk media storage"
```

---

## Task 6: Standalone media models (Image/Audio/Video) + remove PersonaImages

**Files:**
- Create: `src/persona_genesis/schema/media.py`
- Create: `tests/unit/test_schema_media.py`
- Delete: `src/persona_genesis/schema/images.py`, `tests/unit/test_schema_images.py`

- [ ] **Step 6.1: Write the failing tests**

Create `tests/unit/test_schema_media.py`:
```python
import json

import pytest
from pydantic import ValidationError

from persona_genesis.schema.media import Audio, Image, MediaOrigin, Video


def test_ai_origin_requires_provider_and_model() -> None:
    with pytest.raises(ValidationError):
        MediaOrigin(source="ai_generated", provider="fal")
    MediaOrigin(source="ai_generated", provider="fal", model="flux")
    MediaOrigin(source="caller_supplied")


def test_image_defaults_and_unknown_type() -> None:
    img = Image(file_path="image/h.png", media_type="image/png", type="unknown")
    assert img.nsfw == 0.0
    assert img.status == "gen"
    assert img.description is None


def test_nsfw_bounds() -> None:
    with pytest.raises(ValidationError):
        Image(file_path="x", media_type="image/png", type="face", nsfw=1.5)


def test_audio_video_round_trip_no_binary() -> None:
    a = Audio(file_path="audio/h.wav", media_type="audio/wav", type="voice_sample", text="hi")
    v = Video(file_path="video/h.mp4", media_type="video/mp4", type="unknown", fps=30.0)
    assert json.loads(a.model_dump_json())["text"] == "hi"
    assert Audio.model_validate_json(a.model_dump_json()) == a
    assert Video.model_validate_json(v.model_dump_json()) == v
```

- [ ] **Step 6.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_schema_media.py -q`
Expected: ImportError.

- [ ] **Step 6.3: Implement**

Create `src/persona_genesis/schema/media.py`:
```python
"""Standalone typed media with provenance. Binaries live on disk (file_path)."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from persona_genesis.schema.status import Status

ImageType = Literal["face", "full_body", "other", "unknown"]
AudioType = Literal["conversational", "voice_sample", "music", "other", "unknown"]
VideoType = Literal["clip", "avatar", "other", "unknown"]


class MediaOrigin(BaseModel):
    source: Literal["ai_generated", "caller_supplied"]
    provider: str | None = None
    model: str | None = None
    prompt: str | None = None
    generated_at: datetime | None = None

    @model_validator(mode="after")
    def _ai_requires_provenance(self) -> "MediaOrigin":
        if self.source == "ai_generated" and not (self.provider and self.model):
            raise ValueError("ai_generated media must record provider and model")
        return self


class Image(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_path: str
    media_type: str
    type: ImageType
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)
    width: int | None = None
    height: int | None = None
    description: str | None = None
    origin: MediaOrigin | None = None
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class Audio(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_path: str
    media_type: str
    type: AudioType
    text: str | None = None
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)
    sample_rate_hz: int | None = None
    duration_s: float | None = None
    origin: MediaOrigin | None = None
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class Video(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_path: str
    media_type: str
    type: VideoType
    text: str | None = None
    nsfw: float = Field(default=0.0, ge=0.0, le=1.0)
    width: int | None = None
    height: int | None = None
    duration_s: float | None = None
    fps: float | None = None
    description: str | None = None
    origin: MediaOrigin | None = None
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
```

Add the missing UUID import at the top: `from uuid import UUID, uuid4`.

- [ ] **Step 6.4: Delete the obsolete images module**

Run: `git rm src/persona_genesis/schema/images.py tests/unit/test_schema_images.py`

- [ ] **Step 6.5: Run + mypy**

Run: `uv run pytest tests/unit/test_schema_media.py -q && uv run mypy src/persona_genesis/schema/media.py`
Expected: 4 passed; mypy clean.

- [ ] **Step 6.6: Commit**

```bash
git add src/persona_genesis/schema/media.py tests/unit/test_schema_media.py
git rm --cached src/persona_genesis/schema/images.py tests/unit/test_schema_images.py 2>/dev/null; true
git commit -m "feat(schema): standalone Image/Audio/Video media models; remove PersonaImages"
```

---

## Task 7: Biometric embedding models (Face/Body/VoicePrint)

**Files:**
- Create: `src/persona_genesis/schema/biometrics.py`
- Create: `tests/unit/test_schema_biometrics.py`

- [ ] **Step 7.1: Write the failing tests**

Create `tests/unit/test_schema_biometrics.py`:
```python
from uuid import uuid4

from persona_genesis.schema.biometrics import Body, Face, VoicePrint


def test_face_optional_persona_and_round_trip() -> None:
    f = Face(embedding=[0.1, 0.2, 0.3])
    assert f.persona_id is None
    assert f.status == "gen"
    assert Face.model_validate_json(f.model_dump_json()) == f


def test_body_and_voiceprint_require_persona() -> None:
    pid = uuid4()
    b = Body(persona_id=pid, embedding=[0.0, 1.0])
    vp = VoicePrint(persona_id=pid, embedding=[0.5], label="calm")
    assert b.persona_id == pid
    assert vp.label == "calm"
    assert VoicePrint.model_validate_json(vp.model_dump_json()) == vp
```

- [ ] **Step 7.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_schema_biometrics.py -q`
Expected: ImportError.

- [ ] **Step 7.3: Implement**

Create `src/persona_genesis/schema/biometrics.py`:
```python
"""Biometric embedding models. Embeddings are list[float] in the contract;
the DB layer maps them to pgvector vector(N)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status


class Face(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID | None = None  # 0..1 persona
    embedding: list[float]
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class Body(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID
    embedding: list[float]
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class VoicePrint(BaseModel):
    """Biometric speaker embedding (named VoicePrint to avoid clashing with the
    text-section schema.voice.Voice)."""

    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID
    embedding: list[float]
    label: str | None = None  # optional tone descriptor
    status: Status = "gen"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
```

- [ ] **Step 7.4: Run + mypy**

Run: `uv run pytest tests/unit/test_schema_biometrics.py -q && uv run mypy src/persona_genesis/schema/biometrics.py`
Expected: 2 passed; mypy clean.

- [ ] **Step 7.5: Commit**

```bash
git add src/persona_genesis/schema/biometrics.py tests/unit/test_schema_biometrics.py
git commit -m "feat(schema): add Face, Body, VoicePrint embedding models"
```

---

## Task 8: Document, Relationship, Account models

**Files:**
- Create: `src/persona_genesis/schema/document.py`, `relationship.py`, `account.py`
- Create: `tests/unit/test_schema_document.py`, `test_schema_relationship.py`, `test_schema_account.py`

- [ ] **Step 8.1: Write the failing tests**

Create `tests/unit/test_schema_document.py`:
```python
from persona_genesis.schema.document import Document


def test_document_defaults() -> None:
    d = Document(content="An event happened.")
    assert d.metadata == {}
    assert d.embedding is None
    assert d.status == "real"
    assert Document.model_validate_json(d.model_dump_json()) == d
```

Create `tests/unit/test_schema_relationship.py`:
```python
from uuid import uuid4

import pytest
from pydantic import ValidationError

from persona_genesis.schema.relationship import Relationship


def test_relationship_round_trip() -> None:
    r = Relationship(person_1_id=uuid4(), person_2_id=uuid4(), relationship="friend")
    assert r.status == "gen"
    assert Relationship.model_validate_json(r.model_dump_json()) == r


def test_relationship_type_validated() -> None:
    with pytest.raises(ValidationError):
        Relationship(person_1_id=uuid4(), person_2_id=uuid4(), relationship="enemies")
```

Create `tests/unit/test_schema_account.py`:
```python
from uuid import uuid4

from persona_genesis.schema.account import Account


def test_account_round_trip_plaintext_in_memory() -> None:
    a = Account(persona_id=uuid4(), url="https://x", login="u", password="p")
    assert a.password == "p"
    assert a.session_token is None
    assert Account.model_validate_json(a.model_dump_json()) == a
```

- [ ] **Step 8.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_schema_document.py tests/unit/test_schema_relationship.py tests/unit/test_schema_account.py -q`
Expected: ImportError on all three.

- [ ] **Step 8.3: Implement Document**

Create `src/persona_genesis/schema/document.py`:
```python
"""RAG document: content + metadata + embedding. Linked M:N to personas in the DB."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status


class Document(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None
    status: Status = "real"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
```

- [ ] **Step 8.4: Implement Relationship**

Create `src/persona_genesis/schema/relationship.py`:
```python
"""Directional persona<->persona relationship."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status

RelationshipType = Literal[
    "friend", "family", "partner", "coworker", "acquaintance", "other", "unknown"
]


class Relationship(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    person_1_id: UUID  # subject
    person_2_id: UUID  # object
    relationship: RelationshipType
    status: Status = "gen"
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
```

- [ ] **Step 8.5: Implement Account**

Create `src/persona_genesis/schema/account.py`:
```python
"""Account vault entry. Secrets plaintext in-memory; encrypted at the DB boundary."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Account(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    persona_id: UUID
    url: str
    login: str
    password: str
    session_token: str | None = None
    notes: str | None = None
    date_created: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    date_updated: datetime | None = None
```

- [ ] **Step 8.6: Run + mypy**

Run:
```bash
uv run pytest tests/unit/test_schema_document.py tests/unit/test_schema_relationship.py tests/unit/test_schema_account.py -q
uv run mypy src/persona_genesis/schema/document.py src/persona_genesis/schema/relationship.py src/persona_genesis/schema/account.py
```
Expected: green.

- [ ] **Step 8.7: Commit**

```bash
git add src/persona_genesis/schema/document.py src/persona_genesis/schema/relationship.py src/persona_genesis/schema/account.py tests/unit/test_schema_document.py tests/unit/test_schema_relationship.py tests/unit/test_schema_account.py
git commit -m "feat(schema): add Document (RAG), Relationship, and Account models"
```

---

## Task 9: Slim Persona + PartialPersona; fix conftest

**Files:**
- Modify: `src/persona_genesis/schema/persona.py`
- Create: `src/persona_genesis/schema/partial.py`
- Modify: `tests/conftest.py`
- Modify: `tests/unit/test_schema_persona.py`
- Create: `tests/unit/test_schema_partial.py`

- [ ] **Step 9.1: Rewrite Persona (drop images/media)**

Replace `src/persona_genesis/schema/persona.py`:
```python
"""Top-level Persona model — synthetic sections only (media/biometrics are separate)."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from persona_genesis.schema.appearance import Appearance
from persona_genesis.schema.backstory import Backstory
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.device import Device
from persona_genesis.schema.identity import Identity
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
    metadata: PersonaMetadata
```

- [ ] **Step 9.2: Implement PartialPersona**

Create `src/persona_genesis/schema/partial.py`:
```python
"""PartialPersona — all-optional, in-progress mirror of Persona (sections only)."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from persona_genesis.schema.appearance import Appearance
from persona_genesis.schema.backstory import Backstory
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.device import Device
from persona_genesis.schema.identity import Identity
from persona_genesis.schema.location import Location
from persona_genesis.schema.metadata import PersonaMetadata
from persona_genesis.schema.personality import Personality
from persona_genesis.schema.voice import Voice
from persona_genesis.schema.work import Work


class PartialPersona(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    seed: int | None = None
    locale: str | None = None
    identity: Identity | None = None
    location: Location | None = None
    contact: Contact | None = None
    work: Work | None = None
    appearance: Appearance | None = None
    personality: Personality | None = None
    voice: Voice | None = None
    device: Device | None = None
    backstory: Backstory | None = None
    metadata: PersonaMetadata | None = None
```

- [ ] **Step 9.3: Fix conftest (email_handle → email; no images)**

In `tests/conftest.py`, change the `contact=` line from:
```python
        contact=Contact(phone="+55 19 90000-0000", email_handle="ana.souza"),
```
to:
```python
        contact=Contact(phone="+55 19 90000-0000", email="ana.souza@example.com"),
```
(The `Persona(...)` construction has no `images=`/`media=` arg, so nothing else changes.)

- [ ] **Step 9.4: Rewrite the Persona test**

Replace `tests/unit/test_schema_persona.py`:
```python
from uuid import UUID

from persona_genesis.schema import Persona


def test_persona_has_generated_uuid(sample_persona: Persona) -> None:
    assert isinstance(sample_persona.id, UUID)
    assert not hasattr(sample_persona, "media")
    assert not hasattr(sample_persona, "images")


def test_persona_round_trips(sample_persona: Persona) -> None:
    restored = Persona.model_validate_json(sample_persona.model_dump_json())
    assert restored == sample_persona


def test_persona_carries_status_defaults(sample_persona: Persona) -> None:
    assert sample_persona.identity.full_name_status == "fake"
    assert sample_persona.location.country_status == "gen"
    assert sample_persona.contact.email_status == "fake"
```

- [ ] **Step 9.5: Write the PartialPersona test**

Create `tests/unit/test_schema_partial.py`:
```python
from persona_genesis.schema.partial import PartialPersona


def test_partial_all_optional() -> None:
    p = PartialPersona()
    assert p.identity is None
    assert p.metadata is None
    assert p.id is not None


def test_partial_round_trips() -> None:
    p = PartialPersona(locale="pt_BR", seed=1)
    assert PartialPersona.model_validate_json(p.model_dump_json()) == p
```

- [ ] **Step 9.6: Run + mypy**

Run:
```bash
uv run pytest tests/unit/test_schema_persona.py tests/unit/test_schema_partial.py -q
uv run mypy src/persona_genesis/schema/persona.py src/persona_genesis/schema/partial.py
```
Expected: green. (Package-level `schema/__init__.py` still references `PersonaImages`; fixed in Task 13. These tests import `persona_genesis.schema.Persona`, which triggers `schema/__init__.py` — so this will fail until Task 13. **Run these tests at the end of Task 13 instead; here, only run mypy on the two new files.**)

Run now: `uv run mypy src/persona_genesis/schema/persona.py src/persona_genesis/schema/partial.py`
Expected: mypy clean.

- [ ] **Step 9.7: Commit**

```bash
git add src/persona_genesis/schema/persona.py src/persona_genesis/schema/partial.py tests/conftest.py tests/unit/test_schema_persona.py tests/unit/test_schema_partial.py
git commit -m "feat(schema): slim Persona to synthetic sections; add PartialPersona"
```

---

## Task 10: PersonaDraft

**Files:**
- Create: `src/persona_genesis/schema/draft.py`
- Create: `tests/unit/test_schema_draft.py`

- [ ] **Step 10.1: Write the failing test**

Create `tests/unit/test_schema_draft.py`:
```python
from persona_genesis.schema.draft import PersonaDraft
from persona_genesis.schema.partial import PartialPersona


def test_draft_defaults_empty() -> None:
    d = PersonaDraft(persona=PartialPersona(locale="pt_BR"))
    assert d.faces == []
    assert d.images == []
    assert d.accounts == []
    assert d.relationships == []
    assert d.image_face_links == []
    assert d.persona.locale == "pt_BR"
```

- [ ] **Step 10.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_schema_draft.py -q`
Expected: ImportError.

- [ ] **Step 10.3: Implement**

Create `src/persona_genesis/schema/draft.py`:
```python
"""PersonaDraft — the builder's output bundle: a partial persona plus the related
entities and link intents to be persisted together by repository.save_draft."""

from uuid import UUID

from pydantic import BaseModel, Field

from persona_genesis.schema.account import Account
from persona_genesis.schema.biometrics import Body, Face, VoicePrint
from persona_genesis.schema.document import Document
from persona_genesis.schema.media import Audio, Image, Video
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.relationship import Relationship


class PersonaDraft(BaseModel):
    persona: PartialPersona
    faces: list[Face] = Field(default_factory=list)
    bodies: list[Body] = Field(default_factory=list)
    voices: list[VoicePrint] = Field(default_factory=list)
    images: list[Image] = Field(default_factory=list)
    audio: list[Audio] = Field(default_factory=list)
    video: list[Video] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)
    accounts: list[Account] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    image_face_links: list[tuple[UUID, UUID]] = Field(default_factory=list)
    audio_voice_links: list[tuple[UUID, UUID]] = Field(default_factory=list)
    document_persona_links: list[tuple[UUID, UUID]] = Field(default_factory=list)
```

- [ ] **Step 10.4: Run + mypy**

Run: `uv run pytest tests/unit/test_schema_draft.py -q && uv run mypy src/persona_genesis/schema/draft.py`
Expected: 1 passed; mypy clean.

- [ ] **Step 10.5: Commit**

```bash
git add src/persona_genesis/schema/draft.py tests/unit/test_schema_draft.py
git commit -m "feat(schema): add PersonaDraft builder-output bundle"
```

---

## Task 11: Extraction seam

**Files:**
- Create: `src/persona_genesis/extraction.py`
- Create: `tests/unit/test_extraction.py`

- [ ] **Step 11.1: Write the failing tests**

Create `tests/unit/test_extraction.py`:
```python
import pytest

from persona_genesis import extraction


def test_audio_segment_shape() -> None:
    seg = extraction.AudioSegment(text="hi", speaker="A", start_s=0.0, end_s=1.0)
    assert seg.text == "hi"
    assert seg.speaker == "A"


@pytest.mark.parametrize(
    "call",
    [
        lambda: extraction.extract_faces(b"x"),
        lambda: extraction.extract_body(b"x"),
        lambda: extraction.describe_image(b"x"),
        lambda: extraction.score_nsfw(b"x"),
        lambda: extraction.transcribe(b"x"),
        lambda: extraction.embed_text("x"),
    ],
)
def test_extraction_functions_deferred(call) -> None:
    with pytest.raises(NotImplementedError):
        call()
```

- [ ] **Step 11.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_extraction.py -q`
Expected: ImportError.

- [ ] **Step 11.3: Implement**

Create `src/persona_genesis/extraction.py`:
```python
"""AI extraction seam.

Signatures and the ``extract=`` parameter (on PersonaBuilder.add_image/add_audio)
land now; the model implementations are deferred to the extraction milestone and
raise NotImplementedError. Artifacts produced by extraction are labelled
status="gen".
"""

from pydantic import BaseModel

from persona_genesis.schema.biometrics import Body, Face, VoicePrint
from persona_genesis.schema.media import Audio, Image

_DEFERRED = "extraction is implemented in the extraction milestone (not yet wired)"


class AudioSegment(BaseModel):
    """A diarized speech segment (extraction-seam type, not persisted)."""

    text: str
    speaker: str | None = None
    start_s: float
    end_s: float


def extract_faces(image: Image | bytes) -> list[Face]:
    raise NotImplementedError(_DEFERRED)


def extract_body(image: Image | bytes) -> Body:
    raise NotImplementedError(_DEFERRED)


def describe_image(image: Image | bytes) -> str:
    raise NotImplementedError(_DEFERRED)


def score_nsfw(media: Image | Audio | bytes) -> float:
    raise NotImplementedError(_DEFERRED)


def transcribe(audio: Audio | bytes) -> list[AudioSegment]:
    raise NotImplementedError(_DEFERRED)


def extract_voice(segment: AudioSegment | bytes) -> VoicePrint:
    raise NotImplementedError(_DEFERRED)


def embed_text(text: str) -> list[float]:
    raise NotImplementedError(_DEFERRED)
```

- [ ] **Step 11.4: Run + mypy**

Run: `uv run pytest tests/unit/test_extraction.py -q && uv run mypy src/persona_genesis/extraction.py`
Expected: green.

- [ ] **Step 11.5: Commit**

```bash
git add src/persona_genesis/extraction.py tests/unit/test_extraction.py
git commit -m "feat: add AI extraction seam (signatures; impls deferred)"
```

---

## Task 12: PersonaBuilder

**Files:**
- Create: `src/persona_genesis/builder.py`
- Create: `tests/unit/test_builder.py`

- [ ] **Step 12.1: Write the failing tests**

Create `tests/unit/test_builder.py`:
```python
from pathlib import Path

import pytest
from PIL import Image as PILImage
from pydantic import ValidationError

from persona_genesis.builder import PersonaBuilder
from persona_genesis.schema.draft import PersonaDraft


def test_empty_builder_missing_all_core_sections() -> None:
    b = PersonaBuilder(locale="pt_BR", seed=42)
    assert b.missing() == {
        "identity", "location", "contact", "work", "appearance",
        "personality", "voice", "device", "backstory",
    }
    assert isinstance(b.build(), PersonaDraft)


def test_set_merges_and_marks_real() -> None:
    b = PersonaBuilder()
    b.set(identity={"given_name": "Ana", "gender": "female"})
    b.set(identity={"family_name": "Souza"})
    partial = b.build().persona
    assert partial.identity.given_name == "Ana"
    assert partial.identity.family_name == "Souza"
    assert partial.identity.given_name_status == "real"
    assert partial.identity.gender_status == "real"
    assert "identity" not in b.missing()


def test_set_status_override() -> None:
    b = PersonaBuilder()
    b.set(identity={"given_name": "Ana", "given_name_status": "gen"})
    assert b.build().persona.identity.given_name_status == "gen"


def test_set_validation_error_propagates() -> None:
    b = PersonaBuilder()
    with pytest.raises(ValidationError):
        b.set(identity={"gender": "bad"})


def test_add_image_pil_writes_and_links(tmp_path: Path) -> None:
    b = PersonaBuilder(media_dir=tmp_path)
    face = b.add_face(embedding=[0.1, 0.2])
    img = b.add_image(PILImage.new("RGB", (16, 24), "white"), type="face", link_faces=[face])
    assert img.media_type == "image/png"
    assert img.width == 16 and img.height == 24
    assert img.status == "real"
    assert (tmp_path / img.file_path).is_file()
    draft = b.build()
    assert draft.images == [img]
    assert draft.faces == [face]
    assert draft.image_face_links == [(img.id, face.id)]


def test_add_image_bytes_requires_media_type(tmp_path: Path) -> None:
    b = PersonaBuilder(media_dir=tmp_path)
    with pytest.raises(ValueError):
        b.add_image(b"\x00", type="other")


def test_add_audio_voice_document_account_relationship(tmp_path: Path) -> None:
    b = PersonaBuilder(media_dir=tmp_path)
    voice = b.add_voice(embedding=[0.3])
    audio = b.add_audio(data=b"RIFF", media_type="audio/wav", type="voice_sample",
                        link_voices=[voice])
    doc = b.add_document(content="event", embedding=[0.1])
    acc = b.add_account(url="https://m", login="u", password="p")
    from uuid import uuid4
    rel = b.add_relationship(other_persona_id=uuid4(), relationship="friend")
    draft = b.build()
    assert (tmp_path / audio.file_path).is_file()
    assert draft.audio_voice_links == [(audio.id, voice.id)]
    assert draft.documents == [doc]
    assert draft.accounts == [acc]
    assert draft.relationships == [rel]
    assert acc.persona_id == draft.persona.id
    assert rel.person_1_id == draft.persona.id


def test_extract_true_without_provider_raises(tmp_path: Path) -> None:
    b = PersonaBuilder(media_dir=tmp_path)
    with pytest.raises(NotImplementedError):
        b.add_image(PILImage.new("RGB", (8, 8), "white"), type="face", extract=True)
```

- [ ] **Step 12.2: Run to verify failure**

Run: `uv run pytest tests/unit/test_builder.py -q`
Expected: ImportError.

- [ ] **Step 12.3: Implement**

Create `src/persona_genesis/builder.py`:
```python
"""PersonaBuilder — assemble a PartialPersona plus related entities into a
PersonaDraft. set() marks caller-provided scalars status="real". add_* write
binaries to disk and accumulate entities; extract=True runs the (deferred)
extraction seam. No generation, no DB here."""

import io
from pathlib import Path
from typing import Any
from uuid import UUID

from PIL import Image as PILImage

from persona_genesis import extraction
from persona_genesis.media.storage import store_media
from persona_genesis.schema.account import Account
from persona_genesis.schema.appearance import Appearance
from persona_genesis.schema.backstory import Backstory
from persona_genesis.schema.biometrics import Body, Face, VoicePrint
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.device import Device
from persona_genesis.schema.document import Document
from persona_genesis.schema.draft import PersonaDraft
from persona_genesis.schema.identity import Identity
from persona_genesis.schema.location import Location
from persona_genesis.schema.media import Audio, Image, MediaOrigin, Video
from persona_genesis.schema.metadata import PersonaMetadata
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.personality import Personality
from persona_genesis.schema.relationship import Relationship, RelationshipType
from persona_genesis.schema.voice import Voice
from persona_genesis.schema.work import Work

DEFAULT_MEDIA_DIR = "/srv/persona-genesis/media/"

_SECTION_MODELS: dict[str, type[Any]] = {
    "identity": Identity,
    "location": Location,
    "contact": Contact,
    "work": Work,
    "appearance": Appearance,
    "personality": Personality,
    "voice": Voice,
    "device": Device,
    "backstory": Backstory,
    "metadata": PersonaMetadata,
}
_CORE_SECTIONS: tuple[str, ...] = (
    "identity", "location", "contact", "work", "appearance",
    "personality", "voice", "device", "backstory",
)

_PIL_FORMAT = {"image/png": "PNG", "image/jpeg": "JPEG", "image/jpg": "JPEG",
               "image/webp": "WEBP", "image/gif": "GIF"}


class PersonaBuilder:
    def __init__(self, *, locale: str | None = None, seed: int | None = None,
                 media_dir: str | Path = DEFAULT_MEDIA_DIR) -> None:
        self._draft = PersonaDraft(persona=PartialPersona(locale=locale, seed=seed))
        self._media_dir = media_dir

    # -- sections -------------------------------------------------------------

    def set(self, **sections: dict[str, Any]) -> "PersonaBuilder":
        for name, value in sections.items():
            if name not in _SECTION_MODELS:
                raise ValueError(f"unknown section: {name!r}")
            model = _SECTION_MODELS[name]
            existing = getattr(self._draft.persona, name)
            merged: dict[str, Any] = existing.model_dump() if existing is not None else {}
            merged.update(value)
            # mark caller-provided scalars/lists real unless an explicit status was given
            for key in value:
                if key.endswith("_status"):
                    continue
                status_key = f"{key}_status"
                if status_key in model.model_fields and status_key not in value:
                    merged[status_key] = "real"
            setattr(self._draft.persona, name, model.model_validate(merged))
        return self

    def set_status(self, section: str, field: str, status: str) -> "PersonaBuilder":
        return self.set(**{section: {f"{field}_status": status}})

    def missing(self) -> set[str]:
        return {n for n in _CORE_SECTIONS if getattr(self._draft.persona, n) is None}

    # -- media ----------------------------------------------------------------

    def add_image(self, image: PILImage.Image | bytes, *, type: str, media_type: str | None = None,
                  nsfw: float = 0.0, description: str | None = None, status: str = "real",
                  origin: MediaOrigin | None = None, media_dir: str | Path | None = None,
                  extract: bool = False, link_faces: list[Face] | None = None) -> Image:
        width: int | None = None
        height: int | None = None
        if isinstance(image, PILImage.Image):
            media_type = media_type or "image/png"
            width, height = image.size
            buf = io.BytesIO()
            image.save(buf, format=_PIL_FORMAT.get(media_type.lower(), "PNG"))
            data = buf.getvalue()
        else:
            if media_type is None:
                raise ValueError("media_type is required when adding raw image bytes")
            data = image
        rel = store_media(data, kind="image", media_type=media_type,
                          media_dir=media_dir or self._media_dir)
        entry = Image(file_path=rel, media_type=media_type, type=type,  # type: ignore[arg-type]
                      nsfw=nsfw, width=width, height=height, description=description,
                      origin=origin, status=status)  # type: ignore[arg-type]
        self._draft.images.append(entry)
        faces = list(link_faces or [])
        if extract:
            entry.description = extraction.describe_image(entry)
            entry.nsfw = extraction.score_nsfw(entry)
            entry.status = "gen"
            extracted = extraction.extract_faces(entry)
            self._draft.faces.extend(extracted)
            faces.extend(extracted)
        for face in faces:
            self._draft.image_face_links.append((entry.id, face.id))
        return entry

    def add_audio(self, *, data: bytes, media_type: str, type: str, text: str | None = None,
                  nsfw: float = 0.0, sample_rate_hz: int | None = None,
                  duration_s: float | None = None, status: str = "real",
                  origin: MediaOrigin | None = None, media_dir: str | Path | None = None,
                  extract: bool = False, link_voices: list[VoicePrint] | None = None) -> Audio:
        rel = store_media(data, kind="audio", media_type=media_type,
                          media_dir=media_dir or self._media_dir)
        entry = Audio(file_path=rel, media_type=media_type, type=type,  # type: ignore[arg-type]
                      text=text, nsfw=nsfw, sample_rate_hz=sample_rate_hz,
                      duration_s=duration_s, origin=origin, status=status)  # type: ignore[arg-type]
        self._draft.audio.append(entry)
        voices = list(link_voices or [])
        if extract:
            segments = extraction.transcribe(entry)
            entry.text = " ".join(s.text for s in segments)
            entry.nsfw = extraction.score_nsfw(entry)
            entry.status = "gen"
            for seg in segments:
                vp = extraction.extract_voice(seg)
                self._draft.voices.append(vp)
                voices.append(vp)
        for voice in voices:
            self._draft.audio_voice_links.append((entry.id, voice.id))
        return entry

    def add_video(self, *, data: bytes, media_type: str, type: str, media_dir: str | Path | None = None,
                  status: str = "real", **fields: Any) -> Video:
        rel = store_media(data, kind="video", media_type=media_type,
                          media_dir=media_dir or self._media_dir)
        entry = Video(file_path=rel, media_type=media_type, type=type,  # type: ignore[arg-type]
                      status=status, **fields)  # type: ignore[arg-type]
        self._draft.video.append(entry)
        return entry

    # -- biometrics -----------------------------------------------------------

    def add_face(self, *, embedding: list[float], status: str = "real") -> Face:
        face = Face(persona_id=self._draft.persona.id, embedding=embedding, status=status)  # type: ignore[arg-type]
        self._draft.faces.append(face)
        return face

    def add_body(self, *, embedding: list[float], status: str = "real") -> Body:
        body = Body(persona_id=self._draft.persona.id, embedding=embedding, status=status)  # type: ignore[arg-type]
        self._draft.bodies.append(body)
        return body

    def add_voice(self, *, embedding: list[float], label: str | None = None,
                  status: str = "real") -> VoicePrint:
        vp = VoicePrint(persona_id=self._draft.persona.id, embedding=embedding,
                        label=label, status=status)  # type: ignore[arg-type]
        self._draft.voices.append(vp)
        return vp

    # -- documents / accounts / relationships ---------------------------------

    def add_document(self, *, content: str, embedding: list[float] | None = None,
                     metadata: dict[str, Any] | None = None, status: str = "real") -> Document:
        doc = Document(content=content, embedding=embedding, metadata=metadata or {},
                       status=status)  # type: ignore[arg-type]
        self._draft.documents.append(doc)
        self._draft.document_persona_links.append((doc.id, self._draft.persona.id))
        return doc

    def add_account(self, *, url: str, login: str, password: str,
                    session_token: str | None = None, notes: str | None = None) -> Account:
        acc = Account(persona_id=self._draft.persona.id, url=url, login=login,
                      password=password, session_token=session_token, notes=notes)
        self._draft.accounts.append(acc)
        return acc

    def add_relationship(self, *, other_persona_id: UUID, relationship: RelationshipType,
                         status: str = "gen", notes: str | None = None) -> Relationship:
        rel = Relationship(person_1_id=self._draft.persona.id, person_2_id=other_persona_id,
                           relationship=relationship, status=status, notes=notes)  # type: ignore[arg-type]
        self._draft.relationships.append(rel)
        return rel

    # -- links / build --------------------------------------------------------

    def link_image_face(self, image: Image, face: Face) -> None:
        self._draft.image_face_links.append((image.id, face.id))

    def link_audio_voice(self, audio: Audio, voice: VoicePrint) -> None:
        self._draft.audio_voice_links.append((audio.id, voice.id))

    def build(self) -> PersonaDraft:
        return self._draft
```

- [ ] **Step 12.4: Run + lint + mypy**

Run:
```bash
uv run pytest tests/unit/test_builder.py -q
uv run ruff check src/persona_genesis/builder.py
uv run mypy src/persona_genesis/builder.py
```
Expected: all green. (Resolve any `type: ignore` mypy disagreements by narrowing the `status`/`type` params to the proper `Literal`/`Status` types if mypy prefers.)

- [ ] **Step 12.5: Commit**

```bash
git add src/persona_genesis/builder.py tests/unit/test_builder.py
git commit -m "feat: add PersonaBuilder producing a PersonaDraft

set() marks caller scalars status=real; add_* write binaries to disk and
accumulate entities + link intents; extract=True drives the deferred seam."
```

---

## Task 13: Config dims + public re-exports

**Files:**
- Modify: `src/persona_genesis/config.py`, `tests/unit/test_config.py`
- Modify: `src/persona_genesis/schema/__init__.py`, `src/persona_genesis/__init__.py`
- Modify: `tests/unit/test_public_api.py`

- [ ] **Step 13.1: Add Config tests (failing)**

Append to `tests/unit/test_config.py`:
```python
def test_config_persistence_and_embedding_dims() -> None:
    cfg = Config()
    assert cfg.database_url is None
    assert cfg.vault_key is None
    assert cfg.media_dir == "/srv/persona-genesis/media/"
    assert cfg.face_embedding_dim == 512
    assert cfg.body_embedding_dim == 2048
    assert cfg.voice_embedding_dim == 192
    assert cfg.document_embedding_dim == 1536


def test_config_dims_from_dict() -> None:
    cfg = Config.from_dict({"face_embedding_dim": 256, "media_dir": "/tmp/m"})
    assert cfg.face_embedding_dim == 256
    assert cfg.media_dir == "/tmp/m"
```

- [ ] **Step 13.2: Add the fields to Config**

In `src/persona_genesis/config.py`, add to the `Config` class body (after `log_level`):
```python
    database_url: str | None = None
    vault_key: str | bytes | None = None
    media_dir: str = "/srv/persona-genesis/media/"
    face_embedding_dim: int = 512
    body_embedding_dim: int = 2048
    voice_embedding_dim: int = 192
    document_embedding_dim: int = 1536
```

- [ ] **Step 13.3: Rewrite schema/__init__.py**

Replace `src/persona_genesis/schema/__init__.py`:
```python
"""Pydantic schema models — the persona-genesis public contract."""

from persona_genesis.schema.account import Account
from persona_genesis.schema.appearance import Appearance, Build
from persona_genesis.schema.backstory import Backstory, Education, LifeEvent
from persona_genesis.schema.biometrics import Body, Face, VoicePrint
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.device import OS, Browser, Device, DeviceType
from persona_genesis.schema.document import Document
from persona_genesis.schema.draft import PersonaDraft
from persona_genesis.schema.identity import Gender, Identity
from persona_genesis.schema.location import Location
from persona_genesis.schema.media import (
    Audio,
    AudioType,
    Image,
    ImageType,
    MediaOrigin,
    Video,
    VideoType,
)
from persona_genesis.schema.metadata import PersonaMetadata
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.persona import Persona
from persona_genesis.schema.personality import OceanScores, Personality
from persona_genesis.schema.relationship import Relationship, RelationshipType
from persona_genesis.schema.status import Status
from persona_genesis.schema.voice import Voice
from persona_genesis.schema.work import Schedule, Seniority, Work

__all__ = [
    "OS",
    "Account",
    "Appearance",
    "Audio",
    "AudioType",
    "Backstory",
    "Body",
    "Browser",
    "Build",
    "Contact",
    "Device",
    "DeviceType",
    "Document",
    "Education",
    "Face",
    "Gender",
    "Identity",
    "Image",
    "ImageType",
    "LifeEvent",
    "Location",
    "MediaOrigin",
    "OceanScores",
    "PartialPersona",
    "Persona",
    "PersonaDraft",
    "PersonaMetadata",
    "Personality",
    "Relationship",
    "RelationshipType",
    "Schedule",
    "Seniority",
    "Status",
    "Video",
    "VideoType",
    "Voice",
    "VoicePrint",
    "Work",
]
```

- [ ] **Step 13.4: Rewrite top-level __init__.py**

Replace `src/persona_genesis/__init__.py`:
```python
"""persona-genesis: generate detailed, coherent personas.

Public API exposes the data contract (`Persona`, `PartialPersona`, media,
biometric, document, relationship, and vault models), the `PersonaBuilder`,
configuration, and the exception hierarchy. The persistence repository (Plan 2)
and the `PersonaGenerator` orchestrator are added in later milestones.
"""

from persona_genesis.builder import PersonaBuilder
from persona_genesis.config import Config, ImageConfig, LLMConfig
from persona_genesis.exceptions import (
    CoherenceError,
    ConfigError,
    PersonaGenerationError,
    PersonaGenesisError,
    ProviderError,
)
from persona_genesis.schema import (
    Account,
    Appearance,
    Audio,
    Backstory,
    Body,
    Contact,
    Device,
    Document,
    Education,
    Face,
    Identity,
    Image,
    Location,
    MediaOrigin,
    OceanScores,
    PartialPersona,
    Persona,
    PersonaDraft,
    PersonaMetadata,
    Personality,
    Relationship,
    Status,
    Video,
    Voice,
    VoicePrint,
    Work,
)

__version__ = "0.1.0"

__all__ = [
    "Account",
    "Appearance",
    "Audio",
    "Backstory",
    "Body",
    "CoherenceError",
    "Config",
    "ConfigError",
    "Contact",
    "Device",
    "Document",
    "Education",
    "Face",
    "Identity",
    "Image",
    "ImageConfig",
    "LLMConfig",
    "Location",
    "MediaOrigin",
    "OceanScores",
    "PartialPersona",
    "Persona",
    "PersonaBuilder",
    "PersonaDraft",
    "PersonaGenerationError",
    "PersonaGenesisError",
    "PersonaMetadata",
    "Personality",
    "ProviderError",
    "Relationship",
    "Status",
    "Video",
    "Voice",
    "VoicePrint",
    "Work",
    "__version__",
]
```

- [ ] **Step 13.5: Rewrite the public-API test**

Replace `tests/unit/test_public_api.py`:
```python
import persona_genesis


def test_public_api_exposes_contract() -> None:
    from persona_genesis import Config, PartialPersona, Persona, PersonaBuilder

    assert persona_genesis.__version__ == "0.1.0"
    assert Persona.__name__ == "Persona"
    assert PartialPersona.__name__ == "PartialPersona"
    assert PersonaBuilder.__name__ == "PersonaBuilder"
    assert Config().default_locale == "en_US"


def test_new_entity_symbols_exported() -> None:
    from persona_genesis import (
        Account,
        Body,
        Document,
        Face,
        Image,
        Relationship,
        VoicePrint,
    )

    assert {Account, Body, Document, Face, Image, Relationship, VoicePrint}


def test_persona_images_gone() -> None:
    assert not hasattr(persona_genesis, "PersonaImages")
    assert not hasattr(persona_genesis, "PersonaMedia")


def test_exceptions_reachable() -> None:
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

- [ ] **Step 13.6: Full Plan-1 verification**

Run:
```bash
uv run pytest tests/unit -q
uv run ruff check src/persona_genesis tests
uv run mypy src/persona_genesis tests
```
Expected: all unit tests pass; lint clean; mypy clean. This is where the deferred runs from Task 9 Step 9.6 (Persona/Partial via `schema/__init__`) and all builder/media/etc. tests go green together.

- [ ] **Step 13.7: Commit**

```bash
git add src/persona_genesis/config.py tests/unit/test_config.py src/persona_genesis/schema/__init__.py src/persona_genesis/__init__.py tests/unit/test_public_api.py
git commit -m "feat: Config embedding dims + public re-exports for new entities"
```

---

## Task 14: CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 14.1: Record the contract-layer changes**

Under `## [Unreleased]` in `CHANGELOG.md`, add `### Added` / `### Changed` / `### Removed` entries summarising: `Status` provenance with `_status` siblings across all sections; real-only Contact/Location; standalone `Image`/`Audio`/`Video` (with `unknown` type); biometric `Face`/`Body`/`VoicePrint`; RAG `Document`; `Relationship`; `Account`; `PartialPersona`; `PersonaDraft`; `PersonaBuilder`; on-disk media storage; extraction seam; Config embedding-dim fields. Removed: `PersonaImages`, `Persona.images`/`media`.

- [ ] **Step 14.2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: changelog for the decoupled-entities contract layer"
```

---

## Self-Review (against the spec)

**Spec coverage (§ refs to 2026-06-04 spec):**
- §3 `Status` + `_status` across sections, default map, auto-`real` on set → Tasks 1–4, 12.
- §4 slim Persona/PartialPersona → Task 9.
- §5 Image/Audio/Video (+`unknown`), Face/Body/VoicePrint, Document, Relationship, Account, MediaOrigin → Tasks 6, 7, 8.
- §7 PersonaDraft + PersonaBuilder (set/set_status/missing/add_*/link_*/build, `extract=`) → Tasks 10, 12.
- §8 extraction seam (signatures, NotImplementedError, AudioSegment) → Task 11.
- §6.1 on-disk hashed storage → Task 5.
- §10 Config embedding dims + database_url/vault_key/media_dir → Task 13.
- §11 public re-exports add new / drop removed → Task 13.
- §13 testing (round-trips, status defaults/auto-real, provenance validator, nsfw bounds, storage dedupe/override, builder links, extract raises) → Tasks 1–13.

**Deferred (NOT built here):** all AI extraction impls (raise), Video extraction, persistence/`db/` (Plan 2), `afill`, `create_image`/`create_audio`, CLI. Correct.

**Type consistency:** `store_media(data, *, kind, media_type, media_dir)` identical in storage + builder. `VoicePrint` used everywhere (never the text `Voice`) for biometrics. `_CORE_SECTIONS` (9) matches the `missing()` test. Builder status-injection convention `<field>_status` matches the section models' field names. `PersonaDraft` link fields (`image_face_links`, `audio_voice_links`, `document_persona_links`) match the builder's appends.

**Note:** Persistence of `PersonaDraft` (and accounts/relationships/embeddings) is Plan 2; this plan leaves the draft in-memory and fully unit-tested.
