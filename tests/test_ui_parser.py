import tempfile
import unittest
from pathlib import Path

from hermes_android_controller.app_probe import parse_ui_xml, summarize_nodes


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" content-desc="" clickable="false" enabled="true" bounds="[0,0][1080,2400]">
    <node index="1" text="审批中心" resource-id="com.example:id/title" class="android.widget.TextView" content-desc="" clickable="false" enabled="true" bounds="[0,40][1080,120]" />
    <node index="2" text="姓名" resource-id="com.example:id/name_input" class="android.widget.EditText" content-desc="" clickable="true" enabled="true" bounds="[40,160][1040,240]" />
    <node index="3" text="提交" resource-id="com.example:id/submit" class="android.widget.Button" content-desc="" clickable="true" enabled="true" bounds="[800,2200][1040,2320]" />
    <node index="4" text="" resource-id="" class="android.view.View" content-desc="更多操作" clickable="true" enabled="true" bounds="[960,40][1040,120]" />
    <node index="5" text="" resource-id="" class="android.view.View" content-desc="" clickable="false" enabled="true" bounds="[1,1][2,2]" />
  </node>
</hierarchy>
"""


class UiParserTests(unittest.TestCase):
    def _write_xml(self, content=SAMPLE_XML):
        temp_dir = tempfile.TemporaryDirectory()
        path = Path(temp_dir.name) / "screen.xml"
        path.write_text(content, encoding="utf-8")
        self.addCleanup(temp_dir.cleanup)
        return path

    def test_bounds_are_parsed(self):
        nodes = parse_ui_xml(self._write_xml())
        title = next(node for node in nodes if node["text"] == "审批中心")

        self.assertEqual(
            title["bounds"],
            {
                "left": 0,
                "top": 40,
                "right": 1080,
                "bottom": 120,
                "width": 1080,
                "height": 80,
                "center_x": 540,
                "center_y": 80,
            },
        )

    def test_clickable_nodes_are_extracted(self):
        nodes = parse_ui_xml(self._write_xml())
        clickable_labels = {
            node["text"] or node["content_desc"]
            for node in nodes
            if node["clickable"]
        }

        self.assertIn("姓名", clickable_labels)
        self.assertIn("提交", clickable_labels)
        self.assertIn("更多操作", clickable_labels)

    def test_input_fields_are_identified(self):
        nodes = parse_ui_xml(self._write_xml())
        summary = summarize_nodes(nodes, foreground_package="com.bonc.mobile.jlmhim.tt")

        self.assertEqual(len(summary["input_fields"]), 1)
        self.assertEqual(summary["input_fields"][0]["resource_id"], "com.example:id/name_input")

    def test_sensitive_buttons_are_identified(self):
        nodes = parse_ui_xml(self._write_xml())
        summary = summarize_nodes(nodes)
        risk = summary["sensitive_action_risk"]

        self.assertTrue(risk["found"])
        self.assertEqual(risk["elements"][0]["text"], "提交")


if __name__ == "__main__":
    unittest.main()
