"""Appearance sub-model: narrative description plus structured attributes."""

from typing import Literal

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status

Build = Literal["slim", "average", "athletic", "muscular", "heavy"]


class Appearance(BaseModel):
    description: str
    description_status: Status = "gen"
    hair_color: str
    hair_color_status: Status = "fake"
    hair_style: str
    hair_style_status: Status = "fake"
    eye_color: str
    eye_color_status: Status = "fake"
    build: Build
    build_status: Status = "fake"
    height_cm: int = Field(gt=0, le=260)
    height_cm_status: Status = "fake"
    distinguishing_features: list[str] = Field(default_factory=list)
    distinguishing_features_status: Status = "fake"
