"""Personality sub-model: OCEAN scores plus descriptive traits."""

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status


class OceanScores(BaseModel):
    """Big Five scores, each normalized to [0, 1]."""

    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)


class Personality(BaseModel):
    ocean: OceanScores
    ocean_status: Status = "gen"
    traits: list[str] = Field(default_factory=list)
    traits_status: Status = "gen"
    values: list[str] = Field(default_factory=list)
    values_status: Status = "gen"
    quirks: list[str] = Field(default_factory=list)
    quirks_status: Status = "gen"
