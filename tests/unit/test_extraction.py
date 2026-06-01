from collections.abc import Callable

import pytest

from persona_genesis import extraction


def test_audio_segment_shape() -> None:
    seg = extraction.AudioSegment(text="hi", speaker="A", start_s=0.0, end_s=1.0)
    assert seg.text == "hi"
    assert seg.speaker == "A"


@pytest.mark.parametrize(
    "call",
    [
        lambda: extraction.extract_faces(b"x"),
        lambda: extraction.extract_body(b"x"),
        lambda: extraction.describe_image(b"x"),
        lambda: extraction.score_nsfw(b"x"),
        lambda: extraction.transcribe(b"x"),
        lambda: extraction.extract_voice(b"x"),
        lambda: extraction.embed_text("x"),
    ],
)
def test_extraction_functions_deferred(call: Callable[[], object]) -> None:
    with pytest.raises(NotImplementedError):
        call()
