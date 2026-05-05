#!/usr/bin/env python3
"""Submit a user-provided enterprise app SMS verification code."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
import sys
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


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        result = {
            "ok": False,
            "message": "Usage: submit_enterprise_sms_code.py <4-8 digit code>",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    try:
        from hermes_android_controller.enterprise_auth import submit_sms_code

        result = submit_sms_code(argv[1])
    except Exception as exc:  # pragma: no cover - diagnostic script
        result = {
            "ok": False,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result.get("ok") or result.get("need_manual_confirm") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
