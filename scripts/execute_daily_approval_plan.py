#!/usr/bin/env python3
"""Execute the controlled daily approval plan after chat or local env authorization."""

from __future__ import annotations

import argparse
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
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value, key=str)]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm",
        default="",
        help="Must equal 确认审批 unless OA_APPROVAL_AUTO_EXECUTE=true is set in local env.",
    )
    args = parser.parse_args()
    try:
        from hermes_android_controller.enterprise_approval_executor import execute_daily_approval_plan

        result = execute_daily_approval_plan(args.confirm)
    except Exception as exc:  # pragma: no cover - diagnostic script
        result = {
            "ok": False,
            "mode": "controlled_execution",
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
