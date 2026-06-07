"""geoip2-backed GeoLocator. Lazy-imports geoip2 so the [geoip] extra is optional.
The GeoLite2-City .mmdb is MaxMind-licensed and supplied by the caller."""

from persona_genesis.exceptions import PersonaGenerationError
from persona_genesis.geo.base import GeoLocation


class GeoIP2Locator:
    def __init__(self, database_path: str) -> None:
        self._database_path = database_path

    def locate(self, ip: str) -> GeoLocation:
        try:
            import geoip2.database
            import geoip2.errors
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise PersonaGenerationError(
                "geoip2 is required for ip-based location; install the [geoip] extra"
            ) from exc
        try:
            with geoip2.database.Reader(self._database_path) as reader:
                r = reader.city(ip)
        except FileNotFoundError as exc:
            raise PersonaGenerationError(
                f"GeoLite2 database not found: {self._database_path}"
            ) from exc
        except geoip2.errors.AddressNotFoundError as exc:
            raise PersonaGenerationError(f"ip not found in GeoLite2 database: {ip}") from exc
        if r.country.iso_code is None or r.location.time_zone is None:
            raise PersonaGenerationError(f"incomplete GeoLite2 record for ip: {ip}")
        return GeoLocation(
            country=r.country.iso_code,
            region=r.subdivisions.most_specific.name or "",
            city=r.city.name or "",
            timezone=r.location.time_zone,
            postal_code=r.postal.code,
        )
