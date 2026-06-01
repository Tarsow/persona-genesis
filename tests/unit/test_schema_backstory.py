from persona_genesis.schema.backstory import Backstory, Education, LifeEvent


def test_backstory_round_trips() -> None:
    bs = Backstory(
        bio="Grew up in Campinas, moved to São Paulo for work.",
        education=[
            Education(
                institution="UNICAMP",
                degree="BSc",
                field_of_study="Computer Science",
                start_year=2012,
                end_year=2016,
            )
        ],
        key_life_events=[LifeEvent(year=2016, description="First job as a junior dev")],
    )
    restored = Backstory.model_validate_json(bs.model_dump_json())
    assert restored == bs


def test_education_end_year_is_optional() -> None:
    edu = Education(
        institution="USP",
        degree="MSc",
        field_of_study="AI",
        start_year=2020,
    )
    assert edu.end_year is None
