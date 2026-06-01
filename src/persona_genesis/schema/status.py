"""Field-level realism provenance.

- ``real`` — value supplied by the caller.
- ``gen``  — generated but basically real (derived from real data, LLM narrative,
  or an AI embedding/description).
- ``fake`` — randomly generated, only looks real (Faker-invented, sampled).
"""

from typing import Literal

Status = Literal["real", "gen", "fake"]
