"""Identity sub-model."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from persona_genesis.schema.status import Status

Gender = Literal["male", "female", "non_binary"]


class Identity(BaseModel):
    full_name: str
    full_name_status: Status = "fake"
    given_name: str
    given_name_status: Status = "fake"
    family_name: str
    family_name_status: Status = "fake"
    gender: Gender
    gender_status: Status = "fake"
    dob: date
    dob_status: Status = "fake"
    nationality: str  # ISO 3166-1 alpha-2
    nationality_status: Status = "fake"
