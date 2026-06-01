from datetime import date

from persona_genesis.schema.identity import Identity


def test_identity_round_trips() -> None:
    ident = Identity(
        full_name="Ana Souza",
        given_name="Ana",
        family_name="Souza",
        gender="female",
        dob=date(1994, 3, 12),
        nationality="BR",
    )
    dumped = ident.model_dump_json()
    restored = Identity.model_validate_json(dumped)
    assert restored == ident
    assert restored.dob == date(1994, 3, 12)
