#!/usr/bin/env python3
"""Probe one enterprise approval menu without approving anything."""

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
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a single approval menu in dry-run mode.")
    parser.add_argument("--menu", required=True, help="Approval menu name, for example: 工时审批")
    args = parser.parse_args()

    try:
        from hermes_android_controller.enterprise_approval_probe import (
            APPROVAL_MENUS,
            open_main_screen,
            probe_approval_menu,
            return_to_main_screen,
        )

        if args.menu not in APPROVAL_MENUS:
            result = {
                "ok": False,
                "mode": "dry_run",
                "message": f"Unsupported approval menu: {args.menu}",
                "supported_menus": list(APPROVAL_MENUS),
            }
        else:
            open_result = open_main_screen()
            result = probe_approval_menu(args.menu)
            if not result.get("ok") and "not found" in str(result.get("enter", {}).get("message", "")):
                return_to_main_screen()
                open_result = open_main_screen()
                result = probe_approval_menu(args.menu)
            return_result = return_to_main_screen()
            result["open_main_screen"] = open_result
            result["return_to_main_screen"] = return_result
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
