from datetime import date

from persona_genesis.generators.narrative.narrative import (
    NarrativeGenerator,
    _user_prompt,
    _voice_language,
)
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


def test_user_prompt_states_birth_year() -> None:
    # The model must be given the exact birth year so it does not anchor early
    # life events to (current_year - age), which can be dob.year - 1.
    prompt = _user_prompt(_partial(), None)
    assert "1994" in prompt  # _partial()'s dob is 1994-01-01


def test_voice_language_maps_non_english_locales() -> None:
    assert _voice_language("pt_BR") == "Brazilian Portuguese"
    assert _voice_language("de_DE") == "German"
    assert _voice_language("fr-FR") == "French"  # hyphen form normalised


def test_voice_language_is_none_for_english_or_unknown() -> None:
    # English is the default output language → no instruction (keeps the en_US prompt,
    # and thus the snapshot cassette, unchanged).
    assert _voice_language("en_US") is None
    assert _voice_language("en_GB") is None
    assert _voice_language(None) is None
    assert _voice_language("zz_ZZ") is None  # unknown subtag → no explicit name


def test_user_prompt_localizes_voice_for_non_english_locale() -> None:
    partial = _partial().model_copy(update={"locale": "pt_BR"})
    prompt = _user_prompt(partial, None)
    assert "Brazilian Portuguese" in prompt


def test_user_prompt_has_no_voice_language_line_for_english() -> None:
    prompt = _user_prompt(_partial(), None)  # en_US
    assert "language" not in prompt.lower()


async def test_generate_maps_payload_with_gen_status() -> None:
    gen = NarrativeGenerator(FakeLLMProvider(payloads=[_payload()]))
    sections = await gen.generate(_partial())
    assert set(sections) == {"personality", "appearance", "backstory", "voice"}
    assert sections["appearance"].hair_color == "brown"
    assert sections["appearance"].hair_color_status == "gen"     # overrides the 'fake' default
    assert sections["personality"].traits_status == "gen"
    assert sections["voice"].writing_style_status == "gen"
    assert sections["backstory"].bio_status == "gen"
