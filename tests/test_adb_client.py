import subprocess
import unittest
from unittest.mock import patch

from hermes_android_controller.adb_client import AdbClient


class AdbClientTests(unittest.TestCase):
    def test_build_command_includes_serial_when_present(self):
        client = AdbClient(adb_path="/opt/android/adb", serial="pixel6")

        self.assertEqual(
            client.build_command(["shell", "input", "tap", "10", "20"]),
            [
                "/opt/android/adb",
                "-s",
                "pixel6",
                "shell",
                "input",
                "tap",
                "10",
                "20",
            ],
        )

    def test_build_command_includes_device_id_when_present(self):
        client = AdbClient(device_id="device-123")

        self.assertEqual(client.build_command(["devices"]), ["adb", "-s", "device-123", "devices"])

    def test_run_uses_subprocess_list_arguments(self):
        captured = {}

        def fake_run(command, capture_output, text, timeout, check, **kwargs):
            captured.update(
                command=command,
                capture_output=capture_output,
                text=text,
                timeout=timeout,
                check=check,
                shell=kwargs.get("shell"),
            )
            return subprocess.CompletedProcess(command, 0, "ok", "")

        with patch.object(subprocess, "run", fake_run):
            result = AdbClient(default_timeout=7).run(["devices", "-l"])

        self.assertEqual(
            captured,
            {
                "command": ["adb", "devices", "-l"],
                "capture_output": True,
                "text": True,
                "timeout": 7,
                "check": False,
                "shell": None,
            },
        )
        self.assertEqual(result.command, ["adb", "devices", "-l"])
        self.assertEqual(result.timeout, 7)
        self.assertEqual(result.stdout, "ok")
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.ok)
        self.assertEqual(
            result.to_dict(),
            {
                "ok": True,
                "command": ["adb", "devices", "-l"],
                "stdout": "ok",
                "stderr": "",
                "returncode": 0,
            },
        )


    def test_timeout_result_has_required_fields(self):
        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=["adb", "devices"], timeout=3, output="partial", stderr="late")

        with patch.object(subprocess, "run", fake_run):
            result = AdbClient(default_timeout=3).run(["devices"])

        self.assertEqual(result.command, ["adb", "devices"])
        self.assertEqual(result.timeout, 3)
        self.assertEqual(result.stdout, "partial")
        self.assertEqual(result.stderr, "late")
        self.assertEqual(result.returncode, -1)
        self.assertTrue(result.timed_out)
