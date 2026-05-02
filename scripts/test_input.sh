#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="${ROOT_DIR}/src" python3 - <<'PY'
from hermes_android_controller import android_input_tap, android_keyevent

tap = android_input_tap(100, 100)
print("tap:", tap.to_dict())
back = android_keyevent(4)
print("back:", back.to_dict())
raise SystemExit(0 if tap.ok and back.ok else 1)
PY
