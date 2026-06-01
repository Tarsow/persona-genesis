from persona_genesis.db.models import EmbeddingDims, build_models


def test_registry_tables_and_columns() -> None:
    reg = build_models(EmbeddingDims(face=8, body=8, voice=8, document=8))
    tables = set(reg.base.metadata.tables)
    assert {
        "personas", "faces", "bodies", "voices", "images", "audio", "video",
        "documents", "relationships", "accounts",
        "image_faces", "audio_voices", "document_personas",
    } <= tables

    persona_cols = set(reg.PersonaRow.__table__.columns.keys())
    for s in ("identity", "location", "contact", "work", "appearance",
              "personality", "voice", "device", "backstory", "metadata"):
        assert s in persona_cols

    assert {"login_enc", "password_enc", "session_token_enc"} <= set(
        reg.AccountRow.__table__.columns.keys()
    )
    assert "embedding" in reg.FaceRow.__table__.columns
    assert reg.FaceRow.__table__.columns["persona_id"].nullable is True
    assert reg.BodyRow.__table__.columns["persona_id"].nullable is False
