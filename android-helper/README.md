# Hermes Mock Location Helper

This directory contains the Phase 2 Android helper app for authorized Hermes Pixel test devices. It only implements Android mock location provider control through an ADB broadcast.

It does not implement enterprise App workflows, attendance flows, approval flows, risk-control bypasses, hidden mock-location behavior, root/hook behavior, or anti-detection logic.

## Project

- Language: Kotlin
- Package: `com.hermes.mocklocation`
- App name: `Hermes Mock Location Helper`
- minSdk: 26
- targetSdk: 36

## Build APK

Install Android Studio or Android SDK command-line tools with Android SDK Platform 36. Make sure `ANDROID_HOME` points to the SDK, or create `android-helper/local.properties`:

```properties
sdk.dir=/Users/you/Library/Android/sdk
```

Then run:

```bash
cd android-helper
./gradlew :app:assembleDebug
```

If you open the project in Android Studio, use the `app` debug build variant.

## Install To Pixel

Connect the Pixel test device with USB debugging enabled:

```bash
adb devices -l
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Select Mock Location App

On the Pixel:

1. Open Settings > About phone.
2. Tap Build number seven times to enable Developer options.
3. Open Settings > System > Developer options.
4. Choose Select mock location app.
5. Select Hermes Mock Location Helper.

The app screen displays whether it is currently selected as the mock location app.

## Test With ADB Broadcast

Send a test coordinate:

```bash
adb shell am broadcast \
  -a com.hermes.mocklocation.SET \
  --ef lat 31.2304 \
  --ef lon 121.4737 \
  --ef accuracy 10
```

Check logs:

```text
adb logcat -s HermesMockLocation
```

## Verify Location

Open Google Maps or a system location test screen on the Pixel and confirm the displayed location moves to the test coordinate. If it does not update:

- Confirm Hermes Mock Location Helper is selected in Developer options.
- Confirm location services are enabled.
- Re-run the broadcast and inspect `adb logcat -s HermesMockLocation`.
