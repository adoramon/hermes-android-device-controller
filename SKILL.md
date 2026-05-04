---
name: hermes-android-device-controller
description: Android ADB device-control verification for the local Pixel 6 test device, including status, generic input primitives, screen dump, screenshot, and authorized mock-location helper checks.
version: 0.1.0
platforms: [macos]
metadata:
  hermes:
    tags: [android, adb, device-control, testing]
---

# Hermes Android Device Controller

Use this skill only for local Android device-control verification through the repository at:

```bash
/Users/administrator/Code/hermes-android-device-controller
```

Target device:

```text
Pixel 6 ADB serial: 25091FDF60030U
```

## Scope

Allowed:

- Check ADB device status.
- Open Android packages by explicit package name.
- Use generic ADB input primitives: tap, swipe, text, keyevent.
- Dump current screen XML or take screenshots for debugging.
- Set mock location only through the authorized Hermes Mock Location Helper App in test environments.

Not allowed:

- Do not implement or run enterprise App attendance/check-in flows.
- Do not bypass risk controls, hide mock location, evade detection, use Root/Hook, or add anti-detection behavior.
- Do not claim a business action completed unless a local command actually returned that result.

## Tool Entrypoint

Python tools are exported from:

```python
hermes_android_controller.skill_tools
```

Run Python from the repo with `PYTHONPATH=src` unless the package has already been installed:

```bash
cd /Users/administrator/Code/hermes-android-device-controller
PYTHONPATH=src python3 -c 'from hermes_android_controller.skill_tools import android_device_status; print(android_device_status()["message"])'
```

Available functions:

- `android_device_status()`
- `android_open_app(package_name)`
- `android_input_tap(x, y)`
- `android_input_swipe(x1, y1, x2, y2, duration_ms=300)`
- `android_input_text(text)`
- `android_keyevent(code)`
- `android_dump_screen_xml()`
- `android_take_screenshot()`
- `android_set_mock_location(lat, lon, accuracy=10)`

## Preflight

Before relying on the Android tools from Hermes, run:

```bash
cd /Users/administrator/Code/hermes-android-device-controller
bash scripts/verify_hermes_profile_link.sh
PYTHONPATH=src python3 scripts/hermes_preflight.py
```

The preflight only checks imports, ADB status, and the mock-location helper broadcast. It does not operate any enterprise App.
