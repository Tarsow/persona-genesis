# persona-genesis

Generate highly detailed, coherent personas — structured identity, narrative
personality/backstory, and (in later milestones) visual face/body images — as a
pure-generator Python library.

> **Status:** v0.1 foundation. This milestone ships the `Persona` data contract,
> configuration, and the exception hierarchy. Generators and providers land in
> subsequent milestones.

## Install

```bash
uv add "persona-genesis @ git+https://github.com/tarsow/persona-genesis"
```

Provider integrations are opt-in extras: `[anthropic]`, `[openai]`,
`[local-image]`, `[cli]`, `[all]`.

## The contract

```python
from persona_genesis import Persona, Config

# Persona is a Pydantic model. JSON round-trips losslessly; image fields are
# excluded from serialization and handled separately by the consumer.

# Config is injected as a nested dict — the library never reads .env or the
# environment itself. Build the dict however you like (literals, a secrets
# manager, or transformed from your own .env loader — your choice).
cfg = Config.from_dict({
    "llm": {"provider": "anthropic", "api_key": "...", "model": "claude-opus-4-7"},
    "image": {"provider": "fal", "api_key": "...", "model": "fal-ai/flux/schnell"},
    "default_locale": "pt_BR",
})
```

See `specs/` for the full design and `docs/superpowers/plans/` for the
implementation plan.

## Development

```bash
uv sync
uv run ruff check .
uv run mypy
uv run pytest
```

## License

MIT — see [LICENSE](LICENSE).
