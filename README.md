# hermes-android-device-controller

Hermes Android Device Controller is a Python-based ADB control base for a USB-connected Pixel 6 on a Mac mini. It provides a narrow, auditable device-control layer for Hermes Android execution environments.

This repository intentionally does not implement real attendance, approval, risk-control bypass, fake check-in, or enterprise App automation workflows. Phase 1 is limited to generic ADB primitives and local device self-tests. Phase 2.5 is limited to Hermes Skill/profile integration and local device-control verification.

## Project Layout

```text
src/hermes_android_controller/   Python package
scripts/                         Local self-check scripts
tests/                           pytest tests
docs/                            Design and safety documentation
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

## Provided Tool Functions

- `android_device_status()`
- `android_open_app(package_name)`
- `android_input_tap(x, y)`
- `android_input_swipe(x1, y1, x2, y2, duration_ms=300)`
- `android_input_text(text)`
- `android_keyevent(code)`
- `android_dump_screen_xml()`
- `android_take_screenshot()`

## Phase 1 Self-Test Commands

```bash
pytest
bash scripts/check_device.sh
bash scripts/dump_screen.sh
bash scripts/test_input.sh
bash scripts/test_screenshot.sh
```

The scripts call generic ADB primitives only. They do not automate any business App workflow.

## Phase 2.5 Hermes Profile Integration

The local Hermes Skill can be linked into the `sunny-wechat-lite` profile:

```bash
cd /Users/administrator/Code/hermes-android-device-controller
bash scripts/link_to_sunny_wechat_lite.sh
```

Verify the profile link, Skill files, Python package path, and Pixel 6 ADB visibility:

```bash
bash scripts/verify_hermes_profile_link.sh
```

Run the Hermes preflight from the repo root:

```bash
PYTHONPATH=src python3 scripts/hermes_preflight.py
```

The preflight imports `hermes_android_controller.skill_tools` and calls `android_device_status()`. It does not operate any enterprise App.

After creating or changing the Skill link, restart Hermes so the `sunny-wechat-lite` profile rescans Skills. See [docs/phase-2.5-hermes-profile-integration.md](docs/phase-2.5-hermes-profile-integration.md) for restart notes, WeChat test wording, and troubleshooting.

## Daily OA Approval Report Automation

The daily OA approval scheduler can generate one dry-run approval report at a
random time between 14:00 and 16:00, push the Markdown table to WeChat, and wait
for the user to reply `确认审批` before any controlled execution occurs.

See [docs/phase-6-daily-oa-approval-automation.md](docs/phase-6-daily-oa-approval-automation.md).

## Ghostmapx Test-Device Location Helper

Ghostmapx support is limited to address geocoding and visible UI control on the
user's own Android test device. It must not be connected to attendance,
check-in, enterprise workflows, risk-control bypass, hidden mock location,
Root/Hook, or anti-detection behavior.

Each address is translated to a center point, then the coordinate entered into
Ghostmapx is randomized within a 50 meter radius so repeated uses of the same
address do not produce the exact same coordinate:

```bash
PYTHONPATH=src python3 scripts/ghostmapx_location.py "上海市人民广场"
PYTHONPATH=src python3 scripts/ghostmapx_location.py "上海市人民广场" --apply --confirm 确认Ghostmapx测试定位
```
