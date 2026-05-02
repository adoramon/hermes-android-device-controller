"""Generic Android input actions over ADB."""

from __future__ import annotations

from .adb_client import AdbClient, AdbCommandResult, get_default_client


def open_app(package_name: str, client: AdbClient | None = None) -> AdbCommandResult:
    if not package_name or not package_name.strip():
        raise ValueError("package_name must be a non-empty string.")
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
    _validate_coordinate("x", x)
    _validate_coordinate("y", y)
    adb = client or get_default_client()
    return adb.shell(["input", "tap", str(x), str(y)])


def swipe(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration_ms: int = 300,
    client: AdbClient | None = None,
) -> AdbCommandResult:
    for name, value in (("x1", x1), ("y1", y1), ("x2", x2), ("y2", y2)):
        _validate_coordinate(name, value)
    if not isinstance(duration_ms, int) or duration_ms <= 0:
        raise ValueError("duration_ms must be a positive integer.")
    adb = client or get_default_client()
    return adb.shell(["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])


def input_text(text: str, client: AdbClient | None = None) -> AdbCommandResult:
    if not isinstance(text, str):
        raise ValueError("text must be a string.")
    adb = client or get_default_client()
    return adb.shell(["input", "text", _format_input_text(text)])


def keyevent(code: int, client: AdbClient | None = None) -> AdbCommandResult:
    if not isinstance(code, int) or code < 0:
        raise ValueError("keyevent code must be a non-negative integer.")
    adb = client or get_default_client()
    return adb.shell(["input", "keyevent", str(code)])


def _format_input_text(text: str) -> str:
    return text.replace(" ", "%s")


def _validate_coordinate(name: str, value: int) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
