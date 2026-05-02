# Phase 2: Mock Location Helper

The future Android helper app will receive test-only location updates from the Mac mini controller.

## Broadcast Contract

Expected package:

```text
com.hermes.mocklocation
```

Action:

```text
com.hermes.mocklocation.SET
```

Extras:

- `lat`: float latitude
- `lon`: float longitude
- `accuracy`: float accuracy in meters

## Expected Behavior

- Reject malformed coordinates.
- Require explicit installation and Android mock-location app selection.
- Return clear logs or broadcast result signals for troubleshooting.
- Be used only in authorized testing environments.

## Repository Placeholder

`android-helper/` is intentionally a placeholder in Phase 1. The Python controller already sends the planned broadcast so command construction and integration tests can be written early.
