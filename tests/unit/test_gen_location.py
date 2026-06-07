import random

import pytest

from persona_genesis.exceptions import ConfigError
from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.generators.location import generate_location
from persona_genesis.geo.base import GeoLocation


def test_location_from_dataset_is_coherent() -> None:
    loc = generate_location(random.Random(1), locale="pt_BR", geolocator=None,
                            constraints=StructuredConstraints())
    assert loc.country == "BR"
    assert loc.street is None and loc.postal_code is None
    assert loc.country_status == "gen"


def test_location_from_ip_uses_locator_and_no_street() -> None:
    class Fake:
        def locate(self, ip: str) -> GeoLocation:
            return GeoLocation(country="US", region="California", city="San Francisco",
                               timezone="America/Los_Angeles", postal_code="94103")

    loc = generate_location(random.Random(1), locale="en_US", geolocator=Fake(),
                            constraints=StructuredConstraints(ip="8.8.8.8"))
    assert (loc.city, loc.postal_code) == ("San Francisco", "94103")
    assert loc.street is None


def test_ip_without_locator_raises() -> None:
    with pytest.raises(ConfigError):
        generate_location(random.Random(1), locale="en_US", geolocator=None,
                          constraints=StructuredConstraints(ip="8.8.8.8"))
