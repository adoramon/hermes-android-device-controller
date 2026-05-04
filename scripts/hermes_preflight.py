#!/usr/bin/env python3
"""Hermes profile preflight for Android controller import and device checks."""

from __future__ import annotations

from dataclasses import is_dataclass, asdict
import json
import traceback
from typing import Any


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _command_summary(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    result = _jsonable(value)
    if not isinstance(result, dict):
        return None
    returncode = result.get("returncode")
    timed_out = bool(result.get("timed_out", False))
    return {
        "ok": returncode == 0 and not timed_out,
        "command": result.get("command"),
        "returncode": returncode,
        "timed_out": timed_out,
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
    }


def _status_summary(status: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": status.get("ok"),
        "message": status.get("message"),
        "screen_resolution": status.get("screen_resolution"),
        "foreground_package": status.get("foreground_package"),
        "devices": _command_summary(status.get("devices")),
        "screen_size": _command_summary(status.get("screen_size")),
    }


def _mock_location_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": result.get("ok"),
        "message": result.get("message"),
        "result": _command_summary(result.get("result")),
    }


def main() -> int:
    report: dict[str, Any] = {
        "ok": False,
        "checks": {},
    }

    try:
        from hermes_android_controller.skill_tools import (
            android_device_status,
            android_set_mock_location,
        )

        report["checks"]["python_import"] = {
            "ok": True,
            "module": "hermes_android_controller.skill_tools",
        }
    except Exception as exc:  # pragma: no cover - diagnostic script
        report["checks"]["python_import"] = {
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        print(json.dumps(_jsonable(report), ensure_ascii=False, indent=2))
        return 1

    try:
        status = android_device_status()
        report["checks"]["android_device_status"] = _status_summary(status)
    except Exception as exc:  # pragma: no cover - diagnostic script
        report["checks"]["android_device_status"] = {
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    try:
        mock_location = android_set_mock_location(31.2304, 121.4737, 10)
        report["checks"]["android_set_mock_location"] = _mock_location_summary(mock_location)
    except Exception as exc:  # pragma: no cover - diagnostic script
        report["checks"]["android_set_mock_location"] = {
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    report["ok"] = all(
        bool(check.get("ok")) if isinstance(check, dict) else False
        for check in report["checks"].values()
    )
    print(json.dumps(_jsonable(report), ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
