"""AI extraction seam.

Signatures and the ``extract=`` parameter (on PersonaBuilder.add_image/add_audio)
land now; the model implementations are deferred to the extraction milestone and
raise NotImplementedError. Artifacts produced by extraction are labelled
status="gen".
"""

from pydantic import BaseModel

from persona_genesis.schema.biometrics import Body, Face, VoicePrint
from persona_genesis.schema.media import Audio, Image

_DEFERRED = "extraction is implemented in the extraction milestone (not yet wired)"


class AudioSegment(BaseModel):
    """A diarized speech segment (extraction-seam type, not persisted)."""

    text: str
    speaker: str | None = None
    start_s: float
    end_s: float


def extract_faces(image: Image | bytes) -> list[Face]:
    raise NotImplementedError(_DEFERRED)


def extract_body(image: Image | bytes) -> Body:
    raise NotImplementedError(_DEFERRED)


def describe_image(image: Image | bytes) -> str:
    raise NotImplementedError(_DEFERRED)


def score_nsfw(media: Image | Audio | bytes) -> float:
    raise NotImplementedError(_DEFERRED)


def transcribe(audio: Audio | bytes) -> list[AudioSegment]:
    raise NotImplementedError(_DEFERRED)


def extract_voice(segment: AudioSegment | bytes) -> VoicePrint:
    raise NotImplementedError(_DEFERRED)


def embed_text(text: str) -> list[float]:
    raise NotImplementedError(_DEFERRED)
