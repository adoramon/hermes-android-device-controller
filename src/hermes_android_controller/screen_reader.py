"""Screen inspection helpers over ADB."""

from __future__ import annotations

from .adb_client import AdbClient, AdbCommandResult, get_default_client


def dump_screen_xml(client: AdbClient | None = None) -> AdbCommandResult:
    adb = client or get_default_client()
    return adb.run(["exec-out", "uiautomator", "dump", "/dev/tty"])


def take_screenshot(client: AdbClient | None = None) -> AdbCommandResult:
    adb = client or get_default_client()
    return adb.run(["exec-out", "screencap", "-p"], text=False)
