#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="/Users/administrator/Code/hermes-android-device-controller"
PROFILE_DIR="${HOME}/.hermes/profiles/sunny-wechat-lite"
SKILLS_DIR="${PROFILE_DIR}/skills"
LINK_PATH="${SKILLS_DIR}/hermes-android-device-controller-local"

mkdir -p "${SKILLS_DIR}"
ln -sfn "${SOURCE_DIR}" "${LINK_PATH}"

echo "OK linked Hermes skill:"
echo "  ${LINK_PATH} -> $(readlink "${LINK_PATH}")"
ls -ld "${LINK_PATH}"
