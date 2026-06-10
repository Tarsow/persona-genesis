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
from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.geo.base import GeoLocation, GeoLocator
from persona_genesis.geo.geoip2_locator import GeoIP2Locator
from persona_genesis.orchestrator import PersonaGenerator
from persona_genesis.providers.factory import build_llm_provider
from persona_genesis.providers.fake_llm import FakeLLMProvider
from persona_genesis.providers.image import ImageProvider
from persona_genesis.providers.llm import LLMProvider
from persona_genesis.providers.openai_compat import OpenAICompatProvider
from persona_genesis.providers.recorded import RecordedProvider
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
    "FakeLLMProvider",
    "GeoIP2Locator",
    "GeoLocation",
    "GeoLocator",
    "Identity",
    "Image",
    "ImageConfig",
    "ImageProvider",
    "LLMConfig",
    "LLMProvider",
    "Location",
    "MediaOrigin",
    "OceanScores",
    "OpenAICompatProvider",
    "PartialPersona",
    "Persona",
    "PersonaBuilder",
    "PersonaDraft",
    "PersonaGenerationError",
    "PersonaGenerator",
    "PersonaGenesisError",
    "PersonaMetadata",
    "PersonaRepository",
    "Personality",
    "ProviderError",
    "RecordedProvider",
    "Relationship",
    "Status",
    "StructuredConstraints",
    "Video",
    "Voice",
    "VoicePrint",
    "Work",
    "__version__",
    "build_llm_provider",
]
