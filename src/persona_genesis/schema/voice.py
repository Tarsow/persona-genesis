"""Voice sub-model: how the persona writes and posts online."""

from pydantic import BaseModel, Field

from persona_genesis.schema.status import Status


class Voice(BaseModel):
    writing_style: str
    writing_style_status: Status = "gen"
    posting_cadence: str
    posting_cadence_status: Status = "gen"
    typical_topics: list[str] = Field(default_factory=list)
    typical_topics_status: Status = "gen"
    sample_paragraph: str
    sample_paragraph_status: Status = "gen"
