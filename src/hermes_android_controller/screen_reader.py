"""Screen inspection helpers over ADB."""

from __future__ import annotations

from pathlib import Path
import tempfile
import uuid

from .adb_client import AdbClient, get_default_client


DEVICE_XML_PATH = "/sdcard/hermes_screen.xml"
DEVICE_SCREENSHOT_PATH = "/sdcard/hermes_screenshot.png"


def dump_screen_xml(client: AdbClient | None = None) -> dict[str, object]:
    adb = client or get_default_client()
    remote_dump = adb.shell(["uiautomator", "dump", DEVICE_XML_PATH])
    if not remote_dump.ok:
        return {
            "ok": False,
            "path": None,
            "dump": remote_dump,
            "pull": None,
            "message": "Failed to dump screen XML on device.",
        }
    local_path = _local_temp_path("hermes_screen_", ".xml")
    pull = adb.run(["pull", DEVICE_XML_PATH, str(local_path)])
    return {
        "ok": pull.ok,
        "path": str(local_path) if pull.ok else None,
        "dump": remote_dump,
        "pull": pull,
        "message": "Screen XML dumped." if pull.ok else "Failed to pull screen XML to local temp directory.",
    }


def take_screenshot(client: AdbClient | None = None) -> dict[str, object]:
    adb = client or get_default_client()
    capture = adb.shell(["screencap", "-p", DEVICE_SCREENSHOT_PATH])
    if not capture.ok:
        return {
            "ok": False,
            "path": None,
            "capture": capture,
            "pull": None,
            "message": "Failed to capture screenshot on device.",
        }
    local_path = _local_temp_path("hermes_screenshot_", ".png")
    pull = adb.run(["pull", DEVICE_SCREENSHOT_PATH, str(local_path)])
    return {
        "ok": pull.ok,
        "path": str(local_path) if pull.ok else None,
        "capture": capture,
        "pull": pull,
        "message": "Screenshot captured." if pull.ok else "Failed to pull screenshot to local temp directory.",
    }


def _local_temp_path(prefix: str, suffix: str) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="hermes_android_"))
    return temp_dir / f"{prefix}{uuid.uuid4().hex}{suffix}"
