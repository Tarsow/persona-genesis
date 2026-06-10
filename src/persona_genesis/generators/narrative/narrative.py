"""Build the narrative prompt, call the LLM for a NarrativePayload, map to sections."""

from datetime import date
from functools import lru_cache
from importlib.resources import files
from typing import Any

from persona_genesis.generators.narrative.payload import NarrativePayload
from persona_genesis.providers.llm import LLMProvider
from persona_genesis.schema.appearance import Appearance
from persona_genesis.schema.backstory import Backstory
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.personality import Personality
from persona_genesis.schema.voice import Voice


@lru_cache
def _system_prompt() -> str:
    return (files("persona_genesis.prompts") / "narrative.md").read_text(encoding="utf-8")


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _user_prompt(partial: PartialPersona, violations: list[str] | None) -> str:
    i, loc, w = partial.identity, partial.location, partial.work
    assert i is not None and loc is not None and w is not None
    lines = [
        "Generate personality, appearance, backstory, and voice for this person:",
        f"Locale: {partial.locale}",
        f"Name: {i.full_name}; gender: {i.gender}; born: {i.dob.year} "
        f"(age {_age(i.dob)}); nationality: {i.nationality}",
        f"Location: {loc.city}, {loc.region}, {loc.country}",
        f"Work: {w.occupation} ({w.seniority}) at {w.employer}; industry {w.industry}",
    ]
    if violations:
        lines.append("Fix these problems from your previous attempt: " + "; ".join(violations))
    return "\n".join(lines)


def _map(payload: NarrativePayload) -> dict[str, Any]:
    pe, ap, bs, vo = payload.personality, payload.appearance, payload.backstory, payload.voice
    return {
        "personality": Personality(
            ocean=pe.ocean, ocean_status="gen", traits=pe.traits, traits_status="gen",
            values=pe.values, values_status="gen", quirks=pe.quirks, quirks_status="gen",
        ),
        "appearance": Appearance(
            description=ap.description, description_status="gen",
            hair_color=ap.hair_color, hair_color_status="gen",
            hair_style=ap.hair_style, hair_style_status="gen",
            eye_color=ap.eye_color, eye_color_status="gen",
            build=ap.build, build_status="gen",
            height_cm=ap.height_cm, height_cm_status="gen",
            distinguishing_features=ap.distinguishing_features,
            distinguishing_features_status="gen",
        ),
        "voice": Voice(
            writing_style=vo.writing_style, writing_style_status="gen",
            posting_cadence=vo.posting_cadence, posting_cadence_status="gen",
            typical_topics=vo.typical_topics, typical_topics_status="gen",
            sample_paragraph=vo.sample_paragraph, sample_paragraph_status="gen",
        ),
        "backstory": Backstory(
            bio=bs.bio, bio_status="gen", education=bs.education, education_status="gen",
            key_life_events=bs.key_life_events, key_life_events_status="gen",
        ),
    }


class NarrativeGenerator:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def generate(
        self, partial: PartialPersona, *, violations: list[str] | None = None
    ) -> dict[str, Any]:
        payload = await self._llm.acomplete_json(
            _system_prompt(), _user_prompt(partial, violations), NarrativePayload
        )
        assert isinstance(payload, NarrativePayload)
        return _map(payload)
