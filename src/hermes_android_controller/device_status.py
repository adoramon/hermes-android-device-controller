"""Device status helpers."""

from __future__ import annotations

from .adb_client import AdbClient, AdbCommandResult, get_default_client


def device_status(client: AdbClient | None = None) -> dict[str, object]:
    adb = client or get_default_client()
    devices = adb.run(["devices", "-l"])
    state: AdbCommandResult | None = None
    if devices.ok and _has_connected_device(str(devices.stdout)):
        state = adb.run(["get-state"])

    return {
        "ok": devices.ok and (state.ok if state else False),
        "devices": devices,
        "state": state,
        "message": _status_message(devices, state),
    }


def _has_connected_device(devices_stdout: str) -> bool:
    for line in devices_stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[1] == "device":
            return True
    return False


def _status_message(devices: AdbCommandResult, state: AdbCommandResult | None) -> str:
    if not devices.ok:
        return "adb devices failed; verify ADB is installed and accessible."
    if state is None:
        return "No authorized Android device found over ADB."
    if not state.ok:
        return "ADB device was listed, but adb get-state failed."
    return f"ADB device state: {str(state.stdout).strip()}"
