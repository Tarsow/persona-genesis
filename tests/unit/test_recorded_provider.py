import json

import pytest
from pydantic import BaseModel

from persona_genesis.exceptions import ProviderError
from persona_genesis.providers.fake_llm import FakeLLMProvider
from persona_genesis.providers.recorded import RecordedProvider


class _Out(BaseModel):
    x: int


class _CountingProvider:
    """LLMProvider double that counts calls and returns distinct payloads."""

    def __init__(self) -> None:
        self.text_calls = 0
        self.json_calls = 0

    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str:
        self.text_calls += 1
        return f"reply-{self.text_calls}"

    async def acomplete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        self.json_calls += 1
        return schema.model_validate({"x": self.json_calls})


async def test_records_then_replays_text(tmp_path) -> None:
    cassette = tmp_path / "c.json"
    rec = RecordedProvider(cassette, upstream=FakeLLMProvider(text="hello"))
    assert await rec.acomplete("sys", "usr") == "hello"
    assert cassette.exists()

    replay = RecordedProvider(cassette)  # no upstream → pure replay
    assert await replay.acomplete("sys", "usr") == "hello"


async def test_records_then_replays_json(tmp_path) -> None:
    cassette = tmp_path / "c.json"
    rec = RecordedProvider(cassette, upstream=FakeLLMProvider(payloads=[{"x": 9}]))
    out = await rec.acomplete_json("sys", "usr", _Out)
    assert isinstance(out, _Out) and out.x == 9

    replay = RecordedProvider(cassette)
    out2 = await replay.acomplete_json("sys", "usr", _Out)
    assert isinstance(out2, _Out) and out2.x == 9


async def test_record_mode_calls_upstream_only_once_per_prompt(tmp_path) -> None:
    upstream = _CountingProvider()
    rec = RecordedProvider(tmp_path / "c.json", upstream=upstream)
    a = await rec.acomplete("sys", "usr")
    b = await rec.acomplete("sys", "usr")
    assert a == b == "reply-1"
    assert upstream.text_calls == 1


async def test_distinct_prompts_recorded_separately(tmp_path) -> None:
    upstream = _CountingProvider()
    rec = RecordedProvider(tmp_path / "c.json", upstream=upstream)
    a = await rec.acomplete("sys", "one")
    b = await rec.acomplete("sys", "two")
    assert a == "reply-1" and b == "reply-2"
    assert upstream.text_calls == 2


async def test_replay_miss_raises(tmp_path) -> None:
    cassette = tmp_path / "c.json"
    cassette.write_text("{}", encoding="utf-8")
    replay = RecordedProvider(cassette)
    with pytest.raises(ProviderError):
        await replay.acomplete("sys", "unknown")


async def test_replay_missing_file_raises(tmp_path) -> None:
    replay = RecordedProvider(tmp_path / "does-not-exist.json")
    with pytest.raises(ProviderError):
        await replay.acomplete("sys", "usr")


async def test_text_and_json_keys_do_not_collide(tmp_path) -> None:
    cassette = tmp_path / "c.json"
    rec = RecordedProvider(
        cassette,
        upstream=FakeLLMProvider(text="as-text", payloads=[{"x": 1}]),
    )
    text = await rec.acomplete("sys", "usr")
    obj = await rec.acomplete_json("sys", "usr", _Out)
    assert text == "as-text"
    assert isinstance(obj, _Out) and obj.x == 1

    replay = RecordedProvider(cassette)
    assert await replay.acomplete("sys", "usr") == "as-text"
    assert (await replay.acomplete_json("sys", "usr", _Out)).x == 1


async def test_cassette_is_human_readable_json(tmp_path) -> None:
    cassette = tmp_path / "c.json"
    rec = RecordedProvider(cassette, upstream=FakeLLMProvider(text="hi"))
    await rec.acomplete("the-system", "the-user")
    data = json.loads(cassette.read_text(encoding="utf-8"))
    entries = list(data.values())
    assert len(entries) == 1
    assert entries[0]["system"] == "the-system"
    assert entries[0]["user"] == "the-user"
    assert entries[0]["response"] == "hi"
