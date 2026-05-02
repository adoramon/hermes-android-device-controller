# Safety Boundaries

This project is a device-control foundation for authorized Hermes Android test environments.

## Allowed

- Generic ADB health checks.
- Generic tap, swipe, text input, UI XML dump, and screenshot actions.
- Test-only mock-location broadcasts to a Hermes-owned helper app.
- Documentation and tests for command construction and error reporting.

## Not Allowed

- Implementing real clock-in, attendance, approval, expense, or HR workflows.
- Bypassing risk controls, device attestation, anti-fraud checks, or app access controls.
- Hiding automation from a target application or service.
- Using mock location outside authorized test/debug environments.

## Operational Notes

All ADB commands should be auditable. The Python wrapper returns the command, timeout, stdout, stderr, return code, and timeout state for every execution.
