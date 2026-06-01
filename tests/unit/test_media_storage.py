from pathlib import Path

from persona_genesis.media.storage import extension_for, store_media


def test_extension_for() -> None:
    assert extension_for("image/png") == ".png"
    assert extension_for("audio/wav") == ".wav"
    assert extension_for("video/mp4") == ".mp4"
    assert extension_for("application/x-weird") == ".bin"


def test_store_media_hashed_and_deduped(tmp_path: Path) -> None:
    a = store_media(b"hello", kind="image", media_type="image/png", media_dir=tmp_path)
    b = store_media(b"hello", kind="image", media_type="image/png", media_dir=tmp_path)
    assert a == b
    assert a.startswith("image/") and a.endswith(".png")
    assert (tmp_path / a).read_bytes() == b"hello"


def test_store_media_per_kind_subdir(tmp_path: Path) -> None:
    vid = store_media(b"x", kind="video", media_type="video/mp4", media_dir=tmp_path)
    assert vid.split("/")[0] == "video"
    assert (tmp_path / "video").is_dir()
