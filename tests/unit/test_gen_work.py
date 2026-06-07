import random

from faker import Faker

from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.generators.work import generate_work


def _faker(seed: int) -> Faker:
    f = Faker("en_US")
    f.seed_instance(seed)
    return f


def test_young_person_never_senior_role() -> None:
    seen = set()
    for seed in range(40):
        w = generate_work(_faker(seed), random.Random(seed), age=22,
                          constraints=StructuredConstraints())
        seen.add(w.seniority)
    assert seen <= {"intern", "junior"}


def test_occupation_industry_paired_and_status_fake() -> None:
    w = generate_work(_faker(3), random.Random(3), age=40, constraints=StructuredConstraints())
    assert w.occupation and w.industry
    assert w.occupation_status == "fake"


def test_seniority_constraint_honored() -> None:
    w = generate_work(_faker(3), random.Random(3), age=40,
                      constraints=StructuredConstraints(seniority="director"))
    assert w.seniority == "director"
