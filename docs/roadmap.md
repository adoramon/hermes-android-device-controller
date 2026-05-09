# Roadmap

## Phase 1: ADB Control Base

- Create Python package structure.
- Wrap ADB with safe `subprocess.run([...])` calls.
- Provide generic device status, input, screen dump, and screenshot functions.
- Add pytest coverage for command construction.
- Document boundaries and setup.

## Retired: Mock Location Helper

- The Android helper app under `android-helper/` has been removed.
- Hermes no longer exposes `android_set_mock_location`.

## Later Phases

- Add Hermes skill integration adapters.
- Add richer device health checks and observability.
- Add opt-in test fixtures for controlled Android UI flows.
- Keep enterprise App automation outside this repository unless explicitly scoped, reviewed, and compliant.
