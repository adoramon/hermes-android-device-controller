# Phase 2: Mock Location Helper

Phase 2 adds a minimal Android Kotlin helper app under `android-helper/`. The app receives test-only location updates from the Mac mini controller and applies them through Android mock location providers on a self-owned Pixel test device.

This phase does not include enterprise App automation, attendance workflows, approval workflows, risk-control bypasses, hidden mock-location behavior, root/hook behavior, or anti-detection logic.

## Android Project

- Package: `com.hermes.mocklocation`
- App name: `Hermes Mock Location Helper`
- minSdk: 26
- targetSdk: 36
- Language: Kotlin
- Log tag: `HermesMockLocation`

The current stable Android SDK platform used here is Android 16 / API 36. Android 17 is still on beta channels as of May 2, 2026.

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
- Log clear failures with tag `HermesMockLocation`.
- Continue with an existing provider if adding a test provider fails.
- Set `GPS_PROVIDER` and `NETWORK_PROVIDER` test locations when possible.
- Be used only in authorized testing environments.

## Build

```bash
cd android-helper
./gradlew :app:assembleDebug
```

The build requires Android SDK Platform 36. Configure it with `ANDROID_HOME` or `android-helper/local.properties`.

## Install

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Pixel Setup

1. Enable Developer options.
2. Enable USB debugging.
3. Open Developer options > Select mock location app.
4. Select Hermes Mock Location Helper.

## ADB Test

```bash
adb shell am broadcast \
  -a com.hermes.mocklocation.SET \
  --ef lat 31.2304 \
  --ef lon 121.4737 \
  --ef accuracy 10
```

## Verification

Use Google Maps or a system location test screen on the Pixel to confirm the test coordinate is visible. Use `adb logcat -s HermesMockLocation` for troubleshooting.
