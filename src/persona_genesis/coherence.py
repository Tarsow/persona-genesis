"""Deterministic cross-field coherence checks. Returns human-readable violations."""

from datetime import date

from persona_genesis.generators.work import MIN_YEARS_EXPERIENCE
from persona_genesis.schema.persona import Persona


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def check_persona(persona: Persona) -> list[str]:
    violations: list[str] = []
    age = _age(persona.identity.dob)
    needed = MIN_YEARS_EXPERIENCE[persona.work.seniority]
    allowed = max(0, age - 22)
    if needed > allowed:
        violations.append(
            f"seniority '{persona.work.seniority}' needs ~{needed}y experience "
            f"but age {age} allows {allowed}y"
        )
    birth_year = persona.identity.dob.year
    this_year = date.today().year
    for e in persona.backstory.education:
        if e.end_year is not None and e.start_year > e.end_year:
            violations.append(f"education start_year {e.start_year} after end_year {e.end_year}")
        if not (birth_year <= e.start_year <= this_year):
            violations.append(
                f"education start_year {e.start_year} outside [{birth_year}, {this_year}]"
            )
        if e.end_year is not None and not (birth_year <= e.end_year <= this_year):
            violations.append(
                f"education end_year {e.end_year} outside [{birth_year}, {this_year}]"
            )
    years = [le.year for le in persona.backstory.key_life_events]
    if years != sorted(years):
        violations.append("life events are not in chronological order")
    for y in years:
        if not (birth_year <= y <= this_year):
            violations.append(f"life event year {y} outside [{birth_year}, {this_year}]")
    return violations
