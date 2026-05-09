# AGENTS.md

## Project Purpose

This repository is a Python-based Android ADB control layer for Hermes, focused
on a USB-connected Pixel 6 test device on macOS.

The package exposes auditable, narrow device-control tools through
`hermes_android_controller.skill_tools`. It supports generic ADB status/input
operations, screen XML/screenshot capture, enterprise App read-only probing,
dry-run OA approval reporting, explicitly confirmed controlled approval
execution, and Ghostmapx address-to-coordinate helpers for an authorized test
device.

## Safety Boundaries

Treat safety constraints as part of the API contract:

- Generic ADB health checks, app launch by explicit package name, tap/swipe/text
  input, keyevents, UI XML dumps, and screenshots are allowed.
- Enterprise App login may use local `.env` credentials, but SMS codes must be
  provided by the user. Do not read SMS or bypass verification.
- Approval menu probing and daily reports are dry-run by default. They must not
  click approve, agree, pass, submit, confirm, or select-all controls.
- Controlled approval execution requires the exact phrase `确认审批` and must
  build a fresh dry-run plan first.
- Pre-final confirmation validation requires the exact phrase `确认执行审批前验证`
  and must not click the final confirmation.
- Ghostmapx coordinate entry requires the exact phrase `确认Ghostmapx测试定位`.
- Do not add risk-control bypasses, anti-detection behavior, Root/Hook logic,
  hidden mock-location behavior, or attendance/check-in automation.
- Do not claim a business action completed unless a local command returned that
  result.

## Repository Layout

- `src/hermes_android_controller/`: Python package and public tool surface.
- `scripts/`: local CLI wrappers and operational checks.
- `tests/`: pytest suite using fake clients/mocks for most behavior.
- `docs/`: phase notes, safety docs, and operational setup.
- `SKILL.md` and `skill.json`: Hermes skill metadata and command mapping.
- `var/`: runtime output/state may be created locally; do not rely on it being
  committed.

## Setup And Test Commands

Use Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Common local checks:

```bash
bash scripts/verify_hermes_profile_link.sh
PYTHONPATH=src python3 scripts/hermes_preflight.py
PYTHONPATH=src python3 scripts/daily_approval_scheduler.py --once
PYTHONPATH=src python3 scripts/daily_approval_scheduler.py --force
```

ADB device checks:

```bash
adb devices -l
PYTHONPATH=src python3 scripts/check_device.py
```

## Key Modules

- `adb_client.py`: small `subprocess.run([...])` wrapper. Keep commands as argv
  lists and return `AdbCommandResult` for auditability.
- `device_status.py`: checks `adb devices`, screen size, and foreground package.
- `input_actions.py`: generic `monkey`, tap, swipe, text, and keyevent helpers.
- `screen_reader.py`: dumps UIAutomator XML and screenshots to local temp paths.
- `app_probe.py`: read-only enterprise App launch, XML parsing, and screen
  summarization. Enterprise package is `com.bonc.mobile.jlmhim.tt`.
- `enterprise_auth.py`: credential login and user-provided SMS-code handling.
- `enterprise_approval_probe.py`: dry-run approval menu detection and plan
  building for `工时审批`, `考勤异常审批`, `请假审批`, `调休时长审批`, `未打卡审批`.
- `approval_report.py`: formats the dry-run plan into WeChat-safe Markdown.
- `enterprise_approval_executor.py`: gated controlled execution with mandatory
  fresh plan, skip rules, click logs, and before/after XML/screenshots.
- `daily_approval_scheduler.py`: one daily randomized dry-run report between
  `14:00` and `16:00`, webhook delivery, local state, and artifact retention.
- `artifact_archive.py`: copies XML/screenshot artifacts from plan output into
  retained run directories.
- `ghostmapx.py`: geocoding, coordinate randomization within 50 meters by
  default, Ghostmapx probing, and explicitly confirmed coordinate entry.
- `skill_tools.py`: public Hermes-facing wrapper functions. Update this and
  `skill.json`/`SKILL.md` when adding or removing public tools.

## Public Tool Surface

The public entrypoint is:

```python
hermes_android_controller.skill_tools
```

When running directly from the repo, set `PYTHONPATH=src`.

Important functions include:

- `android_device_status()`
- `android_open_app(package_name)`
- `android_input_tap(x, y)`
- `android_input_swipe(x1, y1, x2, y2, duration_ms=300)`
- `android_input_text(text)`
- `android_keyevent(code)`
- `android_dump_screen_xml()`
- `android_take_screenshot()`
- `android_open_enterprise_app()`
- `android_probe_current_screen()`
- `android_parse_current_ui()`
- `android_summarize_current_screen()`
- `android_enterprise_login()`
- `android_enterprise_submit_sms_code(code)`
- `android_enterprise_handle_wechat_sms_code(text)`
- `android_detect_approval_menus()`
- `android_build_daily_approval_plan()`
- `android_build_approval_wechat_report()`
- `android_probe_approval_menu(menu_name)`
- `android_execute_daily_approval_plan(confirm_text)`
- `android_validate_approval_confirmation_flow(confirm_text)`
- `android_run_daily_approval_scan_once()`
- `android_force_daily_approval_scan()`
- `android_ghostmapx_geocode(address, provider="auto", random_radius_meters=50)`
- `android_prepare_ghostmapx_location(address, provider="auto", random_radius_meters=50)`
- `android_apply_ghostmapx_location(address, provider="auto", confirm_text="", random_radius_meters=50)`

## Implementation Notes

- Prefer dependency injection with `AdbClient` for testable code.
- Keep ADB invocations auditable: include command, stdout, stderr, return code,
  timeout, and timeout state in returned structures.
- Do not use shell strings for ADB commands when argv lists are possible.
- UI parsing should use `xml.etree.ElementTree`, not ad hoc text matching over
  raw XML.
- For approval execution, skip unknown, empty, high-risk, unsupported, or
  ambiguous pages. Return `needs_manual_review` instead of guessing.
- For sensitive clicks, preserve before/after XML and screenshot paths in logs.
- Daily scheduler configuration is local `.env` driven:
  `OA_APPROVAL_WECHAT_WEBHOOK_URL`, `OA_APPROVAL_WECHAT_WEBHOOK_SECRET`,
  `OA_APPROVAL_WECHAT_CHAT_ID`, `OA_APPROVAL_WINDOW_START`,
  `OA_APPROVAL_WINDOW_END`, and `OA_APPROVAL_STATE_DIR`.
- Do not commit `.env`, runtime state, screenshots, XML dumps, or generated run
  artifacts.

## Testing Guidance

- Run `pytest` after code changes.
- Add focused tests under `tests/` for new behavior. Existing tests use fake ADB
  clients and mocks; follow that pattern rather than requiring a real device.
- For public tool additions, test the core module behavior and verify
  `skill_tools.py`, `skill.json`, and `SKILL.md` stay consistent.
- For scheduler changes, use injected `datetime` values and environment/state
  isolation, as in `tests/test_daily_approval_scheduler.py`.
- For Ghostmapx changes, keep geocoding and UI mutation paths separate so
  coordinate preparation remains safe and testable.

## Current Operational Context

- Hermes profile: `sunny-wechat-lite`.
- Skill link target:
  `~/.hermes/profiles/sunny-wechat-lite/skills/hermes-android-device-controller-local`.
- Target Pixel 6 serial in skill metadata: `25091FDF60030U`.
- Default Ghostmapx package: `com.ghostmapx.app`, overridable with
  `GHOSTMAPX_PACKAGE`.
