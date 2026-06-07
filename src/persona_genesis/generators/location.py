"""Location generation: bundled real-city dataset, or GeoIP from an `ip` constraint.
Status defaults to 'gen'."""

import random

from persona_genesis.data import load_locations
from persona_genesis.exceptions import ConfigError
from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.geo.base import GeoLocator
from persona_genesis.schema.location import Location


def generate_location(
    rng: random.Random, *, locale: str, geolocator: GeoLocator | None,
    constraints: StructuredConstraints,
) -> Location:
    if constraints.ip is not None:
        if geolocator is None:
            raise ConfigError("a GeoLocator is required to derive location from an ip")
        g = geolocator.locate(constraints.ip)
        return Location(country=g.country, region=g.region, city=g.city,
                        timezone=g.timezone, postal_code=g.postal_code, street=None)
    row = rng.choice(load_locations(locale))
    return Location(country=row["country"], region=row["region"], city=row["city"],
                    timezone=row["timezone"])
