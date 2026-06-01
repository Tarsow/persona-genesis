from uuid import UUID

from persona_genesis.schema import Persona


def test_persona_has_generated_uuid(sample_persona: Persona) -> None:
    assert isinstance(sample_persona.id, UUID)
    assert not hasattr(sample_persona, "media")
    assert not hasattr(sample_persona, "images")


def test_persona_round_trips(sample_persona: Persona) -> None:
    restored = Persona.model_validate_json(sample_persona.model_dump_json())
    assert restored == sample_persona


def test_persona_carries_status_defaults(sample_persona: Persona) -> None:
    assert sample_persona.identity.full_name_status == "fake"
    assert sample_persona.location.country_status == "gen"
    assert sample_persona.contact.email_status == "fake"
