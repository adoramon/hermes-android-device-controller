import os
import struct
import tempfile
import unittest
import zlib

from hermes_android_controller.adb_client import AdbClient, AdbCommandResult
from hermes_android_controller.enterprise_approval_probe import (
    summarize_attendance_exception_approval,
    summarize_comp_time_approval,
    detect_approval_menus,
    detect_empty_state,
    enter_approval_menu,
    summarize_leave_approval,
    summarize_missing_clock_approval,
    summarize_work_hour_approval,
)


def node(text="", resource_id="", clickable=False, bounds=None):
    return {
        "text": text,
        "resource_id": resource_id,
        "class": "android.widget.TextView",
        "content_desc": "",
        "clickable": clickable,
        "enabled": True,
        "bounds": bounds
        or {
            "left": 10,
            "top": 20,
            "right": 210,
            "bottom": 120,
            "width": 200,
            "height": 100,
            "center_x": 110,
            "center_y": 70,
        },
    }


def webview_node():
    return node("", resource_id="com.example.enterprise:id/webview", clickable=True) | {
        "class": "android.webkit.WebView"
    }


def write_test_png(path, bands=None):
    width, height = 1080, 2400
    bands = bands or [(420, 470, 120, 840)]
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            dark_row = any(top <= y <= bottom and left <= x <= right for top, bottom, left, right in bands)
            row.extend((30, 30, 30) if dark_row else (245, 245, 245))
        rows.append(b"\x00" + bytes(row))
    raw = zlib.compress(b"".join(rows))
    with open(path, "wb") as file:
        file.write(b"\x89PNG\r\n\x1a\n")
        _write_png_chunk(file, b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        _write_png_chunk(file, b"IDAT", raw)
        _write_png_chunk(file, b"IEND", b"")


def _write_png_chunk(file, chunk_type, data):
    file.write(struct.pack(">I", len(data)))
    file.write(chunk_type)
    file.write(data)
    file.write(struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF))


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


class EnterpriseApprovalProbeTests(unittest.TestCase):
    def test_menu_detection(self):
        nodes = [
            node("工时审批", clickable=True),
            node("考勤异常审批", clickable=True),
            node("请假审批", clickable=True),
            node("调休时长审批", clickable=True),
            node("未打卡审批", clickable=True),
        ]

        result = detect_approval_menus(nodes=nodes)

        self.assertTrue(result["ok"])
        self.assertTrue(all(item["found"] for item in result["menus"]))

    def test_empty_state_detection(self):
        result = detect_empty_state([node("暂无待审批数据")])

        self.assertTrue(result["is_empty"])

    def test_work_hour_pending_count_parse(self):
        summary = summarize_work_hour_approval(
            nodes=[
                node("项目A", bounds={"left": 10, "top": 20, "right": 610, "bottom": 120, "width": 600, "height": 100}),
                node("待审批3人"),
                node("审批", clickable=True),
            ]
        )

        self.assertEqual(summary["status"], "has_items")
        self.assertEqual(summary["item_count"], 1)
        self.assertEqual(summary["project_count"], 1)
        self.assertEqual(summary["pending_people_count"], 3)
        self.assertEqual(summary["suggested_action"], "needs_manual_review")
        self.assertEqual(summary["risk_level"], "medium")

    def test_work_hour_project_without_pending_count_is_has_items(self):
        summary = summarize_work_hour_approval(
            nodes=[
                node(
                    "智慧项目工时填报",
                    bounds={"left": 10, "top": 20, "right": 850, "bottom": 132, "width": 840, "height": 112},
                )
            ]
        )

        self.assertEqual(summary["status"], "has_items")
        self.assertEqual(summary["item_count"], 1)
        self.assertEqual(summary["project_count"], 1)
        self.assertEqual(summary["pending_people_count"], 0)

    def test_item_count_zero_is_not_has_items(self):
        summary = summarize_work_hour_approval(nodes=[node("待审批0人")])

        self.assertNotEqual(summary["status"], "has_items")
        self.assertEqual(summary["item_count"], 0)

    def test_title_nodes_do_not_count_as_items(self):
        summaries = {
            "工时": summarize_work_hour_approval(nodes=[node("我管理的项目"), node("web_title", resource_id="web_title")]),
            "考勤": summarize_attendance_exception_approval(nodes=[node("我管理的员工"), node("web_title", resource_id="web_title")]),
            "调休": summarize_comp_time_approval(nodes=[node("我管理的员工")]),
            "未打卡": summarize_missing_clock_approval(nodes=[node("我管理的员工"), node("未打卡申请审批")]),
        }

        for summary in summaries.values():
            self.assertEqual(summary["item_count"], 0)
        self.assertEqual(summaries["工时"]["status"], "unknown")
        self.assertEqual(summaries["工时"]["suggested_action"], "needs_manual_review")
        self.assertEqual(summaries["考勤"]["status"], "empty")
        self.assertEqual(summaries["考勤"]["suggested_action"], "return")
        self.assertEqual(summaries["调休"]["status"], "empty")
        self.assertEqual(summaries["调休"]["suggested_action"], "return")
        self.assertEqual(summaries["未打卡"]["status"], "empty")
        self.assertEqual(summaries["未打卡"]["suggested_action"], "return")

    def test_work_hour_pending_zero_is_not_has_items(self):
        summary = summarize_work_hour_approval(nodes=[node("待审批0人"), node("审批", clickable=True)])

        self.assertEqual(summary["item_count"], 0)
        self.assertEqual(summary["status"], "unknown")

    def test_work_hour_pending_three_is_has_items(self):
        summary = summarize_work_hour_approval(
            nodes=[
                node("项目A", bounds={"left": 10, "top": 20, "right": 610, "bottom": 120, "width": 600, "height": 100}),
                node("待审批3人"),
            ]
        )

        self.assertEqual(summary["item_count"], 1)
        self.assertEqual(summary["pending_people_count"], 3)
        self.assertEqual(summary["status"], "has_items")

    def test_leave_pending_count_and_suggested_action(self):
        summary = summarize_leave_approval(
            nodes=[
                node("请假申请 2"),
                node("张三 年假"),
                node("同意", clickable=True),
            ]
        )

        self.assertEqual(summary["status"], "has_items")
        self.assertEqual(summary["item_count"], 2)
        self.assertEqual(summary["suggested_action"], "approve_one_by_one")
        self.assertEqual(summary["risk_level"], "high")
        self.assertEqual(summary["sensitive_actions_seen"][0]["text"], "同意")

    def test_hidden_webview_visual_row_can_be_counted(self):
        with tempfile.TemporaryDirectory() as directory:
            screenshot_path = os.path.join(directory, "screen.png")
            write_test_png(screenshot_path)
            summary = summarize_missing_clock_approval(
                nodes=[
                    node("未打卡申请审批", resource_id="com.example.enterprise:id/web_title"),
                    webview_node(),
                ],
                probe={"screenshot_path": screenshot_path},
            )

        self.assertEqual(summary["status"], "has_items")
        self.assertEqual(summary["item_count"], 1)
        self.assertEqual(summary["items"][0]["source"], "screenshot_visual")
        self.assertEqual(summary["risk_level"], "medium")

    def test_attendance_visual_four_rows_and_applicant_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            screenshot_path = os.path.join(directory, "screen.png")
            write_test_png(
                screenshot_path,
                bands=[
                    (420, 450, 120, 840),
                    (520, 550, 120, 840),
                    (620, 650, 120, 840),
                    (720, 750, 120, 840),
                ],
            )
            summary = summarize_attendance_exception_approval(
                nodes=[
                    node("考勤审批", resource_id="com.example.enterprise:id/web_title"),
                    webview_node(),
                ],
                probe={"screenshot_path": screenshot_path},
            )

        self.assertEqual(summary["status"], "has_items")
        self.assertEqual(summary["item_count"], 4)
        self.assertEqual(summary["applicant_summary"], {"申请人A": 2, "申请人B": 2})

    def test_leave_empty_copy_is_empty(self):
        summary = summarize_leave_approval(nodes=[node("暂无数据")])

        self.assertEqual(summary["status"], "empty")
        self.assertEqual(summary["item_count"], 0)

    def test_leave_pending_tab_zero_is_empty(self):
        summary = summarize_leave_approval(nodes=[node("我的流程"), node("待办(0)"), node("已办(689)"), node("发起(78)")])

        self.assertEqual(summary["status"], "empty")
        self.assertEqual(summary["item_count"], 0)

    def test_comp_time_header_and_approval_button_is_empty(self):
        summary = summarize_comp_time_approval(nodes=[node("我管理的员工"), node("审批", clickable=True)])

        self.assertEqual(summary["status"], "empty")
        self.assertEqual(summary["item_count"], 0)

    def test_missing_clock_item_with_end_marker_is_has_items(self):
        summary = summarize_missing_clock_approval(nodes=[node("申请人C20260427未打卡申请(下午)"), node("没有更多了")])

        self.assertEqual(summary["status"], "has_items")
        self.assertEqual(summary["item_count"], 1)
        self.assertEqual(summary["applicant_summary"], {"申请人C": 1})

    def test_sensitive_buttons_are_not_clicked_when_entering_menu(self):
        client = FakeClient()
        menu_node = node("工时审批", clickable=True, bounds={"center_x": 100, "center_y": 200})
        approve_node = node("审批", clickable=True, bounds={"center_x": 900, "center_y": 2000})

        with unittest.mock.patch(
            "hermes_android_controller.enterprise_approval_probe._screen_nodes",
            return_value={"ok": True, "nodes": [menu_node, approve_node]},
        ):
            result = enter_approval_menu("工时审批", client=client)

        self.assertTrue(result["ok"])
        self.assertIn(["input", "tap", "100", "200"], client.calls)
        self.assertNotIn(["input", "tap", "900", "2000"], client.calls)


if __name__ == "__main__":
    unittest.main()
