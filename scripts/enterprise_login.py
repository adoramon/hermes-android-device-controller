#!/usr/bin/env python3
"""Run authorized enterprise app login using local .env credentials."""

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
        from hermes_android_controller.enterprise_auth import login_with_credentials

        result = login_with_credentials()
    except Exception as exc:  # pragma: no cover - diagnostic script
        result = {
            "ok": False,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result.get("ok") or result.get("need_sms_code") else 1


if __name__ == "__main__":
    raise SystemExit(main())
