"""GeoLocation value model + GeoLocator protocol."""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class GeoLocation(BaseModel):
    country: str            # ISO 3166-1 alpha-2
    region: str
    city: str
    timezone: str           # IANA
    postal_code: str | None = None


@runtime_checkable
class GeoLocator(Protocol):
    def locate(self, ip: str) -> GeoLocation: ...
