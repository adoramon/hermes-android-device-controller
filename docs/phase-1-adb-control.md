# Phase 1: ADB Control

Phase 1 establishes a small Python abstraction over ADB for a USB-connected Pixel 6.

## Scope

- Detect authorized ADB devices.
- Launch an app by package name.
- Send tap, swipe, and text input events.
- Dump UI XML through `uiautomator`.
- Capture screenshots through `screencap`.
- Send a mock-location broadcast for a future helper app.

## Implementation Rules

- Use `subprocess.run` with list arguments.
- Do not use `shell=True`.
- Capture stdout and stderr for every command.
- Include a timeout for every command.
- Preserve command and return code in the result.

## Out of Scope

- Real attendance, approval, HR, finance, or other enterprise App automation.
- Circumventing app security, risk controls, device integrity checks, or access controls.
- Installing or configuring unauthorized mock-location flows.
