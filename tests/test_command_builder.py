import unittest

from hermes_android_controller.adb_client import AdbClient, AdbCommandResult
from hermes_android_controller.input_actions import input_text, keyevent, open_app, swipe, tap
from hermes_android_controller.mock_location import (
    MOCK_LOCATION_ACTION,
    set_mock_location,
)
from hermes_android_controller.screen_reader import dump_screen_xml, take_screenshot


class FakeClient(AdbClient):
    def __init__(self, stdout=None, returncode=0):
        super().__init__()
        self.calls = []
        self.stdout = list(stdout or ["package:/data/app/helper/base.apk", "Broadcast completed: result=0"])
        self.returncode = returncode

    def run(self, args, timeout=None, *, text=True):
        command = self.build_command(args)
        self.calls.append((args, timeout, text))
        stdout = self.stdout[min(len(self.calls) - 1, len(self.stdout) - 1)]
        return AdbCommandResult(
            command=command,
            timeout=self.default_timeout if timeout is None else timeout,
            stdout=stdout if text else b"png",
            stderr="" if self.returncode == 0 else "failure",
            returncode=self.returncode,
        )


class CommandBuilderTests(unittest.TestCase):
    def test_open_app_command(self):
        client = FakeClient()

        open_app("com.example.app", client=client)

        self.assertEqual(
            client.calls[0][0],
            [
                "shell",
                "monkey",
                "-p",
                "com.example.app",
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ],
        )


    def test_input_commands(self):
        client = FakeClient()

        tap(10, 20, client=client)
        swipe(1, 2, 3, 4, 500, client=client)
        input_text("hello world", client=client)
        keyevent(4, client=client)

        self.assertEqual(client.calls[0][0], ["shell", "input", "tap", "10", "20"])
        self.assertEqual(client.calls[1][0], ["shell", "input", "swipe", "1", "2", "3", "4", "500"])
        self.assertEqual(client.calls[2][0], ["shell", "input", "text", "hello%sworld"])
        self.assertEqual(client.calls[3][0], ["shell", "input", "keyevent", "4"])


    def test_screen_reader_commands(self):
        client = FakeClient()

        dump_screen_xml(client=client)
        take_screenshot(client=client)

        self.assertEqual(client.calls[0], (["shell", "uiautomator", "dump", "/sdcard/hermes_screen.xml"], None, True))
        self.assertEqual(client.calls[1][0][:2], ["pull", "/sdcard/hermes_screen.xml"])
        self.assertEqual(client.calls[2], (["shell", "screencap", "-p", "/sdcard/hermes_screenshot.png"], None, True))
        self.assertEqual(client.calls[3][0][:2], ["pull", "/sdcard/hermes_screenshot.png"])


    def test_mock_location_broadcast_command(self):
        client = FakeClient()

        response = set_mock_location(31.23, 121.47, 25, client=client)

        self.assertTrue(response["ok"])
        self.assertEqual(
            client.calls[0][0],
            [
                "shell",
                "am",
                "broadcast",
                "-a",
                MOCK_LOCATION_ACTION,
                "--ef",
                "lat",
                "31.23",
                "--ef",
                "lon",
                "121.47",
                "--ef",
                "accuracy",
                "25",
            ],
        )


    def test_mock_location_reports_clear_error_on_failure(self):
        client = FakeClient(stdout=[""], returncode=1)

        response = set_mock_location(31.23, 121.47, 25, client=client)

        self.assertFalse(response["ok"])
        self.assertIn("Mock Location Helper", response["message"])

    def test_invalid_coordinates_are_rejected(self):
        client = FakeClient()

        with self.assertRaises(ValueError):
            tap(-1, 20, client=client)
        with self.assertRaises(ValueError):
            swipe(0, 0, 10, 10, 0, client=client)
        with self.assertRaises(ValueError):
            keyevent(-1, client=client)

    def test_invalid_location_is_rejected(self):
        client = FakeClient()

        with self.assertRaises(ValueError):
            set_mock_location(91, 121.47, 10, client=client)
        with self.assertRaises(ValueError):
            set_mock_location(31.23, 181, 10, client=client)
        with self.assertRaises(ValueError):
            set_mock_location(31.23, 121.47, 0, client=client)
