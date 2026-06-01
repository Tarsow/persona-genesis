from pathlib import Path

import pytest
from PIL import Image as PILImage
from pydantic import ValidationError

from persona_genesis.builder import PersonaBuilder
from persona_genesis.schema.draft import PersonaDraft


def test_empty_builder_missing_all_core_sections() -> None:
    b = PersonaBuilder(locale="pt_BR", seed=42)
    assert b.missing() == {
        "identity", "location", "contact", "work", "appearance",
        "personality", "voice", "device", "backstory",
    }
    assert isinstance(b.build(), PersonaDraft)


def test_set_merges_and_marks_real() -> None:
    b = PersonaBuilder()
    b.set(identity={"given_name": "Ana", "gender": "female"})
    b.set(identity={"family_name": "Souza"})
    partial = b.build().persona
    assert partial.identity is not None
    assert partial.identity.given_name == "Ana"
    assert partial.identity.family_name == "Souza"
    assert partial.identity.given_name_status == "real"
    assert partial.identity.gender_status == "real"
    assert "identity" not in b.missing()


def test_set_status_override() -> None:
    b = PersonaBuilder()
    b.set(identity={"given_name": "Ana", "given_name_status": "gen"})
    identity = b.build().persona.identity
    assert identity is not None
    assert identity.given_name_status == "gen"


def test_set_validation_error_propagates() -> None:
    b = PersonaBuilder()
    with pytest.raises(ValidationError):
        b.set(identity={"gender": "bad"})


def test_add_image_pil_writes_and_links(tmp_path: Path) -> None:
    b = PersonaBuilder(media_dir=tmp_path)
    face = b.add_face(embedding=[0.1, 0.2])
    img = b.add_image(PILImage.new("RGB", (16, 24), "white"), type="face", link_faces=[face])
    assert img.media_type == "image/png"
    assert img.width == 16 and img.height == 24
    assert img.status == "real"
    assert (tmp_path / img.file_path).is_file()
    assert img.origin is not None
    assert img.origin.source == "caller_supplied"
    draft = b.build()
    assert draft.images == [img]
    assert draft.faces == [face]
    assert draft.image_face_links == [(img.id, face.id)]


def test_add_image_bytes_requires_media_type(tmp_path: Path) -> None:
    b = PersonaBuilder(media_dir=tmp_path)
    with pytest.raises(ValueError):
        b.add_image(b"\x00", type="other")


def test_add_audio_voice_document_account_relationship(tmp_path: Path) -> None:
    b = PersonaBuilder(media_dir=tmp_path)
    voice = b.add_voice(embedding=[0.3])
    audio = b.add_audio(data=b"RIFF", media_type="audio/wav", type="voice_sample",
                        link_voices=[voice])
    doc = b.add_document(content="event", embedding=[0.1])
    acc = b.add_account(url="https://m", login="u", password="p")
    from uuid import uuid4
    rel = b.add_relationship(other_persona_id=uuid4(), relationship="friend")
    draft = b.build()
    assert (tmp_path / audio.file_path).is_file()
    assert draft.audio_voice_links == [(audio.id, voice.id)]
    assert draft.documents == [doc]
    assert draft.accounts == [acc]
    assert draft.relationships == [rel]
    assert acc.persona_id == draft.persona.id
    assert rel.person_1_id == draft.persona.id
    assert draft.document_persona_links == [(doc.id, draft.persona.id)]


def test_extract_true_without_provider_raises(tmp_path: Path) -> None:
    b = PersonaBuilder(media_dir=tmp_path)
    with pytest.raises(NotImplementedError):
        b.add_image(PILImage.new("RGB", (8, 8), "white"), type="face", extract=True)


def test_set_coerces_nested_model_fields() -> None:
    from persona_genesis.schema.personality import OceanScores

    b = PersonaBuilder()
    b.set(personality={"ocean": {"openness": 0.5, "conscientiousness": 0.5,
                                 "extraversion": 0.5, "agreeableness": 0.5,
                                 "neuroticism": 0.5}})
    personality = b.build().persona.personality
    assert personality is not None
    assert isinstance(personality.ocean, OceanScores)
    assert personality.ocean.openness == 0.5
    assert personality.ocean_status == "real"


def test_set_status_only_does_not_satisfy_missing() -> None:
    b = PersonaBuilder()
    b.set_status("identity", "given_name", "gen")
    assert "identity" in b.missing()


def test_add_audio_extract_true_without_provider_raises(tmp_path: Path) -> None:
    b = PersonaBuilder(media_dir=tmp_path)
    with pytest.raises(NotImplementedError):
        b.add_audio(data=b"RIFF", media_type="audio/wav", type="voice_sample", extract=True)
