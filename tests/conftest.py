import os
from datetime import UTC, date, datetime
from pathlib import Path

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


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--level",
        action="store",
        type=int,
        default=0,
        help="API cost tier: 0 offline (default), 1 minimal real API, 2 full real API",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "llm(level): requires API cost --level >= the given value")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_level = int(config.getoption("--level"))
    for item in items:
        marker = item.get_closest_marker("llm")
        if marker is None:
            continue
        required = int(marker.kwargs.get("level", marker.args[0] if marker.args else 1))
        if required > run_level:
            item.add_marker(
                pytest.mark.skip(reason=f"needs --level {required} (running at {run_level})")
            )


def _dotenv() -> dict[str, str]:
    env = Path(__file__).resolve().parent.parent / ".env"
    out: dict[str, str] = {}
    if not env.exists():
        return out
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


@pytest.fixture(scope="session")
def deepseek_api_key() -> str:
    key = _dotenv().get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        pytest.skip("DEEPSEEK_API_KEY not set (add it to .env)")
    return key


@pytest.fixture
def live_llm(deepseek_api_key: str) -> object:
    from persona_genesis.providers.openai_compat import OpenAICompatProvider

    return OpenAICompatProvider(api_key=deepseek_api_key)
