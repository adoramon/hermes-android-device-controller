"""Public tool surface for Hermes skill integration."""

from __future__ import annotations

from .device_status import device_status
from .input_actions import input_text, keyevent, open_app, swipe, tap
from .mock_location import set_mock_location
from .screen_reader import dump_screen_xml, take_screenshot


def android_device_status() -> dict[str, object]:
    return device_status()


def android_open_app(package_name: str):
    return open_app(package_name)


def android_input_tap(x: int, y: int):
    return tap(x, y)


def android_input_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
    return swipe(x1, y1, x2, y2, duration_ms)


def android_input_text(text: str):
    return input_text(text)


def android_keyevent(code: int):
    return keyevent(code)


def android_dump_screen_xml() -> dict[str, object]:
    return dump_screen_xml()


def android_take_screenshot() -> dict[str, object]:
    return take_screenshot()


def android_set_mock_location(lat: float, lon: float, accuracy: float = 10) -> dict[str, object]:
    return set_mock_location(lat, lon, accuracy)

__all__ = [
    "android_device_status",
    "android_open_app",
    "android_input_tap",
    "android_input_swipe",
    "android_input_text",
    "android_keyevent",
    "android_dump_screen_xml",
    "android_take_screenshot",
    "android_set_mock_location",
    "device_status",
    "open_app",
    "tap",
    "swipe",
    "input_text",
    "keyevent",
    "dump_screen_xml",
    "take_screenshot",
    "set_mock_location",
]
