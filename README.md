# hermes-android-device-controller

Hermes Android Device Controller is a Python-based ADB control base for a USB-connected Android test device on macOS. It provides a narrow, auditable device-control layer for Hermes Android execution environments.

This repository intentionally does not implement attendance/check-in, risk-control bypass, fake check-in, or hidden automation workflows. Approval execution is limited to controlled, auditable flows gated by either the `确认审批` phrase or local `.env` setting `OA_APPROVAL_AUTO_EXECUTE=true`.

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

The local Hermes Skill can be linked into the configured Hermes profile:

```bash
cd $HERMES_ANDROID_SOURCE_DIR
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

After creating or changing the Skill link, restart Hermes so the configured Hermes profile rescans Skills. See [docs/phase-2.5-hermes-profile-integration.md](docs/phase-2.5-hermes-profile-integration.md) for restart notes, WeChat test wording, and troubleshooting.

## Daily OA Approval Report Automation

The daily OA approval scheduler can generate one dry-run approval report at a
random time between 14:00 and 16:00 and push the Markdown table to WeChat. It
waits for `确认审批` by default; if local `.env` sets
`OA_APPROVAL_AUTO_EXECUTE=true`, it can execute eligible controlled approvals
without a chat confirmation, push a second execution-result message, and return
to the approval menu home before reporting completion. Missed jobs are not run
after the configured end time.

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

For local test rigs where WeChat location simulation should run without a second
chat confirmation, set `GHOSTMAPX_AUTO_APPLY=true` in local `.env`. The tool
still reports failure unless Ghostmapx opens, the coordinate is entered, and the
app reports a simulating state. After a successful simulation it sends Android
Home so the device is left on the desktop.

Ghostmapx also supports local `.env` aliases for WeChat-style requests:

- `GHOSTMAPX_LOCATION_COMPANY` for `模拟到公司`
- `GHOSTMAPX_LOCATION_GUANGZHOU` for `模拟广州`
- `GHOSTMAPX_LOCATION_FUZHOU` for `模拟福州`

For aliases that should not depend on online geocoding, set local coordinate
fallbacks as `longitude,latitude`:

- `GHOSTMAPX_COORD_COMPANY`
- `GHOSTMAPX_COORD_GUANGZHOU`
- `GHOSTMAPX_COORD_FUZHOU`

Free-form requests such as `模拟到上海市人民广场` are treated as direct
addresses.
