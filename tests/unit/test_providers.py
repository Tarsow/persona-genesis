from persona_genesis.providers.image import ImageProvider
from persona_genesis.providers.llm import LLMProvider


def test_protocols_are_runtime_checkable() -> None:
    class FakeLLM:
        async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str:
            return "x"

        async def acomplete_json(self, system, user, schema):  # type: ignore[no-untyped-def]
            return schema()

    assert isinstance(FakeLLM(), LLMProvider)
    assert not isinstance(object(), ImageProvider)
