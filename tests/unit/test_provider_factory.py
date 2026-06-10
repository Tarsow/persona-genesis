import pytest

from persona_genesis.config import Config
from persona_genesis.exceptions import ConfigError
from persona_genesis.providers.factory import build_llm_provider
from persona_genesis.providers.openai_compat import OpenAICompatProvider


def test_deepseek_default_base_url() -> None:
    cfg = Config.from_dict({"llm": {"provider": "deepseek", "api_key": "k"}})
    p = build_llm_provider(cfg)
    assert isinstance(p, OpenAICompatProvider)
    assert p.model == "deepseek-chat"


def test_missing_api_key_raises() -> None:
    cfg = Config.from_dict({"llm": {"provider": "deepseek", "api_key": None}})
    with pytest.raises(ConfigError):
        build_llm_provider(cfg)


def test_anthropic_not_supported() -> None:
    cfg = Config.from_dict({"llm": {"provider": "anthropic", "api_key": "k"}})
    with pytest.raises(ConfigError):
        build_llm_provider(cfg)


def test_openai_compat_requires_base_url() -> None:
    cfg = Config.from_dict({"llm": {"provider": "openai_compat", "api_key": "k"}})
    with pytest.raises(ConfigError):
        build_llm_provider(cfg)
