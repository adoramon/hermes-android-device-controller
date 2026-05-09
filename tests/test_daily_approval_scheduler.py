import datetime as dt
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hermes_android_controller import daily_approval_scheduler as scheduler


class DailyApprovalSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.env_patch = patch.dict(
            os.environ,
            {
                "OA_APPROVAL_STATE_DIR": self.temp_dir.name,
                "OA_APPROVAL_WINDOW_START": "14:00",
                "OA_APPROVAL_WINDOW_END": "16:00",
            },
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_scheduled_time_is_stable_for_day(self):
        state = {}
        day = dt.date(2026, 5, 5)

        first = scheduler.scheduled_datetime_for_day(day, state=state)
        second = scheduler.scheduled_datetime_for_day(day, state=state)

        self.assertEqual(first, second)
        self.assertEqual(first.date(), day)
        self.assertGreaterEqual(first.time(), dt.time(14, 0))
        self.assertLessEqual(first.time(), dt.time(16, 0))

    def test_run_once_waits_before_scheduled_time(self):
        state = {"scheduled_times": {"2026-05-05": "15:30:00"}}
        scheduler.save_state(state)

        result = scheduler.run_once_if_due(dt.datetime(2026, 5, 5, 14, 0))

        self.assertEqual(result["status"], "waiting")
        self.assertEqual(scheduler.load_state().get("last_report_date"), None)

    def test_run_once_runs_only_once_per_day(self):
        state = {"scheduled_times": {"2026-05-05": "14:00:00"}}
        scheduler.save_state(state)
        with patch("hermes_android_controller.daily_approval_scheduler.run_daily_scan", return_value={"ok": True, "run_id": "r1"}):
            first = scheduler.run_once_if_due(dt.datetime(2026, 5, 5, 14, 1))
            second = scheduler.run_once_if_due(dt.datetime(2026, 5, 5, 15, 1))

        self.assertEqual(first["run_id"], "r1")
        self.assertEqual(second["status"], "skipped")
        self.assertEqual(second["reason"], "already_ran_today")

    def test_collect_artifacts_copies_xml_and_screenshot(self):
        source_xml = Path(self.temp_dir.name) / "screen.xml"
        source_png = Path(self.temp_dir.name) / "screen.png"
        source_xml.write_text("<xml />", encoding="utf-8")
        source_png.write_bytes(b"png")
        dest = Path(self.temp_dir.name) / "artifacts"
        plan = {"menus": [{"xml_path": str(source_xml), "screenshot_path": str(source_png)}]}

        copied = scheduler.collect_artifacts(plan, dest)

        self.assertEqual(len(copied), 2)
        self.assertTrue((dest / "screen.xml").exists())
        self.assertTrue((dest / "screen.png").exists())

    def test_send_wechat_markdown_requires_config(self):
        with patch.dict(os.environ, {}, clear=True):
            result = scheduler.send_wechat_markdown("hello")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "not_configured")


if __name__ == "__main__":
    unittest.main()
