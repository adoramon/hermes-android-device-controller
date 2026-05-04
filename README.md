# hermes-android-device-controller

Hermes Android Device Controller is a Python-based ADB control base for a USB-connected Pixel 6 on a Mac mini. It provides a narrow, auditable device-control layer for Hermes Android execution environments.

This repository intentionally does not implement real attendance, approval, risk-control bypass, fake check-in, or enterprise App automation workflows. Phase 1 is limited to generic ADB primitives and local device self-tests.

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

## Pixel Settings

On the Pixel 6:

1. Open Settings > About phone, tap Build number seven times to enable Developer options.
2. Open Settings > System > Developer options.
3. Enable USB debugging.
4. Keep the screen unlocked for the first authorization prompt.
5. For future mock-location work, select the Hermes Mock Location Helper App as the mock location app only in authorized test environments.

## Provided Tool Functions

- `android_device_status()`
- `android_open_app(package_name)`
- `android_input_tap(x, y)`
- `android_input_swipe(x1, y1, x2, y2, duration_ms=300)`
- `android_input_text(text)`
- `android_keyevent(code)`
- `android_dump_screen_xml()`
- `android_take_screenshot()`
- `android_set_mock_location(lat, lon, accuracy=10)`

`android_set_mock_location` currently sends an ADB broadcast to `com.hermes.mocklocation.SET`. It expects a future Hermes Mock Location Helper App to receive the broadcast in authorized test environments.

## Phase 1 Self-Test Commands

```bash
pytest
bash scripts/check_device.sh
bash scripts/dump_screen.sh
bash scripts/test_input.sh
bash scripts/test_screenshot.sh
python scripts/test_mock_location.py 31.2304 121.4737 25
```

The scripts call generic ADB primitives only. They do not automate any business App workflow.

## Phase 2 Mock Location Helper

The Android helper app lives in `android-helper/`.

Build:

```bash
cd android-helper
./gradlew :app:assembleDebug
```

This requires Android SDK Platform 36 via `ANDROID_HOME` or `android-helper/local.properties`.

Install:

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Select `Hermes Mock Location Helper` in Pixel Developer options > Select mock location app, then test:

```bash
adb shell am broadcast -a com.hermes.mocklocation.SET --ef lat 31.2304 --ef lon 121.4737 --ef accuracy 10
adb logcat -s HermesMockLocation
```
