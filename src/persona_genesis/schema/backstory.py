"""Backstory sub-model: bio, education history and key life events."""

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status


class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_year: int
    end_year: int | None = None


class LifeEvent(BaseModel):
    year: int
    description: str


class Backstory(BaseModel):
    bio: str
    bio_status: Status = "gen"
    education: list[Education] = Field(default_factory=list)
    education_status: Status = "gen"
    key_life_events: list[LifeEvent] = Field(default_factory=list)
    key_life_events_status: Status = "gen"
