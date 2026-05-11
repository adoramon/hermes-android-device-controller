# Safety Boundaries

This project is a device-control foundation for authorized Hermes Android test environments.

## Allowed

- Generic ADB health checks.
- Generic tap, swipe, text input, UI XML dump, and screenshot actions.
- Dry-run enterprise approval probing and WeChat-safe approval reports.
- Controlled approval execution when authorized by either `确认审批` or local
  `.env` setting `OA_APPROVAL_AUTO_EXECUTE=true`.
- Documentation and tests for command construction and error reporting.

## Not Allowed

- Implementing real clock-in, attendance, expense, or broad HR workflows.
- Executing unknown, high-risk, unsupported, or manual-review approval pages.
- Bypassing risk controls, device attestation, anti-fraud checks, or app access controls.
- Hiding automation from a target application or service.
- Using mock location outside authorized test/debug environments.

## Operational Notes

All ADB commands should be auditable. The Python wrapper returns the command,
timeout, stdout, stderr, return code, and timeout state for every execution.
Sensitive approval clicks must keep before/after XML and screenshots.
