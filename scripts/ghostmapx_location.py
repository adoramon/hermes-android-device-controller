#!/usr/bin/env python3
"""Geocode an address and optionally enter it into Ghostmapx."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
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
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address", help="Address to translate into longitude,latitude.")
    parser.add_argument("--provider", default="auto", choices=["auto", "amap", "nominatim"])
    parser.add_argument("--radius-meters", type=float, default=50.0, help="Random radius around the geocoded center. Default: 50.")
    parser.add_argument("--apply", action="store_true", help="Enter the coordinate into Ghostmapx.")
    parser.add_argument("--confirm", default="", help="Required phrase when --apply is used.")
    args = parser.parse_args()

    from hermes_android_controller.ghostmapx import (
        apply_ghostmapx_location,
        prepare_ghostmapx_location,
    )

    if args.apply:
        result = apply_ghostmapx_location(
            args.address,
            provider=args.provider,
            confirm_text=args.confirm,
            random_radius_meters=args.radius_meters,
        )
    else:
        result = prepare_ghostmapx_location(
            args.address,
            provider=args.provider,
            random_radius_meters=args.radius_meters,
        )
    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
