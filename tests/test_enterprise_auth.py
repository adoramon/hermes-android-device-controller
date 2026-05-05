import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hermes_android_controller.adb_client import AdbClient, AdbCommandResult
from hermes_android_controller.enterprise_auth import (
    detect_password_update_prompt,
    detect_login_screen,
    detect_sms_code_screen,
    extract_sms_code,
    fill_login_credentials,
    load_enterprise_credentials,
    submit_sms_code,
)


LOGIN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node text="请输入账号" resource-id="com.bonc.mobile.jlmhim.tt:id/login_user" class="android.widget.EditText" content-desc="" clickable="true" enabled="true" bounds="[151,1078][1014,1176]" />
  <node text="请输入密码" resource-id="com.bonc.mobile.jlmhim.tt:id/login_password" class="android.widget.EditText" content-desc="" clickable="true" enabled="true" bounds="[151,1189][938,1287]" />
  <node text="登录" resource-id="com.bonc.mobile.jlmhim.tt:id/login_login" class="android.widget.Button" content-desc="" clickable="true" enabled="true" bounds="[53,1444][1027,1570]" />
</hierarchy>
"""

SMS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node text="短信验证码" resource-id="com.example:id/title" class="android.widget.TextView" content-desc="" clickable="false" enabled="true" bounds="[0,100][1080,180]" />
  <node text="请输入验证码" resource-id="com.example:id/sms_code" class="android.widget.EditText" content-desc="" clickable="true" enabled="true" bounds="[80,300][1000,390]" />
  <node text="确认" resource-id="com.example:id/confirm" class="android.widget.Button" content-desc="" clickable="true" enabled="true" bounds="[80,430][1000,520]" />
</hierarchy>
"""

PASSWORD_UPDATE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node text="为了账号安全，请更新密码" resource-id="com.example:id/title" class="android.widget.TextView" content-desc="" clickable="false" enabled="true" bounds="[0,100][1080,180]" />
  <node text="暂不修改" resource-id="com.example:id/later" class="android.widget.Button" content-desc="" clickable="true" enabled="true" bounds="[80,430][500,520]" />
  <node text="修改密码" resource-id="com.example:id/change" class="android.widget.Button" content-desc="" clickable="true" enabled="true" bounds="[560,430][1000,520]" />
</hierarchy>
"""


class FakeClient(AdbClient):
    def __init__(self):
        super().__init__()
        self.calls = []

    def shell(self, args, timeout=None):
        self.calls.append((list(args), timeout))
        return AdbCommandResult(
            command=self.build_command(["shell", *[str(arg) for arg in args]]),
            timeout=self.default_timeout if timeout is None else timeout,
            stdout="",
            stderr="",
            returncode=0,
        )


class EnterpriseAuthTests(unittest.TestCase):
    def _write_xml(self, content):
        temp_dir = tempfile.TemporaryDirectory()
        path = Path(temp_dir.name) / "screen.xml"
        path.write_text(content, encoding="utf-8")
        self.addCleanup(temp_dir.cleanup)
        return path

    def test_missing_env_returns_clear_error(self):
        missing_path = Path(tempfile.gettempdir()) / "missing-hermes-enterprise.env"
        with patch.dict(os.environ, {}, clear=True):
            result = load_enterprise_credentials(env_path=missing_path)

        self.assertFalse(result["ok"])
        self.assertIn("ENTERPRISE_APP_USERNAME", result["missing"])
        self.assertIn("ENTERPRISE_APP_PASSWORD", result["missing"])

    def test_sms_code_extraction(self):
        self.assertEqual(extract_sms_code("企信验证码：123456"), "123456")
        self.assertEqual(extract_sms_code("请看 企信验证码: 9876"), "9876")
        self.assertIsNone(extract_sms_code("验证码 123456"))

    def test_invalid_sms_code_is_rejected(self):
        result = submit_sms_code("12ab")

        self.assertFalse(result["ok"])
        self.assertIn("格式无效", result["message"])

    def test_password_does_not_appear_in_fill_result(self):
        client = FakeClient()
        secret_value = "value-that-must-not-be-returned"
        result = fill_login_credentials(
            "u",
            secret_value,
            client=client,
            xml_path=self._write_xml(LOGIN_XML),
        )

        self.assertTrue(result["ok"])
        self.assertNotIn(secret_value, str(result))
        self.assertTrue(result["password_set"])
        self.assertEqual(result["field_results"]["password"]["input_mode"], "character")
        self.assertNotIn(["input", "text", secret_value], [call[0] for call in client.calls])

    def test_login_screen_controls_are_detected(self):
        result = detect_login_screen(xml_path=self._write_xml(LOGIN_XML))

        self.assertTrue(result["is_login_screen"])
        self.assertEqual(result["username_field"]["resource_id"], "com.bonc.mobile.jlmhim.tt:id/login_user")
        self.assertEqual(result["password_field"]["resource_id"], "com.bonc.mobile.jlmhim.tt:id/login_password")
        self.assertEqual(result["login_button"]["text"], "登录")

    def test_sms_code_screen_is_detected(self):
        result = detect_sms_code_screen(xml_path=self._write_xml(SMS_XML))

        self.assertTrue(result["is_sms_code_screen"])
        self.assertEqual(result["code_field"]["resource_id"], "com.example:id/sms_code")
        self.assertEqual(result["submit_button"]["text"], "确认")

    def test_password_update_prompt_is_detected_with_safe_dismiss(self):
        result = detect_password_update_prompt(xml_path=self._write_xml(PASSWORD_UPDATE_XML))

        self.assertTrue(result["is_password_update_prompt"])
        self.assertEqual(result["dismiss_button"]["text"], "暂不修改")


if __name__ == "__main__":
    unittest.main()
