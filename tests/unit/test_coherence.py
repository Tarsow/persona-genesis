from persona_genesis.coherence import check_persona
from persona_genesis.schema.appearance import Appearance
from persona_genesis.schema.backstory import Backstory, Education, LifeEvent
from persona_genesis.schema.device import Device


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


def _device(**overrides: object) -> Device:
    base = dict(
        primary_device="smartphone", os="android", browser="chrome",
        user_agent="Mozilla/5.0 (Linux; Android 14) Chrome/124.0 Mobile",
        screen_resolution="1080x2400",
    )
    base.update(overrides)
    return Device(**base)  # type: ignore[arg-type]


def test_user_agent_missing_os_token_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    bad = sample_persona.model_copy(update={
        "device": _device(os="ios")  # default UA is Android, so ios token is absent
    })
    assert any("user agent" in v and "ios" in v for v in check_persona(bad))


def test_user_agent_missing_browser_token_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    bad = sample_persona.model_copy(update={
        "device": _device(browser="firefox")  # UA still says Chrome
    })
    assert any("user agent" in v and "firefox" in v for v in check_persona(bad))


def test_consistent_user_agent_not_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    ok = sample_persona.model_copy(update={
        "device": _device(
            primary_device="laptop", os="macos", browser="safari",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
            ),
        )
    })
    assert check_persona(ok) == []


def _appearance(**overrides: object) -> Appearance:
    base = dict(
        description="She has dark brown hair and warm brown eyes, an athletic build, 178 cm tall.",
        hair_color="dark brown", hair_style="short", eye_color="brown",
        build="athletic", height_cm=178,
    )
    base.update(overrides)
    return Appearance(**base)  # type: ignore[arg-type]


def test_appearance_hair_color_contradiction_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    bad = sample_persona.model_copy(update={
        "appearance": _appearance(
            description="She has bright blonde hair and warm brown eyes.", hair_color="black",
        )
    })
    assert any("hair" in v for v in check_persona(bad))


def test_appearance_eye_color_contradiction_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    bad = sample_persona.model_copy(update={
        "appearance": _appearance(
            description="She has dark brown hair and striking blue eyes.", eye_color="green",
        )
    })
    assert any("eye" in v for v in check_persona(bad))


def test_appearance_height_mismatch_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    bad = sample_persona.model_copy(update={
        "appearance": _appearance(
            description="He stands 150 cm tall with dark brown hair and brown eyes.",
            height_cm=190,
        )
    })
    assert any("height" in v for v in check_persona(bad))


def test_appearance_build_mismatch_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    bad = sample_persona.model_copy(update={
        "appearance": _appearance(
            description="She has dark brown hair, brown eyes, and a slim build.",
            build="muscular",
        )
    })
    assert any("build" in v for v in check_persona(bad))


def test_appearance_color_omission_not_flagged(sample_persona) -> None:  # type: ignore[no-untyped-def]
    # Description that doesn't name hair/eye colors must not be flagged as a contradiction.
    ok = sample_persona.model_copy(update={
        "appearance": _appearance(
            description="A tall person with a confident posture and a friendly smile.",
        )
    })
    assert check_persona(ok) == []
