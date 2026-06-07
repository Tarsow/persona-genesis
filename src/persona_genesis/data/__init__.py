"""Bundled real-data assets for structured generation, loaded via importlib.resources."""

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast


def _load(rel: str) -> Any:
    return json.loads((files("persona_genesis.data") / rel).read_text(encoding="utf-8"))


@lru_cache
def load_locations(locale: str) -> list[dict[str, str]]:
    return cast(list[dict[str, str]], _load(f"locations/{locale}.json"))


@lru_cache
def load_ua_pool() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], _load("ua_pool.json"))


@lru_cache
def load_occupations() -> list[dict[str, str]]:
    return cast(list[dict[str, str]], _load("occupations.json"))
