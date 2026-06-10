from persona_genesis.coherence import check_persona
from persona_genesis.schema.backstory import Backstory, Education, LifeEvent


def test_clean_persona_has_no_violations(sample_persona) -> None:  # type: ignore[no-untyped-def]
    assert check_persona(sample_persona) == []


def test_education_start_after_end_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    bad = sample_persona.model_copy(update={
        "backstory": Backstory(
            bio="x",
            education=[Education(institution="U", degree="BSc", field_of_study="CS",
                                 start_year=2016, end_year=2012)],
        )
    })
    assert any("start" in v for v in check_persona(bad))


def test_life_events_out_of_order_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    bad = sample_persona.model_copy(update={
        "backstory": Backstory(
            bio="x",
            key_life_events=[LifeEvent(year=2020, description="b"),
                             LifeEvent(year=2010, description="a")],
        )
    })
    assert any("chronological" in v for v in check_persona(bad))
