"""Image provider protocol (visual layer seam; no adapters yet)."""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from PIL.Image import Image


@runtime_checkable
class ImageProvider(Protocol):
    async def agenerate(
        self, prompt: str, *, aspect: str = "1:1", seed: int | None = None
    ) -> "Image": ...
