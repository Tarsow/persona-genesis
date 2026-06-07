# persona-genesis — Structured Generation Layer

**Date:** 2026-06-06
**Status:** Approved
**Phase:** Roadmap Phase 1 (`docs/roadmap.md`)
**Builds on:** `specs/2026-06-01` (PersonaGenerator concept), `specs/2026-06-04` (contract,
`_status` provenance, `PartialPersona`, `PersonaBuilder`).

## 1. Context

Phase 0 shipped the contract + persistence. This phase adds the **deterministic,
offline half of AI generation**: structured fields a persona needs that require no
LLM, image model, or paid API — `identity`, `location`, `work`, `device` — produced
"as real as possible" and reproducible from a seed. The narrative (LLM) and visual
(image) layers are deferred to Phases 2–3 behind provider protocols defined here.

## 2. Public API

```python
from persona_genesis import PersonaGenerator, Config

gen = PersonaGenerator(Config(), geolocator=None)   # llm/image optional, deferred

partial = gen.generate_structured(seed=42, locale="pt_BR")           # sync
partial = await gen.agenerate_structured(seed=42, locale="pt_BR")    # async
# -> PartialPersona: identity/location/work/device filled; contact == Contact();
#    personality/voice/appearance/backstory/metadata == None
```

### 2.1 `PersonaGenerator`

```python
class PersonaGenerator:
    def __init__(
        self,
        config: Config,
        *,
        geolocator: GeoLocator | None = None,
        llm: LLMProvider | None = None,
        image: ImageProvider | None = None,
    ) -> None: ...

    # the deliverable (async-first; sync wrappers delegate to the same core)
    async def agenerate_structured(
        self, seed: int, locale: str | None = None, *,
        constraints: StructuredConstraints | None = None,
    ) -> PartialPersona: ...
    def generate_structured(self, seed, locale=None, *, constraints=None) -> PartialPersona: ...

    async def afill_structured(self, builder: PersonaBuilder) -> PartialPersona: ...
    def fill_structured(self, builder: PersonaBuilder) -> PartialPersona: ...

    # full generation — exists but deferred until an LLM provider is wired (Phase 2)
    async def agenerate(self, seed, locale=None, *, constraints=None, include=None) -> Persona:
        # raises ConfigError("an LLM provider is required to generate narrative sections")
        ...
    def generate(self, *args, **kwargs) -> Persona: ...
```

- `locale` defaults to `config.default_locale`.
- `generate_structured` is the synchronous core; `agenerate_structured` is an async
  wrapper that returns the same result (the structured work is local/CPU-bound — no
  real awaiting, but the async signature keeps the API consistent with Phase 2).
- The result is a **`PartialPersona`** (narrative sections are `None`); strict
  `Persona` requires the narrative layer.

### 2.2 `StructuredConstraints`

```python
class StructuredConstraints(BaseModel):
    age_range: tuple[int, int] = (18, 75)     # inclusive; dob derived to fall in range
    gender: Gender | None = None               # pin gender, else seeded choice
    seniority: Seniority | None = None         # pin seniority, else age-eligible choice
    device_type: DeviceType | None = None      # filter the ua_pool
    ip: str | None = None                      # geolocate -> location (requires GeoLocator)
```

### 2.3 `afill_structured`

Generates only the **structured sections that are entirely `None`** in
`builder.missing()` (section-level granularity), assembling a `PartialPersona` that
preserves every caller-set section unchanged. Uses the builder's `seed`/`locale`.
Completing *partially*-set sections from caller fields is deferred (Phase 2's
`afill`). Deterministic given `seed` + the pre-set fields.

## 3. Section generation

Each generator is deterministic given a `random.Random(seed)` and a
`Faker(faker_locale)` seeded with `seed`. The generator constructs section models
**directly** with explicit `_status` (it does not go through `PersonaBuilder.set`,
which would mark fields `real`).

### 3.1 Identity (`generators/identity.py`) — status `fake`

- `gender` = `constraints.gender` or seeded choice of `male`/`female`/`non_binary`.
- `given_name` = Faker `first_name_male`/`first_name_female` (or `first_name` for
  non-binary); `family_name` = Faker `last_name`; `full_name = f"{given} {family}"`.
- `dob` = Faker `date_of_birth` bounded by `age_range`.
- `nationality` = the locale's country (e.g. `pt_BR → "BR"`, `en_US → "US"`) via a
  locale→country map.

### 3.2 Location (`generators/location.py`) — status `gen`

- **If `constraints.ip` is set:** require a `GeoLocator` (else `ConfigError`); look up
  the IP → `country/region/city/timezone/postal_code`. `street` stays `None` (GeoIP
  has no street — no fabrication). `postal_code` is set when the lookup provides one.
- **Otherwise:** pick a real tuple from the bundled `data/locations/<locale>.json`
  (`{country, region, city, timezone}`) by seeded choice; `street`/`postal_code`
  stay `None`.

### 3.3 Work (`generators/work.py`) — status `fake`

- `occupation` + `industry`: seeded pick of an entry from `data/occupations.json`
  (`{occupation, industry}`) — coherent by construction.
- `employer` = Faker `company` (a realistic but invented name — correctly `fake`).
- `seniority` = `constraints.seniority` or a seeded choice **among seniorities the
  age allows**: `years_experience = max(0, age - 22)`; eligible seniorities are those
  whose `minimum_years_experience` ≤ `years_experience` (lookup below). A 22-year-old
  can only be intern/junior; senior roles require more years. This makes age↔seniority
  coherent without a retry pass.
- `schedule` = seeded choice of the `Schedule` literal.

```python
_MIN_YEARS = {"intern": 0, "junior": 0, "mid": 3, "senior": 7,
              "lead": 10, "manager": 8, "director": 15, "executive": 20}
```

### 3.4 Device (`generators/device.py`) — status `fake`

- Seeded pick of a coherent profile from `data/ua_pool.json` (filtered by
  `constraints.device_type` when given): `{device, os, browser, ua, resolutions}`.
- `screen_resolution` = seeded choice from the profile's `resolutions`.
- All five `Device` fields come from one profile, so `user_agent` always matches
  `primary_device`/`os`/`browser`.

### 3.5 Contact

A generated persona leaves `contact = Contact()` (all `None`) — real-only, never
fabricated.

## 4. Data assets (`src/persona_genesis/data/`)

Bundled JSON, shipped in the wheel (hatchling force-include `data/**`):

- `locations/en_US.json`, `locations/pt_BR.json` — lists of real
  `{country, region, city, timezone}`. Initial locales: `en_US`, `pt_BR`; adding a
  locale = adding a file + a locale→country/Faker-locale entry.
- `ua_pool.json` — coherent device profiles across desktop/laptop/smartphone/tablet ×
  the supported os/browser combinations, each with a real UA string and plausible
  `resolutions`.
- `occupations.json` — `{occupation, industry}` pairs.

Unsupported locale → fall back to `config.default_locale` if it has a dataset, else
raise `PersonaGenerationError`.

## 5. GeoIP (`geo/`)

```python
class GeoLocation(BaseModel):
    country: str            # ISO 3166-1 alpha-2
    region: str
    city: str
    timezone: str           # IANA
    postal_code: str | None = None

class GeoLocator(Protocol):
    def locate(self, ip: str) -> GeoLocation: ...

class GeoIP2Locator:        # geo/geoip2_locator.py
    def __init__(self, database_path: str) -> None: ...   # lazy-imports geoip2
    def locate(self, ip: str) -> GeoLocation: ...          # AddressNotFound -> PersonaGenerationError
```

`Config` gains `geoip_database_path: str | None = None`. The caller constructs
`GeoIP2Locator(config.geoip_database_path)` and passes it to `PersonaGenerator`. The
GeoLite2-City `.mmdb` is MaxMind-licensed and **not bundled** — the caller provides
it. `geoip2` is an optional `[geoip]` extra; `geoip2_locator.py` imports it lazily so
the core install doesn't require it.

## 6. Provider protocols (`providers/`) — seam only

```python
class LLMProvider(Protocol):
    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str: ...
    async def acomplete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel: ...

class ImageProvider(Protocol):
    async def agenerate(self, prompt: str, *, aspect: str = "1:1", seed: int | None = None) -> "PIL.Image.Image": ...
```

No adapters in this phase. `PersonaGenerator.agenerate()` raises `ConfigError` when
`llm is None`.

## 7. Determinism

- One `random.Random(seed)` plus `Faker(faker_locale)` with `seed_instance(seed)`
  drive every choice. Same `(seed, locale, constraints)` → identical `PartialPersona`.
- The IP path depends on the GeoLite2 database contents, so it is **not** guaranteed
  byte-stable across `.mmdb` versions (documented; gated in tests).

## 8. `_status` assignment

Set explicitly by the generators, consistent with the contract's default-status map:
identity → `fake`; location (dataset or IP-derived) → `gen`; work → `fake`; device →
`fake`; contact stays empty. Caller-set fields via `afill_structured` keep their
`real` status (the builder set them).

## 9. Config, dependencies, layout

- `Config.geoip_database_path: str | None = None`.
- New optional extra `[geoip] = ["geoip2>=4"]`; `[all]` includes it.
- `Faker` (already core) powers names/dob/employer. `fake-useragent` and
  `polyfactory` are **not** used by this layer (device uses the curated `ua_pool`);
  they remain declared but unused for now.
- New files:
  ```
  src/persona_genesis/
    orchestrator.py
    generators/{__init__,structured,identity,location,work,device}.py
    geo/{__init__,base,geoip2_locator}.py
    providers/{__init__,llm,image}.py
    data/{locations/en_US.json,locations/pt_BR.json,ua_pool.json,occupations.json}
  ```
- Public re-exports add `PersonaGenerator`, `StructuredConstraints`, `GeoLocator`,
  `GeoLocation`, `GeoIP2Locator`, `LLMProvider`, `ImageProvider`.

## 10. Testing

- **Determinism:** same `(seed, locale)` → identical `PartialPersona`; different seeds
  differ.
- **Identity:** gendered name matches `gender`; `dob` falls within `age_range`;
  `nationality` matches locale; statuses `fake`.
- **Location:** dataset path yields a coherent real `country/region/city/timezone`
  with `street`/`postal_code` `None`; statuses `gen`.
- **Work:** a 22-year-old is never `director`/`executive`; `occupation`/`industry`
  come paired; statuses `fake`.
- **Device:** the five fields come from one `ua_pool` profile (UA matches
  device/os/browser); `device_type` constraint honored.
- **Contact:** `partial.contact == Contact()`.
- **`afill_structured`:** fills only entirely-missing structured sections; never
  overwrites caller-set sections.
- **`agenerate` deferral:** raises `ConfigError` when no LLM provider.
- **GeoIP:** with a fake `GeoLocator`, `ip` yields location with `street is None` and
  `postal_code` from the locator; `ip` without a locator raises `ConfigError`. A real
  `GeoIP2Locator` test is gated behind `PERSONA_GENESIS_TEST_GEOIP_DB` (skips if unset).

## 11. Lands now vs deferred

**Now:** `PersonaGenerator` (structured methods + `agenerate` stub), the four section
generators, `StructuredConstraints`, bundled data (`en_US`/`pt_BR` locations,
`ua_pool`, `occupations`), `GeoLocator` + `GeoIP2Locator`, provider protocols,
`Config.geoip_database_path`, the `[geoip]` extra, public re-exports, tests.

**Deferred:** narrative (LLM) + visual (image) layers and their `agenerate` body, the
coherence **retry** pass (structured is coherent by construction), provider adapters,
`afill` that completes partially-set sections, additional locales.

## 12. Follow-up

Phase 2 (narrative + coherence + LLM adapters), Phase 3 (visual/biometric), and the
later phases per `docs/roadmap.md`.
