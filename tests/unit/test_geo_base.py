from persona_genesis.geo.base import GeoLocation, GeoLocator


def test_geolocation_round_trip() -> None:
    g = GeoLocation(country="BR", region="São Paulo", city="Campinas",
                    timezone="America/Sao_Paulo", postal_code="13010-000")
    assert GeoLocation.model_validate_json(g.model_dump_json()) == g


def test_geolocator_protocol() -> None:
    class Fake:
        def locate(self, ip: str) -> GeoLocation:
            return GeoLocation(country="US", region="CA", city="SF", timezone="America/Los_Angeles")

    assert isinstance(Fake(), GeoLocator)
