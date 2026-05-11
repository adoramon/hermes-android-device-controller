import unittest

from hermes_android_controller.approval_report import (
    build_approval_wechat_report,
    format_approval_wechat_report,
)
from hermes_android_controller.enterprise_approval_executor import CONFIRM_PHRASE


def sample_plan():
    return {
        "ok": True,
        "mode": "dry_run",
        "menus": [
            {
                "menu_name": "工时审批",
                "status": "has_items",
                "item_count": 1,
                "project_count": 1,
                "pending_people_count": 4,
                "project_items": [{"text": "项目A"}],
                "suggested_action": "batch_select_then_approve",
                "risk_level": "medium",
                "xml_path": "/tmp/secret.xml",
                "screenshot_path": "/tmp/secret.png",
            },
            {
                "menu_name": "考勤异常审批",
                "status": "has_items",
                "item_count": 4,
                "applicant_summary": {"申请人A": 2, "申请人B": 2},
                "suggested_action": "batch_select_then_approve",
                "risk_level": "high",
            },
            {
                "menu_name": "请假审批",
                "status": "empty",
                "item_count": 0,
                "suggested_action": "return",
                "risk_level": "low",
            },
            {
                "menu_name": "调休时长审批",
                "status": "empty",
                "item_count": 0,
                "suggested_action": "return",
                "risk_level": "low",
            },
            {
                "menu_name": "未打卡审批",
                "status": "has_items",
                "item_count": 1,
                "applicant_summary": {"申请人C": 1},
                "suggested_action": "batch_select_then_approve",
                "risk_level": "medium",
            },
        ],
    }


class ApprovalReportTests(unittest.TestCase):
    def test_wechat_report_uses_required_columns(self):
        markdown = format_approval_wechat_report(sample_plan())

        self.assertIn("| 审批类型 | 状态 | 数量 | 明细 | 处理方式 |", markdown)
        self.assertIn("|---|---:|---:|---|---|", markdown)
        self.assertNotIn("风险", markdown)
        self.assertNotIn("risk", markdown)

    def test_wechat_report_matches_expected_rows(self):
        markdown = format_approval_wechat_report(sample_plan())

        self.assertIn("| 工时审批 | 待处理 | 1 项/4 人 | 项目数 1，待审批 4 人 | 确认后执行 |", markdown)
        self.assertIn("| 考勤异常审批 | 待处理 | 4 条 | 申请人A 2，申请人B 2 | 确认后执行 |", markdown)
        self.assertIn("| 请假审批 | 无数据 | 0 | 暂无数据 | 跳过 |", markdown)
        self.assertIn("| 调休时长审批 | 无数据 | 0 | 暂无数据 | 跳过 |", markdown)
        self.assertIn("| 未打卡审批 | 待处理 | 1 条 | 申请人C | 确认后执行 |", markdown)

    def test_wechat_report_appends_confirmation_prompt(self):
        markdown = format_approval_wechat_report(sample_plan())

        self.assertTrue(markdown.endswith(f"如确认执行，请回复：\n{CONFIRM_PHRASE}"))

    def test_wechat_report_hides_paths_and_raw_plan_fields(self):
        markdown = format_approval_wechat_report(sample_plan())

        self.assertNotIn("xml_path", markdown)
        self.assertNotIn("screenshot_path", markdown)
        self.assertNotIn("/tmp/secret", markdown)
        self.assertNotIn("project_items", markdown)

    def test_builder_returns_concise_payload_without_raw_plan(self):
        result = build_approval_wechat_report(plan=sample_plan())

        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "wechat_approval_report")
        self.assertIn("markdown", result)
        self.assertNotIn("dry_run_plan", result)
        self.assertNotIn("menus", result)
        self.assertFalse(result["safety"]["auto_execute"])

    def test_unknown_or_manual_review_is_human_check_without_risk_wording(self):
        plan = {
            "ok": True,
            "menus": [
                {
                    "menu_name": "请假审批",
                    "status": "unknown",
                    "item_count": 2,
                    "suggested_action": "needs_manual_review",
                    "risk_level": "high",
                }
            ],
        }

        markdown = format_approval_wechat_report(plan)

        self.assertIn("| 请假审批 | 需人工核对 | 2 条 | 待人工核对 | 人工核对 |", markdown)
        self.assertNotIn("风险", markdown)
        self.assertNotIn("risk_level", markdown)


if __name__ == "__main__":
    unittest.main()
