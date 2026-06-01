from uuid import uuid4

import pytest
from pydantic import ValidationError

from persona_genesis.schema.relationship import Relationship


def test_relationship_round_trip() -> None:
    r = Relationship(person_1_id=uuid4(), person_2_id=uuid4(), relationship="friend")
    assert r.status == "gen"
    assert Relationship.model_validate_json(r.model_dump_json()) == r


def test_relationship_type_validated() -> None:
    with pytest.raises(ValidationError):
        Relationship(person_1_id=uuid4(), person_2_id=uuid4(), relationship="enemies")
