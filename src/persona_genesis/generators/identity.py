"""Identity generation (Faker, locale-aware). Status defaults to 'fake'."""

import random

from faker import Faker

from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.schema.identity import Identity


def generate_identity(
    faker: Faker, rng: random.Random, *, nationality: str, constraints: StructuredConstraints
) -> Identity:
    gender = constraints.gender or rng.choice(["male", "female", "non_binary"])
    if gender == "male":
        given = faker.first_name_male()
    elif gender == "female":
        given = faker.first_name_female()
    else:
        given = faker.first_name()
    family = faker.last_name()
    lo, hi = constraints.age_range
    dob = faker.date_of_birth(minimum_age=lo, maximum_age=hi)
    return Identity(
        full_name=f"{given} {family}", given_name=given, family_name=family,
        gender=gender, dob=dob, nationality=nationality,
    )
