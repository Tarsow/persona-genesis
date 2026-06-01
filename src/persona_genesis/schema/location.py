"""Location sub-model. Coarse fields auto-generated; precise address (real, from IP) optional."""

from pydantic import BaseModel

from persona_genesis.schema.status import Status


class Location(BaseModel):
    country: str
    country_status: Status = "gen"
    region: str
    region_status: Status = "gen"
    city: str
    city_status: Status = "gen"
    timezone: str
    timezone_status: Status = "gen"
    street: str | None = None
    street_status: Status = "gen"
    postal_code: str | None = None
    postal_code_status: Status = "gen"
