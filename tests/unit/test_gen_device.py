import random

from persona_genesis.generators.constraints import StructuredConstraints
from persona_genesis.generators.device import generate_device


def test_device_profile_is_coherent() -> None:
    d = generate_device(random.Random(2), constraints=StructuredConstraints())
    # the UA must mention an OS token consistent with d.os
    ua = d.user_agent.lower()
    tokens = {
        "android": "android",
        "ios": "iphone os" if d.primary_device == "smartphone" else "os",
        "windows": "windows",
        "macos": "mac os",
        "linux": "linux",
    }
    assert tokens[d.os] in ua or d.os in ua
    assert "x" in d.screen_resolution
    assert d.user_agent_status == "fake"


def test_device_type_constraint_filters_pool() -> None:
    constraints = StructuredConstraints(device_type="smartphone")
    d = generate_device(random.Random(5), constraints=constraints)
    assert d.primary_device == "smartphone"


def test_every_device_type_has_a_profile() -> None:
    for dt in ("desktop", "laptop", "smartphone", "tablet"):
        d = generate_device(random.Random(5), constraints=StructuredConstraints(device_type=dt))
        assert d.primary_device == dt
