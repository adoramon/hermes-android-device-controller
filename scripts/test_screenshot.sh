#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="${ROOT_DIR}/src" python3 - <<'PY'
from hermes_android_controller import android_take_screenshot

result = android_take_screenshot()
print(result["message"])
print("path:", result["path"])
raise SystemExit(0 if result["ok"] else 1)
PY
