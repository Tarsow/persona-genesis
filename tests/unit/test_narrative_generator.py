from datetime import date

from persona_genesis.generators.narrative.narrative import NarrativeGenerator
from persona_genesis.generators.narrative.payload import NarrativePayload
from persona_genesis.providers.fake_llm import FakeLLMProvider
from persona_genesis.schema.identity import Identity
from persona_genesis.schema.location import Location
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.work import Work


def _payload() -> NarrativePayload:
    return NarrativePayload.model_validate({
        "personality": {"ocean": {"openness": 0.6, "conscientiousness": 0.6, "extraversion": 0.4,
                                   "agreeableness": 0.7, "neuroticism": 0.3},
                        "traits": ["curious"], "values": ["honesty"], "quirks": ["hums"]},
        "appearance": {"description": "tall with short brown hair", "hair_color": "brown",
                       "hair_style": "short", "eye_color": "brown", "build": "average",
                       "height_cm": 178, "distinguishing_features": ["freckles"]},
        "backstory": {"bio": "grew up coding", "education": [], "key_life_events": []},
        "voice": {"writing_style": "casual", "posting_cadence": "daily",
                  "typical_topics": ["code"], "sample_paragraph": "shipped a feature today"},
    })


def _partial() -> PartialPersona:
    return PartialPersona(
        seed=1, locale="en_US",
        identity=Identity(full_name="Sam Lee", given_name="Sam", family_name="Lee",
                          gender="non_binary", dob=date(1994, 1, 1), nationality="US"),
        location=Location(country="US", region="California", city="San Francisco",
                          timezone="America/Los_Angeles"),
        work=Work(occupation="Engineer", employer="Acme", seniority="senior",
                  industry="Technology", schedule="full_time"),
    )


async def test_generate_maps_payload_with_gen_status() -> None:
    gen = NarrativeGenerator(FakeLLMProvider(payloads=[_payload()]))
    sections = await gen.generate(_partial())
    assert set(sections) == {"personality", "appearance", "backstory", "voice"}
    assert sections["appearance"].hair_color == "brown"
    assert sections["appearance"].hair_color_status == "gen"     # overrides the 'fake' default
    assert sections["personality"].traits_status == "gen"
    assert sections["voice"].writing_style_status == "gen"
    assert sections["backstory"].bio_status == "gen"
