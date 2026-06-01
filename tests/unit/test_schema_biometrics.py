from uuid import uuid4

from persona_genesis.schema.biometrics import Body, Face, VoicePrint


def test_face_optional_persona_and_round_trip() -> None:
    f = Face(embedding=[0.1, 0.2, 0.3])
    assert f.persona_id is None
    assert f.status == "gen"
    assert Face.model_validate_json(f.model_dump_json()) == f


def test_body_and_voiceprint_require_persona() -> None:
    pid = uuid4()
    b = Body(persona_id=pid, embedding=[0.0, 1.0])
    vp = VoicePrint(persona_id=pid, embedding=[0.5], label="calm")
    assert b.persona_id == pid
    assert vp.label == "calm"
    assert VoicePrint.model_validate_json(vp.model_dump_json()) == vp
