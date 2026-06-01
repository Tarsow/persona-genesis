"""Device sub-model: hardware, OS, browser and the matching user agent."""

from typing import Literal

from pydantic import BaseModel

from persona_genesis.schema.status import Status

DeviceType = Literal["desktop", "laptop", "smartphone", "tablet"]
OS = Literal["windows", "macos", "linux", "android", "ios"]
Browser = Literal["chrome", "firefox", "safari", "edge"]


class Device(BaseModel):
    primary_device: DeviceType
    primary_device_status: Status = "fake"
    os: OS
    os_status: Status = "fake"
    browser: Browser
    browser_status: Status = "fake"
    user_agent: str
    user_agent_status: Status = "fake"
    screen_resolution: str  # "<width>x<height>"
    screen_resolution_status: Status = "fake"
