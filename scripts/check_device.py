#!/usr/bin/env python3

from hermes_android_controller import device_status


def main() -> int:
    status = device_status()
    print(status["message"])
    print("screen_resolution:", status.get("screen_resolution"))
    print("foreground_package:", status.get("foreground_package"))
    devices = status["devices"]
    print(devices.stdout, end="" if str(devices.stdout).endswith("\n") else "\n")
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
