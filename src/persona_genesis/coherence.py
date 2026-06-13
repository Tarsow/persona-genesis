"""Deterministic cross-field coherence checks. Returns human-readable violations."""

import re
from datetime import date

from persona_genesis.generators.work import MIN_YEARS_EXPERIENCE
from persona_genesis.schema.appearance import Appearance
from persona_genesis.schema.device import Device
from persona_genesis.schema.persona import Persona

# Substrings a user agent should contain for a given structured OS / browser.
_OS_UA_TOKENS: dict[str, tuple[str, ...]] = {
    "windows": ("windows",),
    "macos": ("mac",),
    "linux": ("linux",),
    "android": ("android",),
    "ios": ("iphone", "ipad", "ios"),
}
_BROWSER_UA_TOKENS: dict[str, tuple[str, ...]] = {
    "chrome": ("chrome",),
    "firefox": ("firefox",),
    "edge": ("edg",),  # modern Edge advertises "Edg/"
}

# Colour words used to detect a contradiction between the free-text description
# and the structured hair/eye colour. Synonyms (e.g. "brunette") are excluded so
# a missing synonym never produces a false positive.
_COLOR_WORDS = frozenset({
    "black", "brown", "blonde", "blond", "red", "auburn", "ginger",
    "gray", "grey", "white", "silver", "hazel", "blue", "green", "amber",
})
_BUILD_WORDS = frozenset({"slim", "average", "athletic", "muscular", "heavy"})


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def _window_before(words: list[str], nouns: set[str], size: int = 4) -> list[str] | None:
    """The `size` words preceding the first occurrence of any noun, or None."""
    for i, w in enumerate(words):
        if w in nouns:
            return words[max(0, i - size):i]
    return None


def _check_device(device: Device) -> list[str]:
    violations: list[str] = []
    ua = device.user_agent.lower()
    os_tokens = _OS_UA_TOKENS.get(device.os, ())
    if os_tokens and not any(t in ua for t in os_tokens):
        violations.append(
            f"user agent does not match os '{device.os}': {device.user_agent}"
        )
    if device.browser == "safari":
        # Chrome and Edge UAs also contain "Safari"; a real Safari UA does not.
        if "safari" not in ua or "chrome" in ua or "edg/" in ua:
            violations.append(
                f"user agent does not match browser 'safari': {device.user_agent}"
            )
    else:
        tokens = _BROWSER_UA_TOKENS.get(device.browser, ())
        if tokens and not any(t in ua for t in tokens):
            violations.append(
                f"user agent does not match browser '{device.browser}': {device.user_agent}"
            )
    return violations


def _check_appearance(appearance: Appearance) -> list[str]:
    violations: list[str] = []
    words = _words(appearance.description)

    for label, nouns, structured in (
        ("hair", {"hair"}, appearance.hair_color),
        ("eye", {"eye", "eyes"}, appearance.eye_color),
    ):
        window = _window_before(words, nouns)
        if window is None:
            continue
        mentioned = {w for w in window if w in _COLOR_WORDS}
        structured_colors = {w for w in _words(structured) if w in _COLOR_WORDS}
        if mentioned and structured_colors and mentioned.isdisjoint(structured_colors):
            violations.append(
                f"{label} colour in description {sorted(mentioned)} contradicts "
                f"structured '{structured}'"
            )

    build_window = _window_before(words, {"build", "physique", "frame"})
    if build_window is not None:
        mentioned_builds = {w for w in build_window if w in _BUILD_WORDS}
        if mentioned_builds and appearance.build not in mentioned_builds:
            violations.append(
                f"build in description {sorted(mentioned_builds)} contradicts "
                f"structured '{appearance.build}'"
            )

    cm = re.search(r"(\d{2,3})\s*cm", appearance.description.lower())
    if cm is not None and abs(int(cm.group(1)) - appearance.height_cm) > 3:
        violations.append(
            f"height in description {cm.group(1)}cm contradicts structured "
            f"{appearance.height_cm}cm"
        )
    return violations


def check_persona(persona: Persona) -> list[str]:
    violations: list[str] = []
    age = _age(persona.identity.dob)
    needed = MIN_YEARS_EXPERIENCE[persona.work.seniority]
    allowed = max(0, age - 22)
    if needed > allowed:
        violations.append(
            f"seniority '{persona.work.seniority}' needs ~{needed}y experience "
            f"but age {age} allows {allowed}y"
        )
    birth_year = persona.identity.dob.year
    this_year = date.today().year
    for e in persona.backstory.education:
        if e.end_year is not None and e.start_year > e.end_year:
            violations.append(f"education start_year {e.start_year} after end_year {e.end_year}")
        if not (birth_year <= e.start_year <= this_year):
            violations.append(
                f"education start_year {e.start_year} outside [{birth_year}, {this_year}]"
            )
        if e.end_year is not None and not (birth_year <= e.end_year <= this_year):
            violations.append(
                f"education end_year {e.end_year} outside [{birth_year}, {this_year}]"
            )
    years = [le.year for le in persona.backstory.key_life_events]
    if years != sorted(years):
        violations.append("life events are not in chronological order")
    for y in years:
        if not (birth_year <= y <= this_year):
            violations.append(f"life event year {y} outside [{birth_year}, {this_year}]")
    violations.extend(_check_device(persona.device))
    violations.extend(_check_appearance(persona.appearance))
    return violations
