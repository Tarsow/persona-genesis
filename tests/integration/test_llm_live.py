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
