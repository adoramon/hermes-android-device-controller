"""Authorized enterprise app login helpers.

This module only automates explicit credential entry and user-provided SMS code
entry. It does not read SMS, bypass verification, or perform business actions.
"""

from __future__ import annotations

from pathlib import Path
import os
import re
import time
from typing import Iterable

from .adb_client import AdbClient, get_default_client
from .app_probe import parse_ui_xml
from .device_status import device_status
from .input_actions import open_app
from .screen_reader import dump_screen_xml


USERNAME_ENV = "ENTERPRISE_APP_USERNAME"
PASSWORD_ENV = "ENTERPRISE_APP_PASSWORD"
PACKAGE_ENV = "ENTERPRISE_APP_PACKAGE"
LOGIN_USER_ID_SUFFIX = ":id/login_user"
LOGIN_PASSWORD_ID_SUFFIX = ":id/login_password"
SMS_CODE_PATTERN = re.compile(r"企信验证码\s*[:：]\s*(\d{4,8})")
SMS_KEYWORDS = ("验证码", "短信验证码", "请输入验证码", "获取验证码")
SMS_SUBMIT_TERMS = ("确认", "登录", "提交")
PASSWORD_UPDATE_KEYWORDS = ("修改密码", "更新密码", "密码过期", "初始密码", "重置密码")
PASSWORD_UPDATE_DISMISS_TERMS = ("忽略", "暂不修改", "暂时不修改", "稍后", "以后再说", "跳过", "取消")
STRONG_PASSWORD_UPDATE_DISMISS_TERMS = ("忽略", "暂不修改", "暂时不修改", "以后再说")
APP_UPDATE_KEYWORDS = ("最新版本", "更新内容", "版本大小", "立即更新")
APP_UPDATE_DISMISS_TERMS = ("暂不更新", "以后再说", "稍后", "取消")


def load_enterprise_credentials(env_path: str | Path | None = None) -> dict[str, object]:
    """Load enterprise credentials from environment variables or local .env."""

    env_file = _read_env_file(_resolve_env_path(env_path))
    username = os.environ.get(USERNAME_ENV) or env_file.get(USERNAME_ENV, "")
    password = os.environ.get(PASSWORD_ENV) or env_file.get(PASSWORD_ENV, "")
    package_name = os.environ.get(PACKAGE_ENV) or env_file.get(PACKAGE_ENV, "")
    missing = [
        name
        for name, value in (
            (PACKAGE_ENV, package_name),
            (USERNAME_ENV, username),
            (PASSWORD_ENV, password),
        )
        if not value
    ]
    if missing:
        return {
            "ok": False,
            "message": "Missing enterprise app credential environment variable(s).",
            "missing": missing,
            "env_path": str(_resolve_env_path(env_path)),
        }
    return {
        "ok": True,
        "package": package_name,
        "username": username,
        "password": password,
        "username_masked": _mask_secret(username),
        "password_set": True,
    }


def detect_login_screen(xml_path: str | Path | None = None, client: AdbClient | None = None) -> dict[str, object]:
    """Detect whether the current UI dump is the enterprise login screen."""

    screen = _load_screen_nodes(xml_path=xml_path, client=client)
    if not screen["ok"]:
        return screen
    nodes = screen["nodes"]
    username_node = _find_node_by_resource_id_suffix(nodes, LOGIN_USER_ID_SUFFIX)
    password_node = _find_node_by_resource_id_suffix(nodes, LOGIN_PASSWORD_ID_SUFFIX)
    login_button = _find_login_button(nodes)
    ok = username_node is not None and password_node is not None and login_button is not None
    return {
        "ok": ok,
        "is_login_screen": ok,
        "xml_path": screen.get("xml_path"),
        "username_field": username_node,
        "password_field": password_node,
        "login_button": login_button,
        "message": "Login screen detected." if ok else "Login screen controls were not all found.",
    }


def fill_login_credentials(
    username: str | None = None,
    password: str | None = None,
    *,
    client: AdbClient | None = None,
    xml_path: str | Path | None = None,
) -> dict[str, object]:
    """Fill username and password fields without returning the password."""

    adb = client or get_default_client()
    credentials = None
    if username is None or password is None:
        credentials = load_enterprise_credentials()
        if not credentials["ok"]:
            return credentials
        username = str(credentials["username"])
        password = str(credentials["password"])

    login = detect_login_screen(xml_path=xml_path, client=adb)
    if not login.get("is_login_screen"):
        return {
            "ok": False,
            "message": login.get("message", "Login screen not detected."),
            "login": login,
        }

    username_result = _replace_field_text(adb, login["username_field"], username)
    password_result = _replace_field_text(adb, login["password_field"], password, sensitive=True)
    ok = username_result["ok"] and password_result["ok"]
    return {
        "ok": ok,
        "message": "Credentials filled." if ok else "Failed to fill one or more credential fields.",
        "username_masked": _mask_secret(username),
        "password_set": bool(password),
        "username_field": _node_ref(login["username_field"]),
        "password_field": _node_ref(login["password_field"]),
        "field_results": {
            "username": username_result,
            "password": password_result,
        },
    }


def tap_login_button(
    *,
    client: AdbClient | None = None,
    xml_path: str | Path | None = None,
) -> dict[str, object]:
    """Tap the login button located through UI XML bounds."""

    adb = client or get_default_client()
    login = detect_login_screen(xml_path=xml_path, client=adb)
    if not login.get("login_button"):
        return {
            "ok": False,
            "message": "Login button was not found.",
            "login": login,
        }
    result = _tap_node_center(adb, login["login_button"])
    return {
        "ok": result,
        "message": "Login button tapped." if result else "Login button bounds were unavailable.",
        "button": _node_ref(login["login_button"]),
    }


def detect_sms_code_screen(
    xml_path: str | Path | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    """Detect an SMS verification screen and its input field."""

    screen = _load_screen_nodes(xml_path=xml_path, client=client)
    if not screen["ok"]:
        return screen
    nodes = screen["nodes"]
    keyword_nodes = [node for node in nodes if _node_has_any(node, SMS_KEYWORDS)]
    code_field = _find_sms_code_field(nodes, keyword_nodes)
    submit_button = _find_sms_submit_button(nodes)
    is_sms = bool(keyword_nodes) and code_field is not None
    return {
        "ok": True,
        "is_sms_code_screen": is_sms,
        "xml_path": screen.get("xml_path"),
        "keyword_nodes": keyword_nodes,
        "code_field": code_field,
        "submit_button": submit_button,
        "message": "SMS code screen detected." if is_sms else "SMS code screen not detected.",
    }


def request_sms_code_prompt() -> str:
    return "已进入短信验证码验证，请回复：企信验证码：xxxxxx"


def detect_password_update_prompt(
    xml_path: str | Path | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    """Detect a password update prompt that can be safely postponed."""

    screen = _load_screen_nodes(xml_path=xml_path, client=client)
    if not screen["ok"]:
        return screen
    nodes = screen["nodes"]
    keyword_nodes = [node for node in nodes if _node_has_any(node, PASSWORD_UPDATE_KEYWORDS)]
    dismiss_button = _find_password_update_dismiss_button(nodes)
    is_prompt = bool(keyword_nodes) or _has_strong_password_update_dismiss(nodes)
    return {
        "ok": True,
        "is_password_update_prompt": is_prompt,
        "xml_path": screen.get("xml_path"),
        "keyword_nodes": keyword_nodes,
        "dismiss_button": dismiss_button,
        "message": "Password update prompt detected." if is_prompt else "Password update prompt not detected.",
    }


def dismiss_password_update_prompt(client: AdbClient | None = None) -> dict[str, object]:
    """Tap a safe postpone/ignore option on a password update prompt."""

    adb = client or get_default_client()
    prompt = detect_password_update_prompt(client=adb)
    dismiss_button = prompt.get("dismiss_button")
    if not prompt.get("is_password_update_prompt"):
        return {
            "ok": False,
            "message": "Password update prompt not detected.",
            "prompt": prompt,
        }
    if not dismiss_button:
        return {
            "ok": False,
            "need_manual_confirm": True,
            "message": "Password update prompt detected, but no safe ignore/postpone button was found.",
            "prompt": prompt,
        }
    tapped = _tap_node_center(adb, dismiss_button)
    return {
        "ok": tapped,
        "message": "Password update prompt dismissed." if tapped else "Dismiss button bounds were unavailable.",
        "button": _node_ref(dismiss_button),
    }


def detect_app_update_prompt(
    xml_path: str | Path | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    """Detect an app update prompt that can be safely skipped."""

    screen = _load_screen_nodes(xml_path=xml_path, client=client)
    if not screen["ok"]:
        return screen
    nodes = screen["nodes"]
    keyword_nodes = [node for node in nodes if _node_has_any(node, APP_UPDATE_KEYWORDS)]
    dismiss_button = _find_app_update_dismiss_button(nodes)
    is_prompt = bool(keyword_nodes) and dismiss_button is not None
    return {
        "ok": True,
        "is_app_update_prompt": is_prompt,
        "xml_path": screen.get("xml_path"),
        "keyword_nodes": keyword_nodes,
        "dismiss_button": dismiss_button,
        "message": "App update prompt detected." if is_prompt else "App update prompt not detected.",
    }


def dismiss_app_update_prompt(client: AdbClient | None = None) -> dict[str, object]:
    """Tap a safe skip option on an app update prompt."""

    adb = client or get_default_client()
    prompt = detect_app_update_prompt(client=adb)
    dismiss_button = prompt.get("dismiss_button")
    if not prompt.get("is_app_update_prompt"):
        return {
            "ok": False,
            "message": "App update prompt not detected.",
            "prompt": prompt,
        }
    tapped = _tap_node_center(adb, dismiss_button)
    return {
        "ok": tapped,
        "message": "App update prompt dismissed." if tapped else "Dismiss button bounds were unavailable.",
        "button": _node_ref(dismiss_button),
    }


def submit_sms_code(code: str, *, client: AdbClient | None = None) -> dict[str, object]:
    """Enter a user-provided SMS code and tap a confirmation button when present."""

    if not _is_valid_sms_code(code):
        return {
            "ok": False,
            "message": "验证码格式无效，请回复 4-8 位数字。",
        }
    adb = client or get_default_client()
    sms = detect_sms_code_screen(client=adb)
    if not sms.get("is_sms_code_screen"):
        return {
            "ok": False,
            "message": "当前页面未识别为短信验证码页。",
            "sms": sms,
        }

    fill_result = _replace_field_text(adb, sms["code_field"], code)
    if not fill_result["ok"]:
        return {
            "ok": False,
            "message": "验证码输入失败。",
            "field_result": fill_result,
        }

    submit_button = sms.get("submit_button")
    if not submit_button:
        return {
            "ok": False,
            "need_manual_confirm": True,
            "message": "验证码已填入，但未找到确认/登录/提交按钮，请人工确认。",
            "code_entered": True,
        }

    tapped = _tap_node_center(adb, submit_button)
    return {
        "ok": tapped,
        "need_manual_confirm": not tapped,
        "message": "验证码已提交。" if tapped else "验证码已填入，但按钮 bounds 不可用，请人工确认。",
        "code_entered": True,
        "button": _node_ref(submit_button),
    }


def login_with_credentials(*, client: AdbClient | None = None, wait_seconds: float = 2.0) -> dict[str, object]:
    """Open the app and perform authorized credential login."""

    adb = client or get_default_client()
    credentials = load_enterprise_credentials()
    if not credentials["ok"]:
        return credentials

    launch = open_app(str(credentials["package"]), client=adb)
    if not launch.ok:
        return {
            "ok": False,
            "message": "Failed to open enterprise app.",
            "launch_returncode": launch.returncode,
            "launch_stdout": launch.stdout,
            "launch_stderr": launch.stderr,
        }
    time.sleep(wait_seconds)

    app_update = dismiss_app_update_prompt_if_present(client=adb)
    if app_update.get("is_app_update_prompt") and not app_update.get("ok"):
        return {
            "ok": False,
            "need_manual_confirm": True,
            "message": app_update.get("message", "App update prompt requires manual confirmation."),
            "app_update_prompt": app_update,
        }
    if app_update.get("is_app_update_prompt") and app_update.get("ok"):
        time.sleep(wait_seconds)

    login = detect_login_screen(client=adb)
    if not login.get("is_login_screen"):
        sms = detect_sms_code_screen(client=adb)
        return {
            "ok": False,
            "message": "Login screen was not detected after opening enterprise app.",
            "need_sms_code": bool(sms.get("is_sms_code_screen")),
            "prompt": request_sms_code_prompt() if sms.get("is_sms_code_screen") else None,
            "foreground_package": _foreground_package(adb),
        }

    fill = fill_login_credentials(
        str(credentials["username"]),
        str(credentials["password"]),
        client=adb,
        xml_path=login.get("xml_path"),
    )
    if not fill["ok"]:
        return fill

    adb.shell(["input", "keyevent", "KEYCODE_BACK"])
    time.sleep(0.5)
    tap = tap_login_button(client=adb)
    if not tap["ok"]:
        return tap

    time.sleep(wait_seconds)
    password_update = detect_password_update_prompt(client=adb)
    if password_update.get("is_password_update_prompt"):
        dismissed = dismiss_password_update_prompt(client=adb)
        if not dismissed.get("ok"):
            return {
                "ok": False,
                "need_manual_confirm": dismissed.get("need_manual_confirm", True),
                "message": dismissed.get("message", "Password update prompt requires manual confirmation."),
                "password_update_prompt": password_update,
            }
        time.sleep(wait_seconds)

    sms = detect_sms_code_screen(client=adb)
    if sms.get("is_sms_code_screen"):
        return {
            "ok": False,
            "need_sms_code": True,
            "prompt": request_sms_code_prompt(),
            "username_masked": credentials["username_masked"],
            "password_set": True,
        }

    login_after = detect_login_screen(client=adb)
    foreground_package = _foreground_package(adb)
    logged_in = foreground_package == credentials["package"] and not login_after.get("is_login_screen")
    return {
        "ok": logged_in,
        "need_sms_code": False,
        "message": "Enterprise app login appears complete." if logged_in else "Login did not leave the login screen.",
        "foreground_package": foreground_package,
        "username_masked": credentials["username_masked"],
        "password_set": True,
        "input_modes": _fill_input_modes(fill),
        "login_screen_after_submit": {
            "is_login_screen": bool(login_after.get("is_login_screen")),
            "message": login_after.get("message"),
            "xml_path": login_after.get("xml_path"),
        },
    }


def handle_wechat_sms_code_message(text: str, *, client: AdbClient | None = None) -> dict[str, object]:
    """Extract `企信验证码：xxxxxx` from WeChat text and submit it."""

    code = extract_sms_code(text)
    if not code:
        return {
            "ok": False,
            "message": "未识别到验证码。请按格式回复：企信验证码：xxxxxx",
        }
    return submit_sms_code(code, client=client)


def dismiss_app_update_prompt_if_present(client: AdbClient | None = None) -> dict[str, object]:
    """Dismiss a skippable app update prompt when present; no-op otherwise."""

    adb = client or get_default_client()
    prompt = detect_app_update_prompt(client=adb)
    if not prompt.get("is_app_update_prompt"):
        return {
            "ok": True,
            "is_app_update_prompt": False,
            "message": prompt.get("message", "App update prompt not detected."),
            "prompt": prompt,
        }
    dismissed = dismiss_app_update_prompt(client=adb)
    return {
        **dismissed,
        "is_app_update_prompt": True,
        "prompt": prompt,
    }


def extract_sms_code(text: str) -> str | None:
    match = SMS_CODE_PATTERN.search(text or "")
    return match.group(1) if match else None


def _load_screen_nodes(
    xml_path: str | Path | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    if xml_path:
        return {
            "ok": True,
            "xml_path": str(xml_path),
            "nodes": parse_ui_xml(xml_path),
        }
    adb = client or get_default_client()
    dump = dump_screen_xml(client=adb)
    if not dump.get("ok") or not dump.get("path"):
        return {
            "ok": False,
            "message": dump.get("message", "Failed to dump UI XML."),
            "dump": dump,
            "nodes": [],
        }
    return {
        "ok": True,
        "xml_path": dump.get("path"),
        "nodes": parse_ui_xml(str(dump["path"])),
    }


def _find_node_by_resource_id(nodes: Iterable[dict[str, object]], resource_id: str) -> dict[str, object] | None:
    for node in nodes:
        if node.get("resource_id") == resource_id:
            return node
    return None


def _find_node_by_resource_id_suffix(nodes: Iterable[dict[str, object]], suffix: str) -> dict[str, object] | None:
    for node in nodes:
        if str(node.get("resource_id", "")).endswith(suffix):
            return node
    return None


def _find_login_button(nodes: Iterable[dict[str, object]]) -> dict[str, object] | None:
    for node in nodes:
        if node.get("clickable") and str(node.get("text", "")).strip() == "登录":
            return node
    for node in nodes:
        label = _node_label(node)
        if node.get("clickable") and "login" in str(node.get("resource_id", "")).lower() and "登录" in label:
            return node
    return None


def _find_sms_code_field(
    nodes: list[dict[str, object]],
    keyword_nodes: list[dict[str, object]],
) -> dict[str, object] | None:
    for node in nodes:
        if _is_input_node(node) and _node_has_any(node, SMS_KEYWORDS):
            return node
    input_nodes = [node for node in nodes if _is_input_node(node)]
    if len(input_nodes) == 1 and keyword_nodes:
        return input_nodes[0]
    for node in input_nodes:
        resource_id = str(node.get("resource_id", "")).lower()
        if "code" in resource_id or "sms" in resource_id or "verify" in resource_id:
            return node
    return None


def _find_sms_submit_button(nodes: Iterable[dict[str, object]]) -> dict[str, object] | None:
    for node in nodes:
        if node.get("clickable") and _node_has_any(node, SMS_SUBMIT_TERMS):
            return node
    return None


def _find_password_update_dismiss_button(nodes: Iterable[dict[str, object]]) -> dict[str, object] | None:
    for node in nodes:
        if node.get("clickable") and _node_has_any(node, PASSWORD_UPDATE_DISMISS_TERMS):
            return node
    return None


def _find_app_update_dismiss_button(nodes: Iterable[dict[str, object]]) -> dict[str, object] | None:
    for node in nodes:
        if node.get("clickable") and _node_has_any(node, APP_UPDATE_DISMISS_TERMS):
            return node
    return None


def _has_strong_password_update_dismiss(nodes: Iterable[dict[str, object]]) -> bool:
    return any(_node_has_any(node, STRONG_PASSWORD_UPDATE_DISMISS_TERMS) for node in nodes)


def _replace_field_text(
    adb: AdbClient,
    node: dict[str, object],
    text: str,
    *,
    sensitive: bool = False,
) -> dict[str, object]:
    if not _tap_node_center(adb, node):
        return {
            "ok": False,
            "message": "Field bounds were unavailable.",
        }
    adb.shell(["input", "keyevent", "KEYCODE_MOVE_END"])
    for _ in range(80):
        adb.shell(["input", "keyevent", "KEYCODE_DEL"])
    if sensitive:
        result, input_mode = _input_text_securely(adb, text)
    else:
        result = adb.shell(["input", "text", _format_adb_text(text)])
        input_mode = "bulk"
    time.sleep(0.2)
    return {
        "ok": result.ok,
        "message": "Field text entered." if result.ok else "ADB text input failed.",
        "returncode": result.returncode,
        "input_mode": input_mode,
    }


def _tap_node_center(adb: AdbClient, node: dict[str, object]) -> bool:
    bounds = node.get("bounds")
    if not isinstance(bounds, dict):
        return False
    center_x = bounds.get("center_x")
    center_y = bounds.get("center_y")
    if not isinstance(center_x, int) or not isinstance(center_y, int):
        return False
    return adb.shell(["input", "tap", str(center_x), str(center_y)]).ok


def _format_adb_text(text: str) -> str:
    return "".join(_format_adb_text_char(char) for char in text)


def _format_adb_text_char(char: str) -> str:
    if char == " ":
        return "%s"
    if char in {"&", "|", ";", "<", ">", "(", ")", "$", "`", "\\", '"', "'", "*", "!", "#", "%"}:
        return "\\" + char
    return char


def _input_text_securely(adb: AdbClient, text: str):
    last_result = None
    for char in text:
        last_result = adb.shell(["input", "text", _format_adb_text_char(char)])
        if not last_result.ok:
            paste_result = _paste_text_via_clipboard(adb, text)
            if paste_result.ok:
                return paste_result, "clipboard"
            return last_result, "character"
        time.sleep(0.03)
    if last_result is None:
        return adb.shell(["input", "text", ""]), "character"
    return last_result, "character"


def _paste_text_via_clipboard(adb: AdbClient, text: str):
    set_clipboard = adb.shell(["cmd", "clipboard", "set", "text", text])
    if not set_clipboard.ok:
        return set_clipboard
    paste = adb.shell(["input", "keyevent", "KEYCODE_PASTE"])
    adb.shell(["cmd", "clipboard", "set", "text", ""])
    time.sleep(0.2)
    return paste


def _node_label(node: dict[str, object]) -> str:
    return " ".join(
        str(node.get(key, ""))
        for key in ("text", "content_desc", "resource_id")
        if node.get(key)
    )


def _node_has_any(node: dict[str, object], terms: Iterable[str]) -> bool:
    label = _node_label(node)
    return any(term in label for term in terms)


def _is_input_node(node: dict[str, object]) -> bool:
    class_name = str(node.get("class", ""))
    resource_id = str(node.get("resource_id", "")).lower()
    return "EditText" in class_name or any(marker in resource_id for marker in ("input", "edit", "code"))


def _is_valid_sms_code(code: str) -> bool:
    return bool(re.fullmatch(r"\d{4,8}", code or ""))


def _node_ref(node: object) -> dict[str, object]:
    if not isinstance(node, dict):
        return {}
    return {
        "text": node.get("text", ""),
        "resource_id": node.get("resource_id", ""),
        "class": node.get("class", ""),
        "bounds": node.get("bounds"),
    }


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 2:
        return "*" * len(value)
    return value[0] + "*" * (len(value) - 2) + value[-1]


def _fill_input_modes(fill: dict[str, object]) -> dict[str, object]:
    field_results = fill.get("field_results")
    if not isinstance(field_results, dict):
        return {}
    modes: dict[str, object] = {}
    for name, result in field_results.items():
        if isinstance(result, dict):
            modes[str(name)] = {
                "ok": result.get("ok"),
                "input_mode": result.get("input_mode"),
                "returncode": result.get("returncode"),
            }
    return modes


def _resolve_env_path(env_path: str | Path | None) -> Path:
    if env_path:
        return Path(env_path)
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env
    return Path(__file__).resolve().parents[2] / ".env"


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _foreground_package(adb: AdbClient) -> str | None:
    status = device_status(client=adb)
    return status.get("foreground_package") if isinstance(status, dict) else None


__all__ = [
    "load_enterprise_credentials",
    "detect_login_screen",
    "fill_login_credentials",
    "tap_login_button",
    "detect_sms_code_screen",
    "detect_app_update_prompt",
    "dismiss_app_update_prompt",
    "dismiss_app_update_prompt_if_present",
    "detect_password_update_prompt",
    "dismiss_password_update_prompt",
    "request_sms_code_prompt",
    "submit_sms_code",
    "login_with_credentials",
    "handle_wechat_sms_code_message",
    "extract_sms_code",
]
