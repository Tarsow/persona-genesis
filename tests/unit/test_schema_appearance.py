import pytest
from pydantic import ValidationError

from persona_genesis.schema.appearance import Appearance


def test_appearance_round_trips() -> None:
    app = Appearance(
        description="Tall with short dark curly hair and warm brown eyes.",
        hair_color="dark brown",
        hair_style="short curly",
        eye_color="brown",
        build="athletic",
        height_cm=178,
        distinguishing_features=["small scar above left eyebrow"],
    )
    restored = Appearance.model_validate_json(app.model_dump_json())
    assert restored == app


def test_appearance_defaults_features_to_empty_list() -> None:
    app = Appearance(
        description="d",
        hair_color="black",
        hair_style="bald",
        eye_color="black",
        build="average",
        height_cm=170,
    )
    assert app.distinguishing_features == []


def test_appearance_rejects_nonpositive_height() -> None:
    with pytest.raises(ValidationError):
        Appearance(
            description="d",
            hair_color="black",
            hair_style="x",
            eye_color="black",
            build="average",
            height_cm=0,
        )
