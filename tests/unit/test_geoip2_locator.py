import pytest

from persona_genesis.exceptions import PersonaGenesisError


def test_missing_db_raises() -> None:
    from persona_genesis.geo.geoip2_locator import GeoIP2Locator

    with pytest.raises(PersonaGenesisError):
        GeoIP2Locator("/nonexistent/GeoLite2-City.mmdb").locate("8.8.8.8")
