import pytest

from persona_genesis.builder import PersonaBuilder
from persona_genesis.config import Config
from persona_genesis.exceptions import ConfigError, PersonaGenerationError
from persona_genesis.orchestrator import PersonaGenerator
from persona_genesis.schema.contact import Contact


def test_generate_structured_fills_structured_sections_only() -> None:
    p = PersonaGenerator(Config()).generate_structured(seed=42, locale="pt_BR")
    assert p.identity is not None and p.location is not None
    assert p.work is not None and p.device is not None
    assert p.contact == Contact()              # real-only, empty
    assert p.personality is None and p.voice is None
    assert p.backstory is None and p.appearance is None
    assert p.seed == 42 and p.locale == "pt_BR"


def test_generate_structured_deterministic_content() -> None:
    g = PersonaGenerator(Config())
    a = g.generate_structured(seed=42, locale="pt_BR")
    b = g.generate_structured(seed=42, locale="pt_BR")
    assert a.model_dump(exclude={"id"}) == b.model_dump(exclude={"id"})


def test_unsupported_locale_raises() -> None:
    cfg = Config.from_dict({"default_locale": "xx_XX"})
    with pytest.raises(PersonaGenerationError):
        PersonaGenerator(cfg).generate_structured(seed=1, locale="zz_ZZ")


def test_locale_falls_back_to_default() -> None:
    cfg = Config.from_dict({"default_locale": "en_US"})
    p = PersonaGenerator(cfg).generate_structured(seed=1, locale="zz_ZZ")
    assert p.locale == "en_US"


def test_agenerate_requires_llm() -> None:
    with pytest.raises(ConfigError):
        PersonaGenerator(Config()).generate(seed=1)


def test_fill_structured_preserves_caller_sections() -> None:
    b = PersonaBuilder(locale="pt_BR", seed=42)
    b.set(work={"occupation": "Astronaut", "employer": "NASA", "seniority": "lead",
                "industry": "Aerospace", "schedule": "full_time"})
    p = PersonaGenerator(Config()).fill_structured(b)
    assert p.work is not None
    assert p.work.occupation == "Astronaut"         # caller-set, untouched
    assert p.work.occupation_status == "real"
    assert p.identity is not None                    # generated (was missing)
    assert p.location is not None and p.device is not None


async def test_agenerate_structured_matches_sync() -> None:
    g = PersonaGenerator(Config())
    a = g.generate_structured(seed=5, locale="en_US")
    b = await g.agenerate_structured(seed=5, locale="en_US")
    assert a.model_dump(exclude={"id"}) == b.model_dump(exclude={"id"})


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
