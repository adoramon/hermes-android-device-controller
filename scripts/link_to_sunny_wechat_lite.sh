#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ".env"
  set +a
fi

SOURCE_DIR="${HERMES_ANDROID_SOURCE_DIR:-$(pwd)}"
PROFILE_DIR="${HERMES_PROFILE_DIR:?Set HERMES_PROFILE_DIR in .env before linking the Hermes skill.}"
SKILLS_DIR="${PROFILE_DIR}/skills"
LINK_NAME="${HERMES_ANDROID_SKILL_LINK_NAME:-hermes-android-device-controller-local}"
LINK_PATH="${SKILLS_DIR}/${LINK_NAME}"

mkdir -p "${SKILLS_DIR}"
ln -sfn "${SOURCE_DIR}" "${LINK_PATH}"

echo "OK linked Hermes skill:"
echo "  ${LINK_PATH} -> $(readlink "${LINK_PATH}")"
ls -ld "${LINK_PATH}"
