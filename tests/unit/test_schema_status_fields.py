from datetime import date

from persona_genesis.schema.device import Device
from persona_genesis.schema.identity import Identity
from persona_genesis.schema.work import Work


def test_identity_status_defaults_fake() -> None:
    i = Identity(full_name="A B", given_name="A", family_name="B", gender="female",
                 dob=date(1994, 3, 12), nationality="BR")
    assert i.full_name_status == "fake"
    assert i.dob_status == "fake"
    assert i.nationality_status == "fake"


def test_work_status_defaults_fake() -> None:
    w = Work(occupation="Engineer", employer="X", seniority="senior", industry="Tech",
             schedule="full_time")
    assert w.occupation_status == "fake"
    assert w.seniority_status == "fake"


def test_device_status_defaults_fake() -> None:
    d = Device(primary_device="smartphone", os="android", browser="chrome",
               user_agent="UA", screen_resolution="1080x2400")
    assert d.user_agent_status == "fake"
    assert d.os_status == "fake"


def test_appearance_status_mix() -> None:
    from persona_genesis.schema.appearance import Appearance

    a = Appearance(description="d", hair_color="brown", hair_style="short",
                   eye_color="brown", build="average", height_cm=170)
    assert a.description_status == "gen"
    assert a.hair_color_status == "fake"
    assert a.distinguishing_features_status == "fake"


def test_personality_voice_backstory_status_gen() -> None:
    from persona_genesis.schema.backstory import Backstory
    from persona_genesis.schema.personality import OceanScores, Personality
    from persona_genesis.schema.voice import Voice

    p = Personality(ocean=OceanScores(openness=0.5, conscientiousness=0.5,
                    extraversion=0.5, agreeableness=0.5, neuroticism=0.5))
    assert p.ocean_status == "gen"
    assert p.traits_status == "gen"

    v = Voice(writing_style="x", posting_cadence="daily", sample_paragraph="y")
    assert v.writing_style_status == "gen"
    assert v.typical_topics_status == "gen"

    b = Backstory(bio="x")
    assert b.bio_status == "gen"
    assert b.education_status == "gen"
