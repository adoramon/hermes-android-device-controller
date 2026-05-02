"""Mock location bridge for a future Android helper app."""

from __future__ import annotations

from .adb_client import AdbClient, AdbCommandResult, get_default_client


MOCK_LOCATION_ACTION = "com.hermes.mocklocation.SET"


def set_mock_location(
    lat: float,
    lon: float,
    accuracy: float = 10,
    client: AdbClient | None = None,
) -> dict[str, object]:
    _validate_location(lat, lon, accuracy)
    adb = client or get_default_client()
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

    return {
        "ok": True,
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


def _validate_location(lat: float, lon: float, accuracy: float) -> None:
    if not isinstance(lat, int | float) or not -90 <= lat <= 90:
        raise ValueError("lat must be a number between -90 and 90.")
    if not isinstance(lon, int | float) or not -180 <= lon <= 180:
        raise ValueError("lon must be a number between -180 and 180.")
    if not isinstance(accuracy, int | float) or accuracy <= 0:
        raise ValueError("accuracy must be a positive number.")
