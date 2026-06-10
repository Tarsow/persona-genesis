"""The LLM's output schema — section content only, no _status fields."""

from pydantic import BaseModel, Field

from persona_genesis.schema.appearance import Build
from persona_genesis.schema.backstory import Education, LifeEvent
from persona_genesis.schema.personality import OceanScores


class PersonalityPayload(BaseModel):
    ocean: OceanScores
    traits: list[str]
    values: list[str]
    quirks: list[str]


class AppearancePayload(BaseModel):
    description: str
    hair_color: str
    hair_style: str
    eye_color: str
    build: Build
    height_cm: int = Field(gt=0, le=260)
    distinguishing_features: list[str]


class BackstoryPayload(BaseModel):
    bio: str
    education: list[Education]
    key_life_events: list[LifeEvent]


class VoicePayload(BaseModel):
    writing_style: str
    posting_cadence: str
    typical_topics: list[str]
    sample_paragraph: str


class NarrativePayload(BaseModel):
    personality: PersonalityPayload
    appearance: AppearancePayload
    backstory: BackstoryPayload
    voice: VoicePayload
