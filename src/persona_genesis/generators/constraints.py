"""Inputs to the structured generation layer."""

from pydantic import BaseModel

from persona_genesis.schema.device import DeviceType
from persona_genesis.schema.identity import Gender
from persona_genesis.schema.work import Seniority


class StructuredConstraints(BaseModel):
    age_range: tuple[int, int] = (18, 75)
    gender: Gender | None = None
    seniority: Seniority | None = None
    device_type: DeviceType | None = None
    ip: str | None = None
