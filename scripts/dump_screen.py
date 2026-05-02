#!/usr/bin/env python3

from hermes_android_controller import dump_screen_xml


def main() -> int:
    result = dump_screen_xml()
    if result.stdout:
        print(result.stdout, end="" if str(result.stdout).endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if str(result.stderr).endswith("\n") else "\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
