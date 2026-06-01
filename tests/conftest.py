import os
from datetime import UTC, date, datetime

import pytest

from persona_genesis.schema import (
    Appearance,
    Backstory,
    Contact,
    Device,
    Education,
    Identity,
    LifeEvent,
    Location,
    OceanScores,
    Persona,
    Personality,
    PersonaMetadata,
    Voice,
    Work,
)


@pytest.fixture
def sample_persona() -> Persona:
    return Persona(
        seed=42,
        locale="pt_BR",
        identity=Identity(
            full_name="Ana Souza",
            given_name="Ana",
            family_name="Souza",
            gender="female",
            dob=date(1994, 3, 12),
            nationality="BR",
        ),
        location=Location(
            country="BR",
            region="São Paulo",
            city="Campinas",
            street="Rua das Flores, 123",
            postal_code="13010-000",
            timezone="America/Sao_Paulo",
        ),
        contact=Contact(phone="+55 19 90000-0000", email="ana.souza@example.com"),
        work=Work(
            occupation="Backend Engineer",
            employer="Nubank",
            seniority="senior",
            industry="Fintech",
            schedule="full_time",
        ),
        appearance=Appearance(
            description="Tall with short dark curly hair and warm brown eyes.",
            hair_color="dark brown",
            hair_style="short curly",
            eye_color="brown",
            build="athletic",
            height_cm=178,
            distinguishing_features=["small scar above left eyebrow"],
        ),
        personality=Personality(
            ocean=OceanScores(
                openness=0.7,
                conscientiousness=0.6,
                extraversion=0.4,
                agreeableness=0.8,
                neuroticism=0.3,
            ),
            traits=["curious", "pragmatic"],
            values=["honesty", "craftsmanship"],
            quirks=["always early"],
        ),
        voice=Voice(
            writing_style="casual, short sentences",
            posting_cadence="2-3 times per day",
            typical_topics=["coding", "cooking"],
            sample_paragraph="Just shipped a new feature, feeling good about it!",
        ),
        device=Device(
            primary_device="smartphone",
            os="android",
            browser="chrome",
            user_agent="Mozilla/5.0 (Linux; Android 14) Chrome/124.0 Mobile",
            screen_resolution="1080x2400",
        ),
        backstory=Backstory(
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
        ),
        metadata=PersonaMetadata(
            generated_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            generator_version="0.1.0",
        ),
    )


DATABASE_URL_ENV = "PERSONA_GENESIS_TEST_DATABASE_URL"


@pytest.fixture
def database_url() -> str:
    url = os.environ.get(DATABASE_URL_ENV)
    if not url:
        pytest.skip(f"set {DATABASE_URL_ENV} to run persistence tests")
    return url


@pytest.fixture
def vault_key() -> bytes:
    from persona_genesis.db.crypto import generate_vault_key

    return generate_vault_key()
