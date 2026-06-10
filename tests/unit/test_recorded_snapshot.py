"""Offline snapshot of the full agenerate() path, replayed from a committed
cassette recorded against the live DeepSeek API. Runs at --level 0 (no network,
no API cost): regressions in prompt assembly, JSON parsing, the coherence pass,
or the PartialPersona -> Persona merge will fail here."""

from pathlib import Path

import pytest

from persona_genesis.config import Config
from persona_genesis.exceptions import ProviderError
from persona_genesis.orchestrator import PersonaGenerator
from persona_genesis.providers.recorded import RecordedProvider
from persona_genesis.schema.persona import Persona

_CASSETTE = (
    Path(__file__).resolve().parent.parent / "data" / "cassettes" / "agenerate_seed1_en_US.json"
)


async def test_agenerate_replays_from_cassette_offline() -> None:
    assert _CASSETTE.exists(), f"missing cassette: {_CASSETTE}"
    llm = RecordedProvider(_CASSETTE)  # no upstream -> pure replay, no network
    gen = PersonaGenerator(Config(), llm=llm)

    persona = await gen.agenerate(seed=1, locale="en_US")

    # Structured sections are deterministic from the seed.
    assert isinstance(persona, Persona)
    assert persona.identity.full_name == "Chad Boone"
    assert persona.work.occupation

    # Narrative sections come from the replayed LLM output, tagged "gen".
    assert persona.backstory.bio
    assert persona.backstory.bio_status == "gen"
    assert persona.appearance.description
    assert persona.appearance.description_status == "gen"
    assert persona.personality.traits
    assert persona.voice.sample_paragraph


async def test_replay_is_deterministic() -> None:
    gen = PersonaGenerator(Config(), llm=RecordedProvider(_CASSETTE))
    a = await gen.agenerate(seed=1, locale="en_US")
    gen2 = PersonaGenerator(Config(), llm=RecordedProvider(_CASSETTE))
    b = await gen2.agenerate(seed=1, locale="en_US")
    assert a.backstory.bio == b.backstory.bio
    assert a.appearance.description == b.appearance.description


async def test_replay_miss_on_wrong_prompt() -> None:
    # A cassette recorded for seed=1/en_US cannot serve a different seed.
    gen = PersonaGenerator(Config(), llm=RecordedProvider(_CASSETTE))
    with pytest.raises(ProviderError):
        await gen.agenerate(seed=999, locale="en_US")
