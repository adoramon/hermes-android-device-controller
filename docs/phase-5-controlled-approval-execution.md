# Phase 5: Controlled Approval Execution

Phase 5 adds a controlled execution layer on top of the Phase 4 dry-run approval plan.

## Execution Authorization

Execution is refused unless one of these authorization paths is present:

1. The user provides the exact confirmation phrase:

```text
确认审批
```

2. Local `.env` explicitly enables automatic execution:

```dotenv
OA_APPROVAL_AUTO_EXECUTE=true
OA_APPROVAL_AUTO_EXECUTE_MAX_ITEMS=20
OA_APPROVAL_AUTO_EXECUTE_MENUS=工时审批,考勤异常审批,请假审批,调休时长审批,未打卡审批
```

The command line interface accepts either path:

```bash
PYTHONPATH=src python3 scripts/execute_daily_approval_plan.py --confirm "确认审批"
PYTHONPATH=src python3 scripts/execute_daily_approval_plan.py
```

If neither path is present, the result is refused and no approval action is
performed.

## Supported Menus

The execution layer can route to:

- 工时审批
- 考勤异常审批
- 请假审批
- 调休时长审批
- 未打卡审批

Before execution, it always builds a fresh dry-run plan with:

```bash
PYTHONPATH=src python3 scripts/build_daily_approval_plan.py
```

## Skip Conditions

Menus are skipped when any of these are true:

- `status != has_items`
- `item_count == 0`
- `risk_level == high`
- `suggested_action == needs_manual_review`
- `suggested_action` is not one of the supported execution hints
- Required controls cannot be found
- The page structure changes unexpectedly
- The same page fails twice while looking for confirmation controls

Skipped menus are reported in the result JSON with a reason.
The explicit skip reason for zero-count entries is `item_count=0`.
`unknown` pages and high-risk pages are never executed, even when the confirmation phrase is correct.

## Logs, Screenshots, And XML

Every click records:

- `clicked_text`
- `clicked_bounds`
- `sensitive_action`
- `before_xml_path`
- `before_screenshot_path`
- `after_xml_path`
- `after_screenshot_path`

Sensitive actions include visible controls containing:

```text
确认 / 提交 / 通过 / 同意 / 批准 / 审批
```

The tool must capture XML and screenshot before and after each click.

## Safety Boundary

Phase 5 does not:

- Run automatically unless `OA_APPROVAL_AUTO_EXECUTE=true` is configured in
  local `.env`.
- Bypass risk controls.
- Hide Mock Location.
- Use Root or Hook.
- Execute when both the confirmation phrase and local auto-execute flag are
  absent.
- Execute high-risk or unknown pages.

## WeChat Test Wording

Plan report:

```text
生成打卡审批报告
```

Equivalent longer wording:

```text
生成微信审批计划报告
```

The WeChat report must show only approval type, status, count, details, and
handling method. It must not include XML paths, screenshot paths, or raw JSON.

Dry run:

```text
生成今日审批 Dry Run
```

Controlled execution by chat:

```text
确认审批
```

Automatic execution by local configuration:

```dotenv
OA_APPROVAL_AUTO_EXECUTE=true
```

Hermes should first run the dry-run plan, then execute only eligible low/medium-risk items. If anything is ambiguous, it must stop and return `needs_manual_review`.
Eligible means `status=has_items`, `item_count>0`, non-high risk, and a supported suggested action.
For known WebView batch pages, execution may use fixed, logged coordinates for
the visible select control and approval button when UIAutomator cannot expose
the WebView child controls. Confirmation and after-click screenshots/XML remain
mandatory; if the confirmation page is not recognizable, execution stops with
`needs_manual_review`.
