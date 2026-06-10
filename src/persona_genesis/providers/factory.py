"""Build an LLMProvider from Config (no env reading; values come from Config)."""

from persona_genesis.config import Config
from persona_genesis.exceptions import ConfigError
from persona_genesis.providers.llm import LLMProvider
from persona_genesis.providers.openai_compat import OpenAICompatProvider

_DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com/v1",
}


def build_llm_provider(config: Config) -> LLMProvider:
    llm = config.llm
    if llm.provider in ("deepseek", "openai", "openai_compat"):
        base_url = llm.base_url or _DEFAULT_BASE_URLS.get(llm.provider)
        if not base_url:
            raise ConfigError("base_url is required for the openai_compat provider")
        if not llm.api_key:
            raise ConfigError("api_key is required for the LLM provider")
        return OpenAICompatProvider(
            api_key=llm.api_key, model=llm.model, base_url=base_url,
            timeout_s=llm.timeout_s, max_retries=llm.max_retries,
        )
    raise ConfigError(f"LLM provider {llm.provider!r} is not yet supported")
