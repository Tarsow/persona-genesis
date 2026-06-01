import pytest
from pydantic import ValidationError

from persona_genesis.schema.personality import OceanScores, Personality


def _ocean() -> OceanScores:
    return OceanScores(
        openness=0.7,
        conscientiousness=0.6,
        extraversion=0.4,
        agreeableness=0.8,
        neuroticism=0.3,
    )


def test_personality_round_trips() -> None:
    p = Personality(
        ocean=_ocean(),
        traits=["curious", "pragmatic"],
        values=["honesty", "craftsmanship"],
        quirks=["always early"],
    )
    restored = Personality.model_validate_json(p.model_dump_json())
    assert restored == p


def test_ocean_scores_bounded_0_1() -> None:
    with pytest.raises(ValidationError):
        OceanScores(
            openness=1.5,
            conscientiousness=0.5,
            extraversion=0.5,
            agreeableness=0.5,
            neuroticism=0.5,
        )
