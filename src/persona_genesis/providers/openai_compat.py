"""OpenAI-compatible chat-completions provider (raw httpx). Default target: DeepSeek.
Works with OpenAI, Ollama, OpenRouter, vLLM via base_url."""

import json
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from persona_genesis.exceptions import ProviderError

_LABEL = "openai_compat"


class OpenAICompatProvider:
    def __init__(
        self, *, api_key: str, model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com", timeout_s: int = 60,
        max_retries: int = 2, http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._client = http_client

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        client = self._client or httpx.AsyncClient(timeout=self._timeout_s)
        try:
            resp = await client.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderError(_LABEL, f"request failed: {exc}") from exc
        finally:
            if self._client is None:
                await client.aclose()
        if resp.status_code >= 400:
            raise ProviderError(_LABEL, f"HTTP {resp.status_code}: {resp.text}")
        data: dict[str, Any] = resp.json()
        return data

    def _content(self, data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(_LABEL, f"unexpected response shape: {data}") from exc
        if not isinstance(content, str):
            raise ProviderError(_LABEL, "response content was not a string")
        return content

    async def acomplete(self, system: str, user: str, *, temperature: float = 0.7) -> str:
        data = await self._post({
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
        })
        return self._content(data)

    async def acomplete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        sys = (
            f"{system}\n\nRespond ONLY with a single JSON object matching this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        last_err = ""
        for attempt in range(self._max_retries + 1):
            u = user if attempt == 0 else (
                f"{user}\n\nYour previous response was invalid ({last_err}). "
                "Return ONLY valid JSON matching the schema."
            )
            data = await self._post({
                "model": self.model,
                "messages": [{"role": "system", "content": sys}, {"role": "user", "content": u}],
                "response_format": {"type": "json_object"},
            })
            content = self._content(data)
            try:
                return schema.model_validate(json.loads(content))
            except (json.JSONDecodeError, ValidationError) as exc:
                last_err = str(exc)[:200]
        raise ProviderError(
            _LABEL, f"no valid JSON after {self._max_retries + 1} attempts: {last_err}"
        )
