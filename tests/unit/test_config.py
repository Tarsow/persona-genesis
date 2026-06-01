import pytest

from persona_genesis.config import Config, ImageConfig, LLMConfig
from persona_genesis.exceptions import ConfigError


def test_defaults_match_spec() -> None:
    cfg = Config()
    assert cfg.llm.provider == "anthropic"
    assert cfg.llm.model == "claude-opus-4-7"
    assert cfg.image.provider == "fal"
    assert cfg.image.model == "fal-ai/flux/schnell"
    assert cfg.default_locale == "en_US"


def test_explicit_construction() -> None:
    cfg = Config(
        llm=LLMConfig(provider="openai", api_key="sk-x", model="gpt-4o"),
        image=ImageConfig(provider="replicate", api_key="r8-x"),
        default_locale="pt_BR",
    )
    assert cfg.llm.provider == "openai"
    assert cfg.default_locale == "pt_BR"


def test_from_dict_reads_nested_keys() -> None:
    cfg = Config.from_dict(
        {
            "llm": {
                "provider": "openai",
                "api_key": "sk-fromdict",
                "model": "gpt-4o",
                "timeout_s": 30,
            },
            "image": {"provider": "fal", "api_key": "fal-key"},
            "default_locale": "pt_BR",
        }
    )
    assert cfg.llm.provider == "openai"
    assert cfg.llm.api_key == "sk-fromdict"
    assert cfg.llm.model == "gpt-4o"
    assert cfg.llm.timeout_s == 30
    assert cfg.image.provider == "fal"
    assert cfg.image.api_key == "fal-key"
    assert cfg.default_locale == "pt_BR"


def test_from_dict_empty_uses_defaults() -> None:
    cfg = Config.from_dict({})
    assert cfg.llm.provider == "anthropic"
    assert cfg.image.provider == "fal"
    assert cfg.default_locale == "en_US"


def test_from_dict_ignores_unknown_keys() -> None:
    cfg = Config.from_dict(
        {
            "llm": {"provider": "openai", "unknown_nested": "ignored"},
            "totally_unknown": {"x": 1},
        }
    )
    assert cfg.llm.provider == "openai"
    assert not hasattr(cfg, "totally_unknown")


def test_from_dict_raises_config_error_on_bad_value() -> None:
    with pytest.raises(ConfigError):
        Config.from_dict({"llm": {"timeout_s": "not-an-int"}})


def test_from_dict_raises_config_error_on_bad_provider() -> None:
    with pytest.raises(ConfigError):
        Config.from_dict({"llm": {"provider": "not-a-provider"}})


def test_config_persistence_and_embedding_dims() -> None:
    cfg = Config()
    assert cfg.database_url is None
    assert cfg.vault_key is None
    assert cfg.media_dir == "/srv/persona-genesis/media/"
    assert cfg.face_embedding_dim == 512
    assert cfg.body_embedding_dim == 2048
    assert cfg.voice_embedding_dim == 192
    assert cfg.document_embedding_dim == 1536


def test_config_dims_from_dict() -> None:
    cfg = Config.from_dict({"face_embedding_dim": 256, "media_dir": "/tmp/m"})
    assert cfg.face_embedding_dim == 256
    assert cfg.media_dir == "/tmp/m"
