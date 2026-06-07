"""Composes the section generators into the structured half of a persona."""

import random
from datetime import date
from typing import Any

from faker import Faker

from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.generators.device import generate_device
from persona_genesis.generators.identity import generate_identity
from persona_genesis.generators.location import generate_location
from persona_genesis.generators.work import generate_work
from persona_genesis.geo.base import GeoLocator

_LOCALES: dict[str, dict[str, str]] = {
    "en_US": {"faker": "en_US", "country": "US"},
    "pt_BR": {"faker": "pt_BR", "country": "BR"},
}
SUPPORTED_LOCALES = frozenset(_LOCALES)


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class StructuredGenerator:
    def __init__(self, *, geolocator: GeoLocator | None = None) -> None:
        self._geolocator = geolocator

    def generate(
        self, seed: int, locale: str, constraints: StructuredConstraints
    ) -> dict[str, Any]:
        meta = _LOCALES[locale]
        faker = Faker(meta["faker"])
        faker.seed_instance(seed)
        rng = random.Random(seed)
        identity = generate_identity(
            faker, rng, nationality=meta["country"], constraints=constraints
        )
        location = generate_location(rng, locale=locale, geolocator=self._geolocator,
                                     constraints=constraints)
        work = generate_work(faker, rng, age=_age(identity.dob), constraints=constraints)
        device = generate_device(rng, constraints=constraints)
        return {"identity": identity, "location": location, "work": work, "device": device}
