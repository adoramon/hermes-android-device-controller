#!/usr/bin/env python3
"""Build a dry-run enterprise approval plan without approving anything."""

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


def main() -> int:
    try:
        from hermes_android_controller.enterprise_approval_probe import build_daily_approval_plan

        result = build_daily_approval_plan()
    except Exception as exc:  # pragma: no cover - diagnostic script
        result = {
            "ok": False,
            "mode": "dry_run",
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
