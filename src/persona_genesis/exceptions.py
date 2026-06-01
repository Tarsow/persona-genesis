"""Exception hierarchy for persona-genesis."""


class PersonaGenesisError(Exception):
    """Base class for all errors raised by persona-genesis."""


class PersonaGenerationError(PersonaGenesisError):
    """Raised when persona generation fails irrecoverably."""


class CoherenceError(PersonaGenesisError):
    """Raised when cross-field coherence validation fails after retry."""


class ProviderError(PersonaGenesisError):
    """Raised when an LLM or image provider call fails."""


class ConfigError(PersonaGenesisError):
    """Raised when configuration is missing or invalid."""
