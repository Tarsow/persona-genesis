"""Work sub-model."""

from typing import Literal

from pydantic import BaseModel

from persona_genesis.schema.status import Status

Seniority = Literal[
    "intern", "junior", "mid", "senior", "lead", "manager", "director", "executive",
]
Schedule = Literal["full_time", "part_time", "contract", "freelance", "shift", "remote"]


class Work(BaseModel):
    occupation: str
    occupation_status: Status = "fake"
    employer: str
    employer_status: Status = "fake"
    seniority: Seniority
    seniority_status: Status = "fake"
    industry: str
    industry_status: Status = "fake"
    schedule: Schedule
    schedule_status: Status = "fake"
