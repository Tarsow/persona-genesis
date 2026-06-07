"""Work generation: curated occupation/industry + Faker employer + age-coherent
seniority. Status defaults to 'fake'."""

import random

from faker import Faker

from persona_genesis.data import load_occupations
from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.schema.work import Schedule, Seniority, Work

_MIN_YEARS: dict[Seniority, int] = {
    "intern": 0, "junior": 0, "mid": 3, "senior": 7,
    "lead": 10, "manager": 8, "director": 15, "executive": 20,
}
_SCHEDULES: list[Schedule] = ["full_time", "part_time", "contract", "freelance", "shift", "remote"]


def generate_work(
    faker: Faker, rng: random.Random, *, age: int, constraints: StructuredConstraints
) -> Work:
    occ = rng.choice(load_occupations())
    employer = faker.company()
    if constraints.seniority is not None:
        seniority: Seniority = constraints.seniority
    else:
        years = max(0, age - 22)
        eligible = [s for s, m in _MIN_YEARS.items() if m <= years]
        seniority = rng.choice(eligible)
    schedule = rng.choice(_SCHEDULES)
    return Work(occupation=occ["occupation"], employer=employer, seniority=seniority,
                industry=occ["industry"], schedule=schedule)
