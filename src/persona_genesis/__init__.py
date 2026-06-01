"""persona-genesis: generate detailed, coherent personas.

Public API exposes the data contract (`Persona`, `PartialPersona`, media,
biometric, document, relationship, and vault models), the `PersonaBuilder`, the
persistence repositories, configuration, and the exception hierarchy. The
`PersonaGenerator` orchestrator is added in a later milestone.
"""

from persona_genesis.builder import PersonaBuilder
from persona_genesis.config import Config, ImageConfig, LLMConfig
from persona_genesis.db.repository import AsyncPersonaRepository, PersonaRepository
from persona_genesis.exceptions import (
    CoherenceError,
    ConfigError,
    PersonaGenerationError,
    PersonaGenesisError,
    ProviderError,
)
from persona_genesis.schema import (
    Account,
    Appearance,
    Audio,
    Backstory,
    Body,
    Contact,
    Device,
    Document,
    Education,
    Face,
    Identity,
    Image,
    Location,
    MediaOrigin,
    OceanScores,
    PartialPersona,
    Persona,
    PersonaDraft,
    Personality,
    PersonaMetadata,
    Relationship,
    Status,
    Video,
    Voice,
    VoicePrint,
    Work,
)

__version__ = "0.1.0"

__all__ = [
    "Account",
    "Appearance",
    "AsyncPersonaRepository",
    "Audio",
    "Backstory",
    "Body",
    "CoherenceError",
    "Config",
    "ConfigError",
    "Contact",
    "Device",
    "Document",
    "Education",
    "Face",
    "Identity",
    "Image",
    "ImageConfig",
    "LLMConfig",
    "Location",
    "MediaOrigin",
    "OceanScores",
    "PartialPersona",
    "Persona",
    "PersonaBuilder",
    "PersonaDraft",
    "PersonaGenerationError",
    "PersonaGenesisError",
    "PersonaMetadata",
    "PersonaRepository",
    "Personality",
    "ProviderError",
    "Relationship",
    "Status",
    "Video",
    "Voice",
    "VoicePrint",
    "Work",
    "__version__",
]
