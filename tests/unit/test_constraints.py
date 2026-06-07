from persona_genesis.generators.constraints import StructuredConstraints


def test_defaults() -> None:
    c = StructuredConstraints()
    assert c.age_range == (18, 75)
    assert c.gender is None and c.seniority is None
    assert c.device_type is None and c.ip is None


def test_overrides() -> None:
    c = StructuredConstraints(age_range=(25, 35), gender="female", device_type="smartphone")
    assert c.age_range == (25, 35)
    assert c.gender == "female"
