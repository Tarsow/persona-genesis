import pytest
from pydantic import ValidationError

from persona_genesis.schema.device import Device


def test_device_round_trips() -> None:
    device = Device(
        primary_device="smartphone",
        os="android",
        browser="chrome",
        user_agent="Mozilla/5.0 (Linux; Android 14) ... Chrome/124.0 Mobile",
        screen_resolution="1080x2400",
    )
    restored = Device.model_validate_json(device.model_dump_json())
    assert restored == device


def test_device_rejects_unknown_os() -> None:
    with pytest.raises(ValidationError):
        Device(
            primary_device="smartphone",
            os="symbian",
            browser="chrome",
            user_agent="x",
            screen_resolution="1x1",
        )
