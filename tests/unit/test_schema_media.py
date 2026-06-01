import json

import pytest
from pydantic import ValidationError

from persona_genesis.schema.media import Audio, Image, MediaOrigin, Video


def test_ai_origin_requires_provider_and_model() -> None:
    with pytest.raises(ValidationError):
        MediaOrigin(source="ai_generated", provider="fal")
    MediaOrigin(source="ai_generated", provider="fal", model="flux")
    MediaOrigin(source="caller_supplied")


def test_image_defaults_and_unknown_type() -> None:
    img = Image(file_path="image/h.png", media_type="image/png", type="unknown")
    assert img.nsfw == 0.0
    assert img.status == "gen"
    assert img.description is None


def test_nsfw_bounds() -> None:
    with pytest.raises(ValidationError):
        Image(file_path="x", media_type="image/png", type="face", nsfw=1.5)


def test_audio_video_round_trip_no_binary() -> None:
    a = Audio(file_path="audio/h.wav", media_type="audio/wav", type="voice_sample", text="hi")
    v = Video(file_path="video/h.mp4", media_type="video/mp4", type="unknown", fps=30.0)
    assert json.loads(a.model_dump_json())["text"] == "hi"
    assert Audio.model_validate_json(a.model_dump_json()) == a
    assert Video.model_validate_json(v.model_dump_json()) == v
