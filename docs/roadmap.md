# Roadmap

## Phase 1: ADB Control Base

- Create Python package structure.
- Wrap ADB with safe `subprocess.run([...])` calls.
- Provide generic device status, input, screen dump, screenshot, and mock-location broadcast functions.
- Add pytest coverage for command construction.
- Document boundaries and setup.

## Phase 2: Mock Location Helper

- Add an Android helper app under `android-helper/`.
- Receive `com.hermes.mocklocation.SET` broadcasts in authorized test environments.
- Validate extras and expose clear success or failure signals.
- Document installation, permissions, and Developer options setup.

## Later Phases

- Add Hermes skill integration adapters.
- Add richer device health checks and observability.
- Add opt-in test fixtures for controlled Android UI flows.
- Keep enterprise App automation outside this repository unless explicitly scoped, reviewed, and compliant.
