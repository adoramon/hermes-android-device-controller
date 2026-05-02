"""Generic Android input actions over ADB."""

from __future__ import annotations

from .adb_client import AdbClient, AdbCommandResult, get_default_client


def open_app(package_name: str, client: AdbClient | None = None) -> AdbCommandResult:
    adb = client or get_default_client()
    return adb.shell(
        [
            "monkey",
            "-p",
            package_name,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ]
    )


def tap(x: int, y: int, client: AdbClient | None = None) -> AdbCommandResult:
    adb = client or get_default_client()
    return adb.shell(["input", "tap", str(x), str(y)])


def swipe(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration_ms: int,
    client: AdbClient | None = None,
) -> AdbCommandResult:
    adb = client or get_default_client()
    return adb.shell(["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])


def input_text(text: str, client: AdbClient | None = None) -> AdbCommandResult:
    adb = client or get_default_client()
    return adb.shell(["input", "text", _format_input_text(text)])


def _format_input_text(text: str) -> str:
    return text.replace(" ", "%s")
