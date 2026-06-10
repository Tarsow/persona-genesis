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
    assert isinstance(a, _Out) and isinstance(b, _Out) and isinstance(c, _Out)
    assert (a.x, b.x, c.x) == (1, 2, 2)
