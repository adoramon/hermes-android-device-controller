"""Device status helpers."""

from __future__ import annotations

from .adb_client import AdbClient, AdbCommandResult, get_default_client


def device_status(client: AdbClient | None = None) -> dict[str, object]:
    adb = client or get_default_client()
    devices = adb.run(["devices", "-l"])
    screen_size: AdbCommandResult | None = None
    foreground_app: AdbCommandResult | None = None
    if devices.ok and _has_connected_device(str(devices.stdout)):
        screen_size = adb.shell(["wm", "size"])
        foreground_app = adb.shell(["dumpsys", "window"])

    return {
        "ok": devices.ok and screen_size is not None and foreground_app is not None,
        "devices": devices,
        "screen_size": screen_size,
        "screen_resolution": _parse_screen_size(str(screen_size.stdout)) if screen_size else None,
        "foreground_app": foreground_app,
        "foreground_package": _parse_foreground_package(str(foreground_app.stdout)) if foreground_app else None,
        "message": _status_message(devices, screen_size, foreground_app),
    }


def _has_connected_device(devices_stdout: str) -> bool:
    for line in devices_stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[1] == "device":
            return True
    return False


def _parse_screen_size(stdout: str) -> str | None:
    for line in stdout.splitlines():
        if "Physical size:" in line:
            return line.split("Physical size:", 1)[1].strip()
    return None


def _parse_foreground_package(stdout: str) -> str | None:
    markers = ("mCurrentFocus=", "mFocusedApp=", "topResumedActivity=")
    for line in stdout.splitlines():
        if any(marker in line for marker in markers):
            for token in line.replace("}", " ").split():
                if "/" in token:
                    return token.split("/", 1)[0].strip("{")
    return None


def _status_message(
    devices: AdbCommandResult,
    screen_size: AdbCommandResult | None,
    foreground_app: AdbCommandResult | None,
) -> str:
    if not devices.ok:
        return "adb devices failed; verify ADB is installed and accessible."
    if screen_size is None or foreground_app is None:
        return "No authorized Android device found over ADB."
    if not screen_size.ok:
        return "ADB device was listed, but screen size query failed."
    if not foreground_app.ok:
        return "ADB device was listed, but foreground app query failed."
    return "ADB device is connected and responsive."
