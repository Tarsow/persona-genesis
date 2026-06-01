import pytest

from persona_genesis.exceptions import (
    CoherenceError,
    ConfigError,
    PersonaGenerationError,
    PersonaGenesisError,
    ProviderError,
)


@pytest.mark.parametrize(
    "exc",
    [PersonaGenerationError, CoherenceError, ProviderError, ConfigError],
)
def test_all_errors_subclass_base(exc: type[Exception]) -> None:
    assert issubclass(exc, PersonaGenesisError)


def test_base_is_an_exception() -> None:
    assert issubclass(PersonaGenesisError, Exception)
    with pytest.raises(PersonaGenesisError):
        raise CoherenceError("boom")
