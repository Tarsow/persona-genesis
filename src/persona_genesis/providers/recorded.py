"""Record-once / replay LLMProvider: snapshot real LLM exchanges to a JSON
cassette so the full generation path is testable offline, deterministically,
with no per-run API cost.

- ``upstream`` set   → record: forward to the real provider on a cassette miss,
  persist the exchange, and reuse it thereafter.
- ``upstream`` None  → replay: serve recorded responses only; a miss raises
  ``ProviderError``.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from persona_genesis.exceptions import ProviderError
from persona_genesis.providers.llm import LLMProvider

_LABEL = "recorded"


class RecordedProvider:
    def __init__(self, path: Path | str, *, upstream: LLMProvider | None = None) -> None:
        self.model = "recorded"
        self._path = Path(path)
        self._upstream = upstream
        self._entries = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        data: dict[str, dict[str, Any]] = json.loads(self._path.read_text(encoding="utf-8"))
        return data

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._entries, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

    @staticmethod
    def _key(kind: str, system: str, user: str, schema: str = "") -> str:
        digest = hashlib.sha256("\0".join((kind, system, user, schema)).encode("utf-8"))
        return digest.hexdigest()

    def _replay_miss(self, system: str, user: str) -> ProviderError:
        return ProviderError(_LABEL, f"no recording for prompt (system={system!r}, user={user!r})")

    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str:
        key = self._key("text", system, user)
        entry = self._entries.get(key)
        if entry is not None:
            return str(entry["response"])
        if self._upstream is None:
            raise self._replay_miss(system, user)
        response = await self._upstream.acomplete(system, user, temperature=temperature)
        self._entries[key] = {"kind": "text", "system": system, "user": user, "response": response}
        self._save()
        return response

    async def acomplete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        key = self._key("json", system, user, schema.__name__)
        entry = self._entries.get(key)
        if entry is not None:
            return schema.model_validate(entry["response"])
        if self._upstream is None:
            raise self._replay_miss(system, user)
        result = await self._upstream.acomplete_json(system, user, schema)
        self._entries[key] = {
            "kind": "json",
            "system": system,
            "user": user,
            "schema": schema.__name__,
            "response": result.model_dump(mode="json"),
        }
        self._save()
        return result
