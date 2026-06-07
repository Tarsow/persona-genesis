import random
from datetime import date

from faker import Faker

from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.generators.identity import generate_identity


def _faker(seed: int) -> Faker:
    f = Faker("en_US")
    f.seed_instance(seed)
    return f


def test_identity_respects_gender_and_age_and_nationality() -> None:
    c = StructuredConstraints(age_range=(30, 40), gender="female")
    i = generate_identity(_faker(1), random.Random(1), nationality="US", constraints=c)
    assert i.gender == "female"
    assert i.nationality == "US"
    age = date.today().year - i.dob.year - (
        (date.today().month, date.today().day) < (i.dob.month, i.dob.day)
    )
    assert 30 <= age <= 40
    assert i.full_name == f"{i.given_name} {i.family_name}"
    assert i.full_name_status == "fake"


def test_identity_deterministic() -> None:
    c = StructuredConstraints()
    a = generate_identity(_faker(7), random.Random(7), nationality="US", constraints=c)
    b = generate_identity(_faker(7), random.Random(7), nationality="US", constraints=c)
    assert a == b
