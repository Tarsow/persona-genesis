"""Content-hashed media writer: media_dir/<kind>/<sha256-hex><ext>."""

import hashlib
from pathlib import Path

_EXTENSIONS: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}
_FALLBACK_EXT = ".bin"


def extension_for(media_type: str) -> str:
    return _EXTENSIONS.get(media_type.lower().strip(), _FALLBACK_EXT)


def store_media(data: bytes, *, kind: str, media_type: str, media_dir: str | Path) -> str:
    digest = hashlib.sha256(data).hexdigest()
    rel = f"{kind}/{digest}{extension_for(media_type)}"
    dest = Path(media_dir) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return rel
