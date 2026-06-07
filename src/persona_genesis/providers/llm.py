"""LLM provider protocol (narrative layer seam; no adapters yet)."""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class LLMProvider(Protocol):
    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str: ...

    async def acomplete_json(
        self, system: str, user: str, schema: type[BaseModel]
    ) -> BaseModel: ...
