"""PersonaGenerator — the public generation entry point. Structured layer is live;
narrative/visual layers raise until providers are wired (later phases)."""

from persona_genesis.builder import PersonaBuilder
from persona_genesis.config import Config
from persona_genesis.exceptions import ConfigError, PersonaGenerationError
from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.generators.structured import SUPPORTED_LOCALES, StructuredGenerator
from persona_genesis.geo.base import GeoLocator
from persona_genesis.providers.image import ImageProvider
from persona_genesis.providers.llm import LLMProvider
from persona_genesis.schema.contact import Contact
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.persona import Persona

_STRUCTURED_SECTIONS = ("identity", "location", "work", "device")


class PersonaGenerator:
    def __init__(
        self, config: Config, *, geolocator: GeoLocator | None = None,
        llm: LLMProvider | None = None, image: ImageProvider | None = None,
    ) -> None:
        self._config = config
        self._llm = llm
        self._image = image
        self._structured = StructuredGenerator(geolocator=geolocator)

    def _resolve_locale(self, locale: str | None) -> str:
        loc = locale or self._config.default_locale
        if loc in SUPPORTED_LOCALES:
            return loc
        if self._config.default_locale in SUPPORTED_LOCALES:
            return self._config.default_locale
        raise PersonaGenerationError(
            f"unsupported locale {loc!r}; supported: {sorted(SUPPORTED_LOCALES)}"
        )

    def generate_structured(
        self, seed: int, locale: str | None = None, *,
        constraints: StructuredConstraints | None = None,
    ) -> PartialPersona:
        loc = self._resolve_locale(locale)
        sections = self._structured.generate(seed, loc, constraints or StructuredConstraints())
        return PartialPersona(seed=seed, locale=loc, contact=Contact(), **sections)

    async def agenerate_structured(
        self, seed: int, locale: str | None = None, *,
        constraints: StructuredConstraints | None = None,
    ) -> PartialPersona:
        return self.generate_structured(seed, locale, constraints=constraints)

    def fill_structured(self, builder: PersonaBuilder) -> PartialPersona:
        partial = builder.build().persona
        loc = self._resolve_locale(partial.locale)
        seed = partial.seed if partial.seed is not None else 0
        sections = self._structured.generate(seed, loc, StructuredConstraints())
        missing = builder.missing()
        updated = partial.model_copy()
        for name in _STRUCTURED_SECTIONS:
            if name in missing:
                setattr(updated, name, sections[name])
        if "contact" in missing:
            updated.contact = Contact()
        if updated.locale is None:
            updated.locale = loc
        return updated

    async def afill_structured(self, builder: PersonaBuilder) -> PartialPersona:
        return self.fill_structured(builder)

    def generate(
        self, seed: int, locale: str | None = None, *,
        constraints: StructuredConstraints | None = None,
        include: set[str] | None = None,
    ) -> Persona:
        if self._llm is None:
            raise ConfigError("an LLM provider is required to generate narrative sections")
        raise NotImplementedError("narrative/visual generation lands in a later phase")

    async def agenerate(
        self, seed: int, locale: str | None = None, *,
        constraints: StructuredConstraints | None = None,
        include: set[str] | None = None,
    ) -> Persona:
        return self.generate(seed, locale, constraints=constraints, include=include)
