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
