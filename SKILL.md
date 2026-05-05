---
name: hermes-android-device-controller
description: Pixel 6 / Android ADB 本机控制与企业 App 审批辅助：检查设备状态、运行 Hermes Android preflight、截图/XML、生成打卡审批报告/微信审批计划报告。
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
- Perform authorized enterprise App login with local credentials and user-provided SMS verification code.

Not allowed:

- Do not implement or run enterprise App attendance/check-in flows.
- Do not read SMS messages or bypass SMS verification.
- Do not submit enterprise App approval or business forms.
- Do not bypass risk controls, hide mock location, evade detection, use Root/Hook, or add anti-detection behavior.
- Do not claim a business action completed unless a local command actually returned that result.

## When To Use

Use this skill when the user asks in Chinese or English for:

- `检查 Pixel 6 ADB 状态`
- `检查安卓手机状态`
- `检查 Android 设备连接`
- `运行 Android preflight`
- `运行 Hermes Android preflight`
- `测试 Mock Location Helper`
- `测试安卓截图 / dump XML / ADB 输入`
- `用 Hermes 控制 Pixel 6`
- `android_device_status`
- `android_set_mock_location`
- `打开企业 App`
- `企业 App 登录`
- `企信登录`
- `企信验证码：123456`
- `android_enterprise_login`
- `android_enterprise_handle_wechat_sms_code`
- `生成审批 Dry Run`
- `构建每日审批计划`
- `生成微信审批计划报告`
- `生成打卡审批报告`
- `打卡审批报告`
- `审批菜单探测`
- `android_build_daily_approval_plan`
- `android_build_approval_wechat_report`
- `确认审批`
- `android_execute_daily_approval_plan`

For status or preflight requests, run the local scripts first and answer only from the command JSON/output. Do not freely infer device state from old chat history.
For enterprise login requests, use local `.env` credentials only. If SMS verification is required, ask the user to reply exactly `企信验证码：xxxxxx`; do not read SMS or bypass verification.
For approval menu requests, only run dry-run probes. Do not click approve, agree, pass, submit, confirm, or select-all controls.
For WeChat approval plan reports, treat `生成打卡审批报告`, `打卡审批报告`, and `生成微信审批计划报告` as equivalent. Use `android_build_approval_wechat_report()` and return only the Markdown table plus the confirmation prompt. Do not include `risk_level`, XML paths, screenshot paths, or raw JSON in the WeChat reply.
For controlled approval execution, require the exact phrase `确认审批`, build a fresh dry-run plan first, skip ineligible/unknown/manual-review menus, and record before/after XML and screenshots for every click.

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
- `android_open_enterprise_app()`
- `android_probe_current_screen()`
- `android_parse_current_ui()`
- `android_summarize_current_screen()`
- `android_enterprise_login()`
- `android_enterprise_detect_sms_code()`
- `android_enterprise_submit_sms_code(code)`
- `android_enterprise_handle_wechat_sms_code(text)`
- `android_detect_approval_menus()`
- `android_build_daily_approval_plan()`
- `android_build_approval_wechat_report()`
- `android_probe_approval_menu(menu_name)`
- `android_execute_daily_approval_plan(confirm_text)`
- `android_execute_work_hour_approval(confirm_text)`
- `android_execute_attendance_exception_approval(confirm_text)`
- `android_execute_leave_approval(confirm_text)`
- `android_execute_comp_time_approval(confirm_text)`
- `android_execute_missing_clock_approval(confirm_text)`

## Command Mapping

Check whether the profile link, Skill files, Python package path, and Pixel 6 ADB device are visible:

```bash
cd /Users/administrator/Code/hermes-android-device-controller && bash scripts/verify_hermes_profile_link.sh
```

Run the full Hermes preflight:

```bash
cd /Users/administrator/Code/hermes-android-device-controller && PYTHONPATH=src python3 scripts/hermes_preflight.py
```

Check device status only:

```bash
cd /Users/administrator/Code/hermes-android-device-controller && PYTHONPATH=src python3 -c 'from hermes_android_controller.skill_tools import android_device_status; import json; print(json.dumps(android_device_status(), default=lambda o: o.to_dict() if hasattr(o, "to_dict") else str(o), ensure_ascii=False, indent=2))'
```

Run authorized enterprise App login:

```bash
cd /Users/administrator/Code/hermes-android-device-controller && PYTHONPATH=src python3 scripts/enterprise_login.py
```

Submit a user-provided SMS verification code:

```bash
cd /Users/administrator/Code/hermes-android-device-controller && PYTHONPATH=src python3 scripts/submit_enterprise_sms_code.py 123456
```

Build the dry-run daily approval plan:

```bash
cd /Users/administrator/Code/hermes-android-device-controller && PYTHONPATH=src python3 scripts/build_daily_approval_plan.py
```

Build the WeChat approval plan report:

```bash
cd /Users/administrator/Code/hermes-android-device-controller && PYTHONPATH=src python3 -c 'from hermes_android_controller.skill_tools import android_build_approval_wechat_report; print(android_build_approval_wechat_report()["markdown"])'
```

Execute the controlled approval plan only after exact confirmation:

```bash
cd /Users/administrator/Code/hermes-android-device-controller && PYTHONPATH=src python3 scripts/execute_daily_approval_plan.py --confirm "确认审批"
```

## Preflight

Before relying on the Android tools from Hermes, run:

```bash
cd /Users/administrator/Code/hermes-android-device-controller
bash scripts/verify_hermes_profile_link.sh
PYTHONPATH=src python3 scripts/hermes_preflight.py
```

The preflight only checks imports, ADB status, and the mock-location helper broadcast. It does not operate any enterprise App.
