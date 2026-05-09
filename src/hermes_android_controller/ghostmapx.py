"""Ghostmapx address-to-coordinate helpers for authorized test devices."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import random
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .adb_client import AdbClient, get_default_client
from .app_probe import parse_ui_xml
from .device_status import device_status
from .input_actions import open_app
from .screen_reader import dump_screen_xml, take_screenshot


GHOSTMAPX_PACKAGE_ENV = "GHOSTMAPX_PACKAGE"
GHOSTMAPX_PACKAGE = "com.ghostmapx.app"
GHOSTMAPX_AMAP_KEY_ENV = "GHOSTMAPX_AMAP_KEY"
GHOSTMAPX_CONFIRM_TEXT = "确认Ghostmapx测试定位"
DEFAULT_RANDOM_RADIUS_METERS = 50.0
EARTH_RADIUS_METERS = 6_371_000.0

SEARCH_INPUT_ID_SUFFIX = ":id/searchInput"
COORD_TEXT_ID_SUFFIX = ":id/coordText"
STATUS_TEXT_ID_SUFFIX = ":id/statusText"
SIMULATING_TERMS = ("模拟中", "已模拟", "Mocking", "Simulating")


@dataclass(frozen=True)
class Coordinates:
    longitude: float
    latitude: float
    provider: str
    raw: dict[str, Any]
    center_longitude: float | None = None
    center_latitude: float | None = None
    random_radius_meters: float = 0.0
    random_offset_meters: float = 0.0

    @property
    def ghostmapx_text(self) -> str:
        return f"{self.longitude:.6f},{self.latitude:.6f}"

    def to_dict(self) -> dict[str, object]:
        return {
            "longitude": self.longitude,
            "latitude": self.latitude,
            "provider": self.provider,
            "ghostmapx_text": self.ghostmapx_text,
            "center_longitude": self.center_longitude,
            "center_latitude": self.center_latitude,
            "random_radius_meters": self.random_radius_meters,
            "random_offset_meters": self.random_offset_meters,
            "raw": self.raw,
        }


def geocode_address(
    address: str,
    *,
    provider: str = "auto",
    env_path: str | Path | None = None,
    random_radius_meters: float = DEFAULT_RANDOM_RADIUS_METERS,
    timeout: float = 10.0,
) -> dict[str, object]:
    """Translate a human address into randomized longitude/latitude coordinates."""

    normalized = _require_address(address)
    radius = _validate_random_radius(random_radius_meters)
    env = _read_env_file(_resolve_env_path(env_path))
    selected_provider = _select_provider(provider, env)
    try:
        if selected_provider == "amap":
            center = _geocode_amap(normalized, env=env, timeout=timeout)
        elif selected_provider == "nominatim":
            center = _geocode_nominatim(normalized, timeout=timeout)
        else:
            raise ValueError("provider must be one of: auto, amap, nominatim.")
        coordinates = _randomize_coordinates(center, radius)
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Failed to geocode address with {selected_provider}: {exc}",
            "address": normalized,
            "provider": selected_provider,
        }

    return {
        "ok": True,
        "message": "Address geocoded and randomized.",
        "address": normalized,
        "coordinates": coordinates.to_dict(),
    }


def open_ghostmapx(client: AdbClient | None = None) -> dict[str, object]:
    """Open Ghostmapx by package name."""

    adb = client or get_default_client()
    package_name = _ghostmapx_package()
    status = device_status(client=adb)
    if status.get("foreground_package") == package_name:
        return {
            "ok": True,
            "message": "Ghostmapx is already foreground.",
            "package": package_name,
            "launch": None,
            "status": status,
        }
    launch = open_app(package_name, client=adb)
    time.sleep(2)
    return {
        "ok": launch.ok,
        "message": "Ghostmapx opened." if launch.ok else "Failed to open Ghostmapx.",
        "package": package_name,
        "launch": launch,
    }


def probe_ghostmapx_screen(client: AdbClient | None = None) -> dict[str, object]:
    """Read Ghostmapx UI state without changing location."""

    adb = client or get_default_client()
    package_name = _ghostmapx_package()
    status = device_status(client=adb)
    xml_result = dump_screen_xml(client=adb)
    screenshot_result = take_screenshot(client=adb)
    nodes: list[dict[str, object]] = []
    parse_error = None
    if xml_result.get("ok") and xml_result.get("path"):
        try:
            nodes = parse_ui_xml(str(xml_result["path"]))
        except Exception as exc:
            parse_error = str(exc)
    search_input = _find_node_by_suffix(nodes, SEARCH_INPUT_ID_SUFFIX)
    coord_text = _find_node_by_suffix(nodes, COORD_TEXT_ID_SUFFIX)
    status_text = _find_node_by_suffix(nodes, STATUS_TEXT_ID_SUFFIX)
    status_label = str(status_text.get("text", "")) if status_text else ""
    return {
        "ok": bool(status.get("ok")) and bool(xml_result.get("ok")) and parse_error is None,
        "package": package_name,
        "foreground_package": status.get("foreground_package"),
        "is_foreground": status.get("foreground_package") == package_name,
        "xml_path": xml_result.get("path"),
        "screenshot_path": screenshot_result.get("path"),
        "search_input": search_input,
        "coord_text": coord_text,
        "status_text": status_text,
        "is_simulating": _is_simulating_label(status_label),
        "status_label": status_label,
        "parse_error": parse_error,
        "node_count": len(nodes),
        "status": status,
        "xml": xml_result,
        "screenshot": screenshot_result,
    }


def prepare_ghostmapx_location(
    address: str,
    *,
    provider: str = "auto",
    random_radius_meters: float = DEFAULT_RANDOM_RADIUS_METERS,
) -> dict[str, object]:
    """Geocode an address and report current Ghostmapx state without writing anything."""

    geocode = geocode_address(address, provider=provider, random_radius_meters=random_radius_meters)
    if not geocode.get("ok"):
        return geocode
    opened = open_ghostmapx()
    screen = probe_ghostmapx_screen()
    return {
        "ok": bool(opened.get("ok")) and bool(screen.get("ok")),
        "message": "Ghostmapx location is ready to apply.",
        "address": address,
        "coordinates": geocode.get("coordinates"),
        "open": opened,
        "screen": _screen_summary(screen),
    }


def apply_ghostmapx_location(
    address: str,
    *,
    provider: str = "auto",
    confirm_text: str = "",
    random_radius_meters: float = DEFAULT_RANDOM_RADIUS_METERS,
    client: AdbClient | None = None,
) -> dict[str, object]:
    """Geocode an address, enter it in Ghostmapx, and confirm the app is simulating.

    The explicit confirmation phrase keeps this tool from being triggered by a
    casual address mention in chat or by unrelated enterprise automation.
    """

    if confirm_text != GHOSTMAPX_CONFIRM_TEXT:
        return {
            "ok": False,
            "message": f"Refusing to modify Ghostmapx without confirm_text={GHOSTMAPX_CONFIRM_TEXT!r}.",
            "required_confirm_text": GHOSTMAPX_CONFIRM_TEXT,
        }

    adb = client or get_default_client()
    geocode = geocode_address(address, provider=provider, random_radius_meters=random_radius_meters)
    if not geocode.get("ok"):
        return geocode
    coordinates = geocode["coordinates"]
    if not isinstance(coordinates, dict):
        return {"ok": False, "message": "Geocoder returned an invalid coordinate payload."}
    ghostmapx_text = str(coordinates["ghostmapx_text"])

    opened = open_ghostmapx(client=adb)
    if not opened.get("ok"):
        return {"ok": False, "message": "Failed to open Ghostmapx.", "open": opened}

    before = probe_ghostmapx_screen(client=adb)
    coord_text_node = before.get("coord_text")
    if not isinstance(coord_text_node, dict):
        return {
            "ok": False,
            "message": "Ghostmapx coordinate text control was not found.",
            "coordinates": coordinates,
            "screen": _screen_summary(before),
        }

    entered = _enter_manual_coordinates(
        adb,
        coord_text_node,
        longitude=str(coordinates["longitude"]),
        latitude=str(coordinates["latitude"]),
    )
    time.sleep(2)
    after = probe_ghostmapx_screen(client=adb)
    coord_text = _node_text(after.get("coord_text"))
    target_changed = _coord_text_matches(coord_text or "", ghostmapx_text)
    return {
        "ok": bool(entered.get("ok")) and bool(after.get("is_simulating")) and target_changed,
        "message": (
            "Ghostmapx coordinate entered and app reports simulating."
            if bool(entered.get("ok")) and bool(after.get("is_simulating")) and target_changed
            else "Coordinate entry did not produce the expected Ghostmapx coordinate and simulating state."
        ),
        "address": address,
        "coordinates": coordinates,
        "entered": entered,
        "before": _screen_summary(before),
        "after": _screen_summary(after),
    }


def _enter_manual_coordinates(
    adb: AdbClient,
    coord_text_node: dict[str, object],
    *,
    longitude: str,
    latitude: str,
) -> dict[str, object]:
    if not _tap_node_center(adb, coord_text_node):
        return {"ok": False, "message": "Coordinate control bounds were unavailable."}
    time.sleep(0.5)
    dialog = _current_nodes(adb)
    if not _find_text(dialog, "输入坐标"):
        if not _tap_node_center(adb, coord_text_node):
            return {"ok": False, "message": "Manual coordinate dialog did not open."}
        time.sleep(0.5)
        dialog = _current_nodes(adb)
    fields = [node for node in dialog if str(node.get("class", "")).endswith("EditText")]
    if len(fields) < 2:
        return {"ok": False, "message": "Manual coordinate dialog fields were not found."}
    longitude_result = _replace_numeric_field_text(adb, fields[0], f"{float(longitude):.6f}")
    latitude_result = _replace_numeric_field_text(adb, fields[1], f"{float(latitude):.6f}")
    if not longitude_result.get("ok") or not latitude_result.get("ok"):
        return {
            "ok": False,
            "message": "Failed to fill one or more manual coordinate fields.",
            "longitude": longitude_result,
            "latitude": latitude_result,
        }
    refreshed = _current_nodes(adb)
    locate_button = _find_clickable_text(refreshed, "定位")
    if not locate_button:
        adb.shell(["input", "keyevent", "KEYCODE_BACK"])
        time.sleep(0.3)
        refreshed = _current_nodes(adb)
        locate_button = _find_clickable_text(refreshed, "定位")
    if not locate_button:
        return {"ok": False, "message": "Manual coordinate locate button was not found."}
    clicked = _tap_node_center(adb, locate_button)
    return {
        "ok": clicked,
        "message": "Manual coordinate dialog submitted." if clicked else "Failed to tap locate button.",
        "longitude": longitude_result,
        "latitude": latitude_result,
    }


def _replace_numeric_field_text(adb: AdbClient, node: dict[str, object], text: str) -> dict[str, object]:
    if not _tap_node_center(adb, node):
        return {"ok": False, "message": "Field bounds were unavailable."}
    time.sleep(0.2)
    adb.shell(["input", "keyevent", "KEYCODE_MOVE_END"])
    for _ in range(40):
        adb.shell(["input", "keyevent", "KEYCODE_DEL"])
    result = adb.shell(["input", "text", text])
    time.sleep(0.2)
    return {
        "ok": result.ok,
        "message": "Numeric field text entered." if result.ok else "ADB numeric input failed.",
        "returncode": result.returncode,
    }


def _current_nodes(adb: AdbClient) -> list[dict[str, object]]:
    screen = dump_screen_xml(client=adb)
    if not screen.get("ok") or not screen.get("path"):
        return []
    try:
        return parse_ui_xml(str(screen["path"]))
    except Exception:
        return []


def _find_clickable_text(nodes: list[dict[str, object]], text: str) -> dict[str, object] | None:
    for node in nodes:
        if node.get("clickable") and str(node.get("text", "")) == text:
            return node
    return None


def _find_text(nodes: list[dict[str, object]], text: str) -> dict[str, object] | None:
    for node in nodes:
        if str(node.get("text", "")) == text:
            return node
    return None


def _geocode_amap(address: str, *, env: dict[str, str], timeout: float) -> Coordinates:
    key = os.environ.get(GHOSTMAPX_AMAP_KEY_ENV) or env.get(GHOSTMAPX_AMAP_KEY_ENV)
    if not key:
        raise ValueError(f"Missing {GHOSTMAPX_AMAP_KEY_ENV}.")
    params = urlencode({"key": key, "address": address})
    payload = _http_json(f"https://restapi.amap.com/v3/geocode/geo?{params}", timeout=timeout)
    if str(payload.get("status")) != "1" or not payload.get("geocodes"):
        raise ValueError(str(payload.get("info") or "AMap returned no geocodes."))
    geocode = payload["geocodes"][0]
    location = str(geocode.get("location", ""))
    longitude, latitude = _parse_lon_lat(location)
    return Coordinates(longitude=longitude, latitude=latitude, provider="amap", raw=geocode)


def _geocode_nominatim(address: str, *, timeout: float) -> Coordinates:
    params = urlencode({"q": address, "format": "jsonv2", "limit": "1"})
    payload = _http_json(f"https://nominatim.openstreetmap.org/search?{params}", timeout=timeout)
    if not isinstance(payload, list) or not payload:
        raise ValueError("Nominatim returned no results.")
    item = payload[0]
    return Coordinates(
        longitude=float(item["lon"]),
        latitude=float(item["lat"]),
        provider="nominatim",
        raw=item,
    )


def _randomize_coordinates(center: Coordinates, radius_meters: float) -> Coordinates:
    if radius_meters == 0:
        return Coordinates(
            longitude=center.longitude,
            latitude=center.latitude,
            provider=center.provider,
            raw=center.raw,
            center_longitude=center.longitude,
            center_latitude=center.latitude,
            random_radius_meters=0.0,
            random_offset_meters=0.0,
        )

    rng = random.SystemRandom()
    distance = radius_meters * math.sqrt(rng.random())
    angle = rng.random() * math.tau
    north_meters = distance * math.cos(angle)
    east_meters = distance * math.sin(angle)
    latitude_delta = math.degrees(north_meters / EARTH_RADIUS_METERS)
    latitude_radians = math.radians(center.latitude)
    longitude_delta = math.degrees(east_meters / (EARTH_RADIUS_METERS * math.cos(latitude_radians)))
    longitude = center.longitude + longitude_delta
    latitude = center.latitude + latitude_delta
    _validate_coordinates(longitude, latitude)
    return Coordinates(
        longitude=longitude,
        latitude=latitude,
        provider=center.provider,
        raw=center.raw,
        center_longitude=center.longitude,
        center_latitude=center.latitude,
        random_radius_meters=radius_meters,
        random_offset_meters=distance,
    )


def _http_json(url: str, *, timeout: float) -> Any:
    request = Request(url, headers={"User-Agent": "hermes-android-device-controller/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _select_provider(provider: str, env: dict[str, str]) -> str:
    normalized = provider.strip().lower()
    if normalized != "auto":
        return normalized
    if os.environ.get(GHOSTMAPX_AMAP_KEY_ENV) or env.get(GHOSTMAPX_AMAP_KEY_ENV):
        return "amap"
    return "nominatim"


def _replace_field_text(adb: AdbClient, node: dict[str, object], text: str) -> dict[str, object]:
    if not _tap_node_center(adb, node):
        return {"ok": False, "message": "Field bounds were unavailable."}
    adb.shell(["input", "keyevent", "KEYCODE_MOVE_END"])
    for _ in range(80):
        adb.shell(["input", "keyevent", "KEYCODE_DEL"])
    result = _paste_text_via_clipboard(adb, text)
    time.sleep(0.2)
    return {
        "ok": result.ok,
        "message": "Coordinate text entered." if result.ok else "ADB text input failed.",
        "returncode": result.returncode,
    }


def _paste_text_via_clipboard(adb: AdbClient, text: str):
    set_clipboard = adb.shell(["cmd", "clipboard", "set", "text", text])
    if not set_clipboard.ok:
        return set_clipboard
    paste = adb.shell(["input", "keyevent", "KEYCODE_PASTE"])
    adb.shell(["cmd", "clipboard", "set", "text", ""])
    time.sleep(0.2)
    return paste


def _tap_node_center(adb: AdbClient, node: dict[str, object]) -> bool:
    bounds = node.get("bounds")
    if not isinstance(bounds, dict):
        return False
    center_x = bounds.get("center_x")
    center_y = bounds.get("center_y")
    if not isinstance(center_x, int) or not isinstance(center_y, int):
        return False
    return adb.shell(["input", "tap", str(center_x), str(center_y)]).ok


def _format_adb_text(text: str) -> str:
    return "".join(_format_adb_text_char(char) for char in text)


def _format_adb_text_char(char: str) -> str:
    if char == " ":
        return "%s"
    if char in {"&", "|", ";", "<", ">", "(", ")", "$", "`", "\\", '"', "'", "*", "!", "#", "%"}:
        return "\\" + char
    return char


def _find_node_by_suffix(nodes: list[dict[str, object]], resource_suffix: str) -> dict[str, object] | None:
    for node in nodes:
        resource_id = str(node.get("resource_id", ""))
        if resource_id.endswith(resource_suffix):
            return node
    return None


def _is_simulating_label(value: str) -> bool:
    return any(term.lower() in value.lower() for term in SIMULATING_TERMS)


def _screen_summary(screen: dict[str, object]) -> dict[str, object]:
    return {
        "ok": screen.get("ok"),
        "foreground_package": screen.get("foreground_package"),
        "is_foreground": screen.get("is_foreground"),
        "status_label": screen.get("status_label"),
        "is_simulating": screen.get("is_simulating"),
        "coord_text": _node_text(screen.get("coord_text")),
        "xml_path": screen.get("xml_path"),
        "screenshot_path": screen.get("screenshot_path"),
    }


def _node_text(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    text = value.get("text")
    return str(text) if text is not None else None


def _coord_text_matches(actual: str, expected: str) -> bool:
    try:
        actual_lon, actual_lat = _parse_lon_lat(actual)
        expected_lon, expected_lat = _parse_lon_lat(expected)
    except ValueError:
        return False
    return abs(actual_lon - expected_lon) <= 0.00001 and abs(actual_lat - expected_lat) <= 0.00001


def _parse_lon_lat(value: str) -> tuple[float, float]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Invalid longitude,latitude value: {value!r}")
    longitude = float(parts[0])
    latitude = float(parts[1])
    _validate_coordinates(longitude, latitude)
    return longitude, latitude


def _validate_coordinates(longitude: float, latitude: float) -> None:
    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180.")
    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90.")


def _validate_random_radius(value: float) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError("random_radius_meters must be a number.")
    radius = float(value)
    if radius < 0 or radius > 1_000:
        raise ValueError("random_radius_meters must be between 0 and 1000.")
    return radius


def _require_address(address: str) -> str:
    if not isinstance(address, str) or not address.strip():
        raise ValueError("address must be a non-empty string.")
    return address.strip()


def _ghostmapx_package() -> str:
    return os.environ.get(GHOSTMAPX_PACKAGE_ENV, GHOSTMAPX_PACKAGE)


def _resolve_env_path(env_path: str | Path | None = None) -> Path:
    if env_path is not None:
        return Path(env_path)
    return Path.cwd() / ".env"


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
