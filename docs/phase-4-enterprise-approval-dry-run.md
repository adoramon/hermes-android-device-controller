# Phase 4: Enterprise Approval Dry Run

Phase 4 models enterprise app approval menus without performing real approval actions.

Target menus:

- 工时审批
- 考勤异常审批
- 请假审批
- 调休时长审批
- 未打卡审批

## Business Flow

The dry-run probe:

1. Opens the enterprise app main screen.
2. Detects known approval menu entries from UIAutomator XML.
3. Enters each detected menu.
4. Captures a screenshot and UI XML.
5. Determines whether the page is empty, has items, or is unknown.
6. Extracts visible project, employee, request, and count hints.
7. Returns to the main screen with Android Back.
8. Emits a daily approval plan JSON.

The probe may tap menu entries and Back only. It must not tap final approval actions.

## Dry Run Output

The top-level output shape is:

```json
{
  "ok": true,
  "mode": "dry_run",
  "menus": [
    {
      "menu_name": "工时审批",
      "status": "has_items",
      "item_count": 3,
      "items": [],
      "suggested_action": "needs_manual_review",
      "risk_level": "medium",
      "screenshot_path": "...",
      "xml_path": "..."
    }
  ]
}
```

Possible `status` values:

- `has_items`
- `empty`
- `unknown`

`has_items` is only allowed when `item_count > 0`. Header-only labels such as
`我管理的项目`, `我管理的员工`, and nodes with `web_title` identifiers are not
approval items.

Menu-specific item rules:

- 工时审批: requires `待审批X人` with `X > 0`.
- 考勤异常审批, 调休时长审批, 未打卡审批: requires a real employee/request row or a positive pending count.
- 请假审批: requires a positive pending count or a real leave request card.
- If a page is not visibly empty but no real item can be identified, it is marked `unknown` with `suggested_action=needs_manual_review`.

Some enterprise pages render their list inside `android.webkit.WebView` without
exposing row text to UIAutomator XML. For known batch approval pages, the probe
uses the retained screenshot to detect visible list rows and marks those items
with `source=screenshot_visual`.

Possible `suggested_action` values:

- `return`
- `batch_select_then_approve`
- `approve_one_by_one`
- `needs_manual_review`

These are planning hints only. They are not execution commands in Phase 4.
`item_count=0` never means executable work.

## Screenshot And XML Retention

Each menu summary includes:

- `screenshot_path`
- `xml_path`
- `sensitive_actions_seen`

The screenshot and XML are kept as local temp files created by the existing Android screen reader. These artifacts are used for manual review and workflow modeling.

## Safety Boundary

Phase 4 must not:

- Execute real approval.
- Tap `同意`, `批准`, `审批`, `通过`, `确认`, `提交`, or `全选`.
- Automatically approve leave, attendance, work hours, comp time, or missing clock requests.
- Add timed jobs or background automation.
- Bypass risk controls, hide Mock Location, use Root, Hook, or anti-detection behavior.

## Self-Test Commands

From the repo root:

```bash
PYTHONPATH=src python3 scripts/build_daily_approval_plan.py
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
```

## Phase 5 Preview

Phase 5 may add controlled execution, but only with explicit protection mechanisms:

- Human confirmation before real approval.
- Per-menu risk gates.
- Skip all `item_count=0`, `unknown`, high-risk, and `needs_manual_review` entries.
- Dry-run diff before execution.
- Screenshot/XML evidence before and after each action.
- Hard blocks for unexpected UI or sensitive action ambiguity.

Until Phase 5 exists, `suggested_action` is only a modeling field.
