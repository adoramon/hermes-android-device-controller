#!/usr/bin/env bash
set -u

SOURCE_DIR="/Users/administrator/Code/hermes-android-device-controller"
PROFILE_DIR="${HOME}/.hermes/profiles/sunny-wechat-lite"
LINK_PATH="${PROFILE_DIR}/skills/hermes-android-device-controller-local"
DEVICE_ID="25091FDF60030U"
FAILURES=0

ok() {
  printf 'OK   %s\n' "$1"
}

fail() {
  printf 'FAIL %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}

if [ -L "${LINK_PATH}" ]; then
  TARGET="$(readlink "${LINK_PATH}")"
  if [ "${TARGET}" = "${SOURCE_DIR}" ]; then
    ok "Hermes skill link points to ${SOURCE_DIR}"
  else
    fail "Hermes skill link points to ${TARGET}, expected ${SOURCE_DIR}"
  fi
else
  fail "Hermes skill link is missing: ${LINK_PATH}"
fi

if [ -f "${LINK_PATH}/skill.json" ]; then
  ok "skill.json exists"
  if python3 - "${LINK_PATH}/skill.json" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

assert data.get("name") == "hermes-android-device-controller"
assert data.get("entrypoint") == "hermes_android_controller.skill_tools"
assert data.get("pythonPath") == "src"
assert isinstance(data.get("tools"), list) and data["tools"]
PY
  then
    ok "skill.json metadata is valid"
  else
    fail "skill.json metadata is invalid"
  fi
else
  fail "skill.json is missing"
fi

if [ -f "${LINK_PATH}/SKILL.md" ]; then
  ok "SKILL.md exists for Hermes skill loading"
else
  fail "SKILL.md is missing"
fi

if [ -d "${LINK_PATH}/src/hermes_android_controller" ]; then
  ok "src/hermes_android_controller exists"
else
  fail "src/hermes_android_controller is missing"
fi

if ! command -v adb >/dev/null 2>&1; then
  fail "adb is not on PATH"
else
  ADB_OUTPUT="$(adb devices 2>&1)"
  if printf '%s\n' "${ADB_OUTPUT}" | grep -Eq "^${DEVICE_ID}[[:space:]]+device($|[[:space:]])"; then
    ok "adb sees authorized Pixel 6 device ${DEVICE_ID}"
  elif printf '%s\n' "${ADB_OUTPUT}" | grep -Eq "^${DEVICE_ID}[[:space:]]+unauthorized($|[[:space:]])"; then
    fail "Pixel 6 ${DEVICE_ID} is unauthorized; accept the USB debugging prompt"
  elif printf '%s\n' "${ADB_OUTPUT}" | grep -Eq "^${DEVICE_ID}[[:space:]]+offline($|[[:space:]])"; then
    fail "Pixel 6 ${DEVICE_ID} is offline; reconnect USB or restart adb server"
  else
    fail "adb devices does not list ${DEVICE_ID}"
    printf '%s\n' "${ADB_OUTPUT}"
  fi
fi

if [ "${FAILURES}" -eq 0 ]; then
  echo "OK   Hermes profile link verification passed"
  exit 0
fi

echo "FAIL Hermes profile link verification failed with ${FAILURES} issue(s)"
exit 1
