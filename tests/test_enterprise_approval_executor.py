import unittest
from unittest.mock import patch

from hermes_android_controller.enterprise_approval_executor import (
    AUTO_EXECUTE_ENV,
    CONFIRM_PHRASE,
    VALIDATION_CONFIRM_PHRASE,
    execute_daily_approval_plan,
    validate_daily_approval_confirmation_flow,
    _capture_nodes,
    _click_node,
    _click_first_confirmation,
    _final_confirmation_candidate,
    _inspect_confirmation_surface,
    _missing_clock_applicant_choice_control,
    _validation_work_hour_detail_selection,
    _webview_batch_control,
)
from hermes_android_controller.adb_client import AdbClient, AdbCommandResult


class FakeClient(AdbClient):
    def __init__(self):
        super().__init__()
        self.calls = []

    def shell(self, args, timeout=None):
        self.calls.append(list(args))
        return AdbCommandResult(
            command=self.build_command(["shell", *[str(arg) for arg in args]]),
            timeout=self.default_timeout if timeout is None else timeout,
            stdout="",
            stderr="",
            returncode=0,
        )


def menu(menu_name, status="has_items", risk_level="medium", suggested_action="batch_select_then_approve"):
    return {
        "menu_name": menu_name,
        "status": status,
        "risk_level": risk_level,
        "suggested_action": suggested_action,
        "item_count": 1,
        "items": [{"label": "item"}],
    }


class EnterpriseApprovalExecutorTests(unittest.TestCase):
    def test_missing_confirmation_refuses_execution(self):
        with patch.dict("os.environ", {AUTO_EXECUTE_ENV: "false"}, clear=False):
            result = execute_daily_approval_plan("")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "refused")

    def test_wrong_confirmation_refuses_execution(self):
        with patch.dict("os.environ", {AUTO_EXECUTE_ENV: "false"}, clear=False):
            result = execute_daily_approval_plan("确认执行今日审批")

        self.assertFalse(result["ok"])
        self.assertEqual(result["required_confirm_text"], CONFIRM_PHRASE)

    def test_env_auto_execute_allows_execution_without_confirmation(self):
        plan = {"ok": True, "menus": [menu("工时审批")]}
        with patch.dict("os.environ", {AUTO_EXECUTE_ENV: "true"}, clear=False), patch(
            "hermes_android_controller.enterprise_approval_executor.build_daily_approval_plan",
            return_value=plan,
        ), patch(
            "hermes_android_controller.enterprise_approval_executor._ensure_approval_menu_home",
            return_value={"ok": True},
        ), patch(
            "hermes_android_controller.enterprise_approval_executor._execute_menu_by_name",
            return_value={"ok": True, "menu_name": "工时审批", "executed": True},
        ):
            result = execute_daily_approval_plan("", client=FakeClient())

        self.assertTrue(result["ok"])
        self.assertEqual(result["authorization"]["mode"], "env_auto_execute")
        self.assertTrue(result["safety"]["env_auto_execute"])

    def test_env_auto_execute_menu_allowlist_skips_unlisted_menu(self):
        plan = {"ok": True, "menus": [menu("请假审批", suggested_action="approve_one_by_one")]}
        with patch.dict(
            "os.environ",
            {
                AUTO_EXECUTE_ENV: "true",
                "OA_APPROVAL_AUTO_EXECUTE_MENUS": "工时审批",
            },
            clear=False,
        ), patch(
            "hermes_android_controller.enterprise_approval_executor.build_daily_approval_plan",
            return_value=plan,
        ):
            result = execute_daily_approval_plan("", client=FakeClient())

        self.assertFalse(result["results"][0]["executed"])
        self.assertEqual(result["results"][0]["reason"], "menu_not_auto_enabled")

    def test_env_auto_execute_max_items_skips_large_menu(self):
        item = menu("工时审批")
        item["item_count"] = 3
        plan = {"ok": True, "menus": [item]}
        with patch.dict(
            "os.environ",
            {
                AUTO_EXECUTE_ENV: "true",
                "OA_APPROVAL_AUTO_EXECUTE_MAX_ITEMS": "2",
            },
            clear=False,
        ), patch(
            "hermes_android_controller.enterprise_approval_executor.build_daily_approval_plan",
            return_value=plan,
        ):
            result = execute_daily_approval_plan("", client=FakeClient())

        self.assertFalse(result["results"][0]["executed"])
        self.assertEqual(result["results"][0]["reason"], "item_count>2")

    def test_high_risk_is_skipped(self):
        plan = {"ok": True, "menus": [menu("请假审批", risk_level="high", suggested_action="approve_one_by_one")]}
        with patch("hermes_android_controller.enterprise_approval_executor.build_daily_approval_plan", return_value=plan):
            result = execute_daily_approval_plan(CONFIRM_PHRASE, client=FakeClient())

        self.assertFalse(result["results"][0]["executed"])
        self.assertEqual(result["results"][0]["reason"], "risk_level=high")

    def test_unknown_is_skipped(self):
        plan = {"ok": True, "menus": [menu("工时审批", status="unknown")]}
        with patch("hermes_android_controller.enterprise_approval_executor.build_daily_approval_plan", return_value=plan):
            result = execute_daily_approval_plan(CONFIRM_PHRASE, client=FakeClient())

        self.assertFalse(result["results"][0]["executed"])
        self.assertEqual(result["results"][0]["reason"], "status=unknown")

    def test_needs_manual_review_is_skipped(self):
        plan = {"ok": True, "menus": [menu("工时审批", suggested_action="needs_manual_review")]}
        with patch("hermes_android_controller.enterprise_approval_executor.build_daily_approval_plan", return_value=plan):
            result = execute_daily_approval_plan(CONFIRM_PHRASE, client=FakeClient())

        self.assertFalse(result["results"][0]["executed"])
        self.assertEqual(result["results"][0]["reason"], "suggested_action=needs_manual_review")

    def test_item_count_zero_is_skipped(self):
        item = menu("工时审批")
        item["item_count"] = 0
        plan = {"ok": True, "menus": [item]}
        with patch("hermes_android_controller.enterprise_approval_executor.build_daily_approval_plan", return_value=plan):
            result = execute_daily_approval_plan(CONFIRM_PHRASE, client=FakeClient())

        self.assertFalse(result["results"][0]["executed"])
        self.assertEqual(result["results"][0]["reason"], "item_count=0")

    def test_failed_capture_returns_diagnostics(self):
        failed_probe = {
            "ok": False,
            "xml_path": "/tmp/last.xml",
            "screenshot_path": "/tmp/last.png",
            "xml": {
                "dump": AdbCommandResult(command=["adb"], timeout=1, stdout="xml out", stderr="xml err", returncode=1)
            },
            "screenshot": {
                "capture": AdbCommandResult(command=["adb"], timeout=1, stdout="shot out", stderr="shot err", returncode=1)
            },
        }
        with patch.dict("os.environ", {"ENTERPRISE_APP_PACKAGE": "com.example.enterprise"}), patch(
            "hermes_android_controller.enterprise_approval_executor.device_status",
            return_value={"foreground_package": "com.example.enterprise", "message": "ok"},
        ), patch(
            "hermes_android_controller.enterprise_approval_executor.probe_current_screen",
            return_value=failed_probe,
        ):
            result = _capture_nodes(FakeClient(), attempts=1)

        self.assertFalse(result["ok"])
        self.assertEqual(result["current_foreground_package"], "com.example.enterprise")
        self.assertEqual(result["last_xml_path"], "/tmp/last.xml")
        self.assertEqual(result["last_screenshot_path"], "/tmp/last.png")
        retry = result["adb"]["retry_logs"][0]
        self.assertEqual(retry["xml_dump"]["stderr"], "xml err")
        self.assertEqual(retry["screenshot_capture"]["stdout"], "shot out")

    def test_hidden_webview_batch_control_uses_known_safe_bounds(self):
        page = {
            "nodes": [
                {
                    "text": "未打卡申请审批",
                    "resource_id": "com.example.enterprise:id/web_title",
                    "class": "android.widget.TextView",
                    "bounds": {"left": 375, "top": 162, "right": 704, "bottom": 225},
                },
                {
                    "text": "",
                    "resource_id": "com.example.enterprise:id/webview",
                    "class": "android.webkit.WebView",
                    "bounds": {"left": 0, "top": 259, "right": 1080, "bottom": 2337},
                },
            ]
        }

        choice = _webview_batch_control("未打卡审批", page, "employee_choice")
        approve = _webview_batch_control("未打卡审批", page, "approve_button")

        self.assertEqual(choice["bounds"]["center_y"], 327)
        self.assertEqual(approve["bounds"]["center_x"], 921)

    def test_missing_clock_prefers_applicant_row_over_select_all(self):
        page = {
            "nodes": [
                {
                    "text": "未打卡申请审批",
                    "resource_id": "com.example.enterprise:id/web_title",
                    "class": "android.widget.TextView",
                    "bounds": {"left": 375, "top": 162, "right": 704, "bottom": 225},
                },
                {
                    "text": "",
                    "resource_id": "com.example.enterprise:id/webview",
                    "class": "android.webkit.WebView",
                    "bounds": {"left": 0, "top": 259, "right": 1080, "bottom": 2337},
                },
            ]
        }
        plan_menu = {
            "items": [
                {
                    "label": "申请人C visual row 1",
                    "bounds": {
                        "left": 0,
                        "top": 480,
                        "right": 1080,
                        "bottom": 598,
                        "center_x": 540,
                        "center_y": 539,
                    },
                }
            ]
        }

        choice = _missing_clock_applicant_choice_control(page, plan_menu)

        self.assertEqual(choice["text"], "missing_clock_applicant_choice:申请人C")
        self.assertEqual(choice["bounds"]["center_y"], 539)
        self.assertEqual(choice["bounds"]["center_x"], 48)
        self.assertNotEqual(choice["bounds"]["center_y"], 327)

    def test_missing_clock_can_use_visible_applicant_node(self):
        page = {
            "nodes": [
                {
                    "text": "申请人C 20260427 未打卡申请",
                    "bounds": {"left": 180, "top": 620, "right": 980, "bottom": 690, "center_x": 580, "center_y": 655},
                }
            ]
        }

        choice = _missing_clock_applicant_choice_control(page, None)

        self.assertEqual(choice["bounds"]["center_y"], 655)
        self.assertEqual(choice["bounds"]["center_x"], 48)

    def test_sensitive_click_log_has_required_fields(self):
        client = FakeClient()
        node = {"bounds": {"center_x": 10, "center_y": 20}, "text": "审批"}
        page = {"ok": True, "nodes": [], "xml_path": "/tmp/a.xml", "screenshot_path": "/tmp/a.png"}
        with patch("hermes_android_controller.enterprise_approval_executor._capture_nodes", return_value=page):
            log = _click_node(client, node, clicked_text="审批", sensitive_action=True)

        self.assertTrue(log["sensitive_action"])
        self.assertEqual(log["clicked_text"], "审批")
        self.assertEqual(log["clicked_bounds"], {"center_x": 10, "center_y": 20})
        self.assertEqual(log["before_xml_path"], "/tmp/a.xml")
        self.assertEqual(log["after_screenshot_path"], "/tmp/a.png")

    def test_pre_final_validation_requires_phrase(self):
        result = validate_daily_approval_confirmation_flow("")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["required_confirm_text"], VALIDATION_CONFIRM_PHRASE)

    def test_pre_final_validation_skips_ineligible_menu(self):
        item = menu("请假审批", status="empty", suggested_action="return")
        item["item_count"] = 0
        plan = {"ok": True, "menus": [item]}
        with patch("hermes_android_controller.enterprise_approval_executor.build_daily_approval_plan", return_value=plan):
            result = validate_daily_approval_confirmation_flow(VALIDATION_CONFIRM_PHRASE, client=FakeClient())

        self.assertEqual(result["mode"], "pre_final_confirmation_validation")
        self.assertFalse(result["results"][0]["validated"])
        self.assertEqual(result["results"][0]["reason"], "item_count=0")
        self.assertFalse(result["safety"]["final_confirmation_clicked"])

    def test_confirmation_surface_detects_options_without_clicking(self):
        page = {
            "ok": True,
            "nodes": [
                {"text": "通过", "clickable": True, "bounds": {"center_x": 10, "center_y": 20}},
                {"text": "不通过", "clickable": True, "bounds": {"center_x": 30, "center_y": 40}},
                {"text": "确认", "clickable": True, "bounds": {"center_x": 50, "center_y": 60}},
            ],
        }

        result = _inspect_confirmation_surface(page)

        self.assertTrue(result["has_pass_option"])
        self.assertTrue(result["has_reject_option"])
        self.assertTrue(result["has_final_confirmation_candidate"])
        self.assertFalse(result["final_confirmation_clicked"])

    def test_confirmation_surface_detects_webview_text_button_bounds(self):
        page = {
            "ok": True,
            "nodes": [
                {"text": "通过", "clickable": False, "bounds": {"center_x": 10, "center_y": 20}},
                {"text": "不通过", "clickable": False, "bounds": {"center_x": 30, "center_y": 40}},
                {"text": "确定", "clickable": False, "bounds": {"center_x": 50, "center_y": 60}},
            ],
        }

        result = _inspect_confirmation_surface(page)

        self.assertTrue(result["has_final_confirmation_candidate"])
        self.assertEqual(len(result["final_confirmation_candidates"]), 1)
        self.assertEqual(result["final_confirmation_candidates"][0]["text"], "确定")

    def test_final_confirmation_candidate_ignores_pass_options(self):
        page = {
            "ok": True,
            "nodes": [
                {"text": "通过", "clickable": True, "bounds": {"center_x": 10, "center_y": 20}},
                {"text": "同意", "clickable": True, "bounds": {"center_x": 30, "center_y": 40}},
                {"text": "确认", "clickable": False, "bounds": {"center_x": 50, "center_y": 60}},
            ],
        }

        result = _final_confirmation_candidate(page)

        self.assertEqual(result["text"], "确认")

    def test_click_first_confirmation_requires_dialog_dismissal(self):
        client = FakeClient()
        dialog = {
            "ok": True,
            "nodes": [
                {"text": "确认", "clickable": False, "bounds": {"center_x": 50, "center_y": 60}},
            ],
            "xml_path": "/tmp/dialog.xml",
            "screenshot_path": "/tmp/dialog.png",
        }
        dismissed = {"ok": True, "nodes": [], "xml_path": "/tmp/done.xml", "screenshot_path": "/tmp/done.png"}
        with patch(
            "hermes_android_controller.enterprise_approval_executor._capture_nodes",
            side_effect=[dialog, dialog, dismissed, dismissed],
        ):
            logs = []
            result = _click_first_confirmation(client, logs)

        self.assertTrue(result["ok"])
        self.assertEqual(logs[0]["clicked_text"], "确认")
        self.assertIn(["input", "tap", "50", "60"], client.calls)

    def test_click_first_confirmation_rejects_pass_without_final_confirm(self):
        page = {
            "ok": True,
            "nodes": [
                {"text": "通过", "clickable": True, "bounds": {"center_x": 10, "center_y": 20}},
            ],
            "xml_path": "/tmp/pass.xml",
            "screenshot_path": "/tmp/pass.png",
        }
        with patch("hermes_android_controller.enterprise_approval_executor._capture_nodes", return_value=page):
            logs = []
            result = _click_first_confirmation(FakeClient(), logs)

        self.assertFalse(result["ok"])
        self.assertTrue(result["needs_manual_review"])
        self.assertEqual(logs, [])

    def test_work_hour_detail_prefers_top_select_all(self):
        page = {
            "nodes": [
                {
                    "text": "集成贸易-2025年国家管网集团管道光纤安全预警系统集约化采购项目",
                    "bounds": {"left": 32, "top": 294, "right": 1049, "bottom": 372, "center_x": 540, "center_y": 333},
                },
                {
                    "text": "白鉴琦(本事业部)20260428",
                    "bounds": {"left": 322, "top": 444, "right": 1049, "bottom": 520, "center_x": 685, "center_y": 482},
                },
            ]
        }
        menu_item = {
            "project_detail_probe": {
                "visual_rows": [
                    {"center_y": 485},
                ]
            }
        }

        result = _validation_work_hour_detail_selection(menu_item, page)

        self.assertEqual(result["text"], "work_hour_select_all")
        self.assertEqual(result["bounds"]["center_y"], 333)
        self.assertLess(result["bounds"]["center_y"], 430)


if __name__ == "__main__":
    unittest.main()
