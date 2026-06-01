import pytest
from pydantic import ValidationError

from persona_genesis.schema.work import Work


def test_work_round_trips() -> None:
    work = Work(
        occupation="Backend Engineer",
        employer="Nubank",
        seniority="senior",
        industry="Fintech",
        schedule="full_time",
    )
    restored = Work.model_validate_json(work.model_dump_json())
    assert restored == work


def test_work_rejects_unknown_seniority() -> None:
    with pytest.raises(ValidationError):
        Work(
            occupation="x",
            employer="y",
            seniority="grandmaster",
            industry="z",
            schedule="full_time",
        )
