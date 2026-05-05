# Phase 3: Enterprise App UI Probe

Phase 3 adds read-only UI probing for the enterprise Android app:

```text
com.bonc.mobile.jlmhim.tt
```

## Goal

Hermes can open the enterprise app on the authorized Pixel 6 test device, capture the current screen, export UIAutomator XML, parse controls, and produce a page summary for later workflow modeling.

The probe output includes:

- Foreground package.
- Local UI XML path.
- Local screenshot path.
- Possible page title.
- Clickable element list.
- Input field list.
- Sensitive action risk markers.

## Safety Boundary

Allowed in this phase:

- Open the enterprise app.
- Capture screenshot.
- Dump UI XML.
- Parse controls and bounds.
- Summarize visible UI state.

Not allowed in this phase:

- Do not perform attendance or check-in submission.
- Do not perform approval submission.
- Do not tap business action buttons such as `打卡`, `提交`, `确认`, or `审批通过`.
- Do not bypass risk controls.
- Do not hide Mock Location.
- Do not implement anti-detection, Root, or Hook behavior.

## Self-Test Commands

From the repo root:

```bash
PYTHONPATH=src python3 scripts/probe_enterprise_app.py
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
```

The probe script opens the enterprise app, waits 2 seconds, dumps XML, captures a screenshot, and prints a JSON summary. It does not click any business UI element.

## Modeling From UI XML

Use UIAutomator XML as the source of truth for the current screen.

For each retained node, the parser records:

- `text`
- `resource_id`
- `class`
- `content_desc`
- `clickable`
- `enabled`
- `bounds`

Nodes are retained when they have visible text, content description, resource id, or are clickable. Bounds include the raw rectangle, size, and center point so a later human-reviewed model can map UI regions without guessing.

## Manual Flow Confirmation

Future approval-flow modeling should be built from multiple read-only probes:

1. Open the app and capture the landing page.
2. Manually navigate to the target module outside Hermes automation if needed.
3. Run the probe again on each page.
4. Record page title, stable resource ids, input fields, and safe navigation controls.
5. Flag sensitive buttons for human confirmation before any future automation design.

Any future write/action workflow must be explicitly approved and must preserve the existing safety boundaries.
