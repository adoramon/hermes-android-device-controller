#!/usr/bin/env python3
"""Open the enterprise app and produce a read-only UI probe summary."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
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
    timed_out = bool(result.get("timed_out", False))
    return {
        "ok": result.get("returncode") == 0 and not timed_out,
        "command": result.get("command"),
        "returncode": result.get("returncode"),
        "timed_out": timed_out,
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
    }


def _compact_probe(summary: dict[str, Any]) -> dict[str, Any]:
    probe = summary.get("probe")
    if not isinstance(probe, dict):
        return summary
    compact = dict(summary)
    compact["probe"] = {
        "ok": probe.get("ok"),
        "foreground_package": probe.get("foreground_package"),
        "xml_path": probe.get("xml_path"),
        "screenshot_path": probe.get("screenshot_path"),
        "status_message": (probe.get("status") or {}).get("message")
        if isinstance(probe.get("status"), dict)
        else None,
        "xml_dump": _command_summary((probe.get("xml") or {}).get("dump"))
        if isinstance(probe.get("xml"), dict)
        else None,
        "xml_pull": _command_summary((probe.get("xml") or {}).get("pull"))
        if isinstance(probe.get("xml"), dict)
        else None,
        "screenshot_capture": _command_summary((probe.get("screenshot") or {}).get("capture"))
        if isinstance(probe.get("screenshot"), dict)
        else None,
        "screenshot_pull": _command_summary((probe.get("screenshot") or {}).get("pull"))
        if isinstance(probe.get("screenshot"), dict)
        else None,
        "diagnostics": _compact_diagnostics(probe.get("diagnostics")),
    }
    return compact


def _compact_diagnostics(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    foreground = value.get("foreground_stability")
    xml_attempts = value.get("xml_dump_attempts")
    return {
        "foreground_stability": {
            "ok": foreground.get("ok"),
            "stable": foreground.get("stable"),
            "foreground_package": foreground.get("foreground_package"),
            "expected_package": foreground.get("expected_package"),
            "observations": [
                {
                    "attempt": item.get("attempt"),
                    "ok": item.get("ok"),
                    "foreground_package": item.get("foreground_package"),
                    "message": item.get("message"),
                }
                for item in foreground.get("observations", [])
                if isinstance(item, dict)
            ],
        }
        if isinstance(foreground, dict)
        else None,
        "xml_dump_attempts": xml_attempts if isinstance(xml_attempts, list) else [],
    }


def main() -> int:
    report: dict[str, Any] = {
        "ok": False,
        "enterprise_app_package": "configured-in-env",
        "safety": {
            "read_only": True,
            "business_submit": False,
            "approval_submit": False,
            "risk_bypass": False,
        },
    }
    try:
        from hermes_android_controller.app_probe import open_enterprise_app, summarize_screen

        launch = open_enterprise_app()
        report["launch"] = _command_summary(launch)
        if not launch.ok:
            report["message"] = "Failed to open enterprise app."
            print(json.dumps(_jsonable(report), ensure_ascii=False, indent=2))
            return 1

        summary = summarize_screen()
        report["summary"] = _compact_probe(summary)
        report["ok"] = bool(summary.get("ok"))
        report["message"] = "Enterprise app UI probe completed." if report["ok"] else "Enterprise app UI probe failed."
    except Exception as exc:  # pragma: no cover - diagnostic script
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()

    print(json.dumps(_jsonable(report), ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
