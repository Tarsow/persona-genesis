import persona_genesis


def test_public_api_exposes_contract() -> None:
    from persona_genesis import Config, PartialPersona, Persona, PersonaBuilder

    assert persona_genesis.__version__ == "0.1.0"
    assert Persona.__name__ == "Persona"
    assert PartialPersona.__name__ == "PartialPersona"
    assert PersonaBuilder.__name__ == "PersonaBuilder"
    assert Config().default_locale == "en_US"


def test_new_entity_symbols_exported() -> None:
    from persona_genesis import (
        Account,
        Body,
        Document,
        Face,
        Image,
        Relationship,
        VoicePrint,
    )

    assert {Account, Body, Document, Face, Image, Relationship, VoicePrint}


def test_persona_images_gone() -> None:
    assert not hasattr(persona_genesis, "PersonaImages")
    assert not hasattr(persona_genesis, "PersonaMedia")


def test_exceptions_reachable() -> None:
    from persona_genesis import (
        CoherenceError,
        ConfigError,
        PersonaGenerationError,
        PersonaGenesisError,
        ProviderError,
    )

    for exc in (PersonaGenerationError, CoherenceError, ProviderError, ConfigError):
        assert issubclass(exc, PersonaGenesisError)


def test_generator_symbols_exported() -> None:
    from persona_genesis import (
        GeoIP2Locator,
        GeoLocation,
        GeoLocator,
        ImageProvider,
        LLMProvider,
        PersonaGenerator,
        StructuredConstraints,
    )

    assert PersonaGenerator.__name__ == "PersonaGenerator"
    assert {
        GeoIP2Locator,
        GeoLocation,
        GeoLocator,
        ImageProvider,
        LLMProvider,
        StructuredConstraints,
    }
