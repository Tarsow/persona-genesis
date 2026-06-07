from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.generators.structured import SUPPORTED_LOCALES, StructuredGenerator


def test_generates_four_sections_deterministically() -> None:
    g = StructuredGenerator()
    a = g.generate(42, "pt_BR", StructuredConstraints())
    b = g.generate(42, "pt_BR", StructuredConstraints())
    assert set(a) == {"identity", "location", "work", "device"}
    assert a["identity"] == b["identity"]
    assert a["location"].country == "BR"
    assert a["device"] == b["device"]


def test_supported_locales() -> None:
    assert {"en_US", "pt_BR"} <= SUPPORTED_LOCALES
