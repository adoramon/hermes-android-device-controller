#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="${ROOT_DIR}/src" python3 - <<'PY'
from hermes_android_controller import android_device_status

status = android_device_status()
print(status["message"])
print("screen_resolution:", status.get("screen_resolution"))
print("foreground_package:", status.get("foreground_package"))
devices = status["devices"]
print(devices.stdout, end="" if str(devices.stdout).endswith("\n") else "\n")
raise SystemExit(0 if status["ok"] else 1)
PY
