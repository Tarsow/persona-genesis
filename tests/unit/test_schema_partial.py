from persona_genesis.schema.partial import PartialPersona


def test_partial_all_optional() -> None:
    p = PartialPersona()
    assert p.identity is None
    assert p.metadata is None
    assert p.id is not None


def test_partial_round_trips() -> None:
    p = PartialPersona(locale="pt_BR", seed=1)
    assert PartialPersona.model_validate_json(p.model_dump_json()) == p
