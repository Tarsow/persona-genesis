from typing import get_args

from persona_genesis.schema.status import Status


def test_status_has_three_values() -> None:
    assert set(get_args(Status)) == {"real", "gen", "fake"}
