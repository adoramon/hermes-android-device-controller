#!/usr/bin/env bash
set -u

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ".env"
  set +a
fi

SOURCE_DIR="${HERMES_ANDROID_SOURCE_DIR:-$(pwd)}"
PROFILE_DIR="${HERMES_PROFILE_DIR:-}"
LINK_NAME="${HERMES_ANDROID_SKILL_LINK_NAME:-hermes-android-device-controller-local}"
LINK_PATH="${PROFILE_DIR}/skills/${LINK_NAME}"
SNAPSHOT_PATH="${PROFILE_DIR}/.skills_prompt_snapshot.json"
SOUL_PATH="${PROFILE_DIR}/SOUL.md"
DEVICE_ID="${ANDROID_DEVICE_ID:-}"
FAILURES=0
WARNINGS=0

ok() {
  printf 'OK   %s\n' "$1"
}

warn() {
  printf 'WARN %s\n' "$1"
  WARNINGS=$((WARNINGS + 1))
}

fail() {
  printf 'FAIL %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}

if [ -z "${PROFILE_DIR}" ]; then
  fail "HERMES_PROFILE_DIR is not set; add it to local .env"
elif [ -L "${LINK_PATH}" ]; then
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

if [ -f "${SNAPSHOT_PATH}" ]; then
  if grep -q "hermes-android-device-controller-local" "${SNAPSHOT_PATH}"; then
    ok "Hermes skills prompt snapshot includes hermes-android-device-controller-local"
  else
    fail "Hermes skills prompt snapshot does not include hermes-android-device-controller-local; restart Hermes to rescan skills"
  fi
else
  warn "Hermes skills prompt snapshot is missing; restart Hermes after linking the skill"
fi

if [ -f "${SOUL_PATH}" ]; then
  if grep -Eq "Android|安卓|Pixel 6|preflight|hermes-android" "${SOUL_PATH}"; then
    ok "SOUL.md contains an Android/preflight routing hint"
  else
    warn "SOUL.md has no Android/preflight routing hint; WeChat routing may fall back to unrelated skills"
  fi
else
  warn "SOUL.md is missing; skipping profile routing hint check"
fi

if [ -z "${DEVICE_ID}" ]; then
  warn "ANDROID_DEVICE_ID is not set; skipping exact-device ADB check"
elif ! command -v adb >/dev/null 2>&1; then
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
  if [ "${WARNINGS}" -gt 0 ]; then
    echo "OK   Hermes profile link verification passed with ${WARNINGS} warning(s)"
  else
    echo "OK   Hermes profile link verification passed"
  fi
  exit 0
fi

echo "FAIL Hermes profile link verification failed with ${FAILURES} issue(s) and ${WARNINGS} warning(s)"
exit 1
