from persona_genesis.schema.draft import PersonaDraft
from persona_genesis.schema.partial import PartialPersona


def test_draft_defaults_empty() -> None:
    d = PersonaDraft(persona=PartialPersona(locale="pt_BR"))
    assert d.faces == []
    assert d.images == []
    assert d.accounts == []
    assert d.relationships == []
    assert d.image_face_links == []
    assert d.persona.locale == "pt_BR"
