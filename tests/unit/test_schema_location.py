from persona_genesis.schema.location import Location


def test_location_precise_address_optional_with_gen_status() -> None:
    loc = Location(country="BR", region="SP", city="Campinas", timezone="America/Sao_Paulo")
    assert loc.street is None
    assert loc.postal_code is None
    assert loc.country_status == "gen"
    assert loc.street_status == "gen"


def test_location_round_trips() -> None:
    loc = Location(
        country="BR", region="SP", city="Campinas",
        street="Rua das Flores, 123", postal_code="13010-000",
        timezone="America/Sao_Paulo",
    )
    restored = Location.model_validate_json(loc.model_dump_json())
    assert restored == loc
