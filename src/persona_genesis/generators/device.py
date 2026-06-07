"""Device generation from the curated ua_pool. Status defaults to 'fake'."""

import random

from persona_genesis.data import load_ua_pool
from persona_genesis.exceptions import PersonaGenerationError
from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.schema.device import Device


def generate_device(rng: random.Random, *, constraints: StructuredConstraints) -> Device:
    pool = load_ua_pool()
    if constraints.device_type is not None:
        pool = [p for p in pool if p["device"] == constraints.device_type]
        if not pool:
            raise PersonaGenerationError(
                f"no ua_pool profile for device {constraints.device_type!r}"
            )
    profile = rng.choice(pool)
    resolution = rng.choice(profile["resolutions"])
    return Device(primary_device=profile["device"], os=profile["os"], browser=profile["browser"],
                  user_agent=profile["ua"], screen_resolution=resolution)
