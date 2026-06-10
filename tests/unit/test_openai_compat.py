import httpx
import pytest
from pydantic import BaseModel

from persona_genesis.exceptions import ProviderError
from persona_genesis.providers.openai_compat import OpenAICompatProvider


def _provider(handler: object, **kw: object) -> OpenAICompatProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
    return OpenAICompatProvider(api_key="k", http_client=client, **kw)  # type: ignore[arg-type]


async def test_acomplete_returns_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "pong"}}]})

    assert await _provider(handler).acomplete("s", "u") == "pong"


async def test_acomplete_json_parses_schema() -> None:
    class Out(BaseModel):
        x: int

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"x": 7}'}}]})

    out = await _provider(handler).acomplete_json("s", "u", Out)
    assert isinstance(out, Out) and out.x == 7


async def test_acomplete_json_retries_then_raises() -> None:
    class Out(BaseModel):
        x: int

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    with pytest.raises(ProviderError):
        await _provider(handler, max_retries=2).acomplete_json("s", "u", Out)
    assert calls["n"] == 3  # initial + 2 retries


async def test_http_error_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(ProviderError):
        await _provider(handler).acomplete("s", "u")
