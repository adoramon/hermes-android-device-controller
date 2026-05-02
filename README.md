# hermes-android-device-controller

Hermes Android Device Controller is a Python-based ADB control base for a USB-connected Pixel 6 on a Mac mini. It provides a narrow, auditable device-control layer for Hermes execution environments.

This repository intentionally does not implement real attendance, approval, risk-control bypass, or enterprise App automation workflows. The current phase only prepares the GitHub project framework and generic ADB primitives.

## Project Layout

```text
src/hermes_android_controller/   Python package
scripts/                         Local self-check scripts
tests/                           pytest tests
docs/                            Design and safety documentation
android-helper/                  Placeholder for the future helper app
```

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## ADB Prerequisites

1. Install Android Platform Tools so `adb` is available on `PATH`.
2. Enable Developer options and USB debugging on the Pixel 6.
3. Connect the device to the Mac mini over USB.
4. Accept the Android USB debugging authorization prompt.
5. Confirm exactly one authorized device is visible:

```bash
adb devices -l
```

## Provided Tool Functions

- `device_status()`
- `open_app(package_name)`
- `tap(x, y)`
- `swipe(x1, y1, x2, y2, duration_ms)`
- `input_text(text)`
- `dump_screen_xml()`
- `take_screenshot()`
- `set_mock_location(lat, lon, accuracy)`

`set_mock_location` currently checks for helper package `com.hermes.mocklocation`, then sends an ADB broadcast to `com.hermes.mocklocation.SET`. It expects a future Hermes Mock Location Helper App to be installed, selected as the Android mock location app, and authorized for test environments.

## Self-Test Commands

```bash
pytest
python scripts/check_device.py
python scripts/dump_screen.py
python scripts/test_mock_location.py 31.2304 121.4737 25
```

The scripts call generic ADB primitives only. They do not automate any business App workflow.
