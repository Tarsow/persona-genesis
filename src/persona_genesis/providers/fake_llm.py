"""Offline LLMProvider double for tests and dev (no network)."""

from pydantic import BaseModel


class FakeLLMProvider:
    def __init__(
        self, *, payloads: list[BaseModel | dict[str, object]] | None = None, text: str = "ok"
    ) -> None:
        self.model = "fake"
        self._payloads = list(payloads or [])
        self._text = text
        self._i = 0

    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str:
        return self._text

    async def acomplete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        if not self._payloads:
            raise ValueError("FakeLLMProvider has no payloads configured")
        item = self._payloads[min(self._i, len(self._payloads) - 1)]
        self._i += 1
        return item if isinstance(item, schema) else schema.model_validate(item)
