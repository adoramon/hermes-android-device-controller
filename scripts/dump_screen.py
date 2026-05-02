#!/usr/bin/env python3

from hermes_android_controller import dump_screen_xml


def main() -> int:
    result = dump_screen_xml()
    print(result["message"])
    print("path:", result["path"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
