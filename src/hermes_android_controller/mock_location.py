"""Mock location bridge for a future Android helper app."""

from __future__ import annotations

from .adb_client import AdbClient, AdbCommandResult, get_default_client


MOCK_LOCATION_ACTION = "com.hermes.mocklocation.SET"
MOCK_LOCATION_HELPER_PACKAGE = "com.hermes.mocklocation"


def set_mock_location(
    lat: float,
    lon: float,
    accuracy: float,
    client: AdbClient | None = None,
) -> dict[str, object]:
    adb = client or get_default_client()
    package_check = adb.shell(["pm", "path", MOCK_LOCATION_HELPER_PACKAGE])
    if not package_check.ok or not str(package_check.stdout).strip():
        return _mock_location_error(
            package_check,
            "Mock Location Helper App is not installed or is not visible to ADB.",
        )

    result = adb.shell(
        [
            "am",
            "broadcast",
            "-a",
            MOCK_LOCATION_ACTION,
            "--ef",
            "lat",
            str(lat),
            "--ef",
            "lon",
            str(lon),
            "--ef",
            "accuracy",
            str(accuracy),
        ]
    )

    if not result.ok:
        return _mock_location_error(result, "Mock Location Helper broadcast failed.")

    stdout = str(result.stdout)
    if "Broadcast completed" not in stdout:
        return _mock_location_error(
            result,
            "Mock Location Helper App may not be installed or did not receive the broadcast.",
        )

    return {
        "ok": True,
        "package_check": package_check,
        "result": result,
        "message": "Mock location broadcast completed.",
    }


def _mock_location_error(result: AdbCommandResult, message: str) -> dict[str, object]:
    return {
        "ok": False,
        "result": result,
        "message": (
            f"{message} Install and authorize the Hermes Mock Location Helper App, "
            "then enable it as the Android mock location app in Developer options."
        ),
    }
