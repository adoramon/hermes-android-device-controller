#!/usr/bin/env python3

import argparse

from hermes_android_controller import set_mock_location


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("lat", type=float)
    parser.add_argument("lon", type=float)
    parser.add_argument("accuracy", type=float)
    args = parser.parse_args()

    response = set_mock_location(args.lat, args.lon, args.accuracy)
    print(response["message"])
    result = response["result"]
    if result.stdout:
        print(result.stdout, end="" if str(result.stdout).endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if str(result.stderr).endswith("\n") else "\n")
    return 0 if response["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
