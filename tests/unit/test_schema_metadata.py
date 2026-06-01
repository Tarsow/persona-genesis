from datetime import UTC, datetime

from persona_genesis.schema.metadata import PersonaMetadata


def test_metadata_round_trips() -> None:
    meta = PersonaMetadata(
        generated_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        generator_version="0.1.0",
        provider_versions={"llm": "anthropic:claude-opus-4-7", "image": "fal:flux-schnell"},
    )
    restored = PersonaMetadata.model_validate_json(meta.model_dump_json())
    assert restored == meta


def test_metadata_provider_versions_default_empty() -> None:
    meta = PersonaMetadata(
        generated_at=datetime(2026, 6, 1, tzinfo=UTC),
        generator_version="0.1.0",
    )
    assert meta.provider_versions == {}
