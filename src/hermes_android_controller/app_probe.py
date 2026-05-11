"""Read-only enterprise app UI probing helpers."""

from __future__ import annotations

from pathlib import Path
import time
import xml.etree.ElementTree as ET

from .adb_client import AdbClient, AdbCommandResult, get_default_client
from .device_status import device_status
from .env_config import env_value, require_env_value
from .input_actions import open_app
from .screen_reader import dump_screen_xml, take_screenshot


ENTERPRISE_APP_PACKAGE_ENV = "ENTERPRISE_APP_PACKAGE"
ENTERPRISE_APP_PACKAGE = env_value(ENTERPRISE_APP_PACKAGE_ENV)
INPUT_CLASS_MARKERS = ("EditText", "AutoCompleteTextView")
SENSITIVE_ACTION_TERMS = ("打卡", "提交", "确认", "审批通过")
NON_TITLE_TEXT_MARKERS = ("公网安备", "ICP备", "备案", "请输入", "忘记密码")


def open_enterprise_app(client: AdbClient | None = None):
    """Open the configured enterprise app without performing business actions."""

    adb = client or get_default_client()
    package_name = enterprise_app_package()
    before = device_status(client=adb)
    if before.get("foreground_package") == package_name:
        result = AdbCommandResult(
            command=[],
            timeout=adb.default_timeout,
            stdout="Enterprise app is already foreground; monkey launch skipped.",
            stderr="",
            returncode=0,
        )
    else:
        result = open_app(package_name, client=adb)
    time.sleep(3)
    return result


def probe_current_screen(client: AdbClient | None = None) -> dict[str, object]:
    """Capture foreground package, UI XML, and screenshot for read-only inspection."""

    adb = client or get_default_client()
    stable = _wait_for_stable_foreground(client=adb, expected_package=enterprise_app_package())
    status = stable.get("status") if isinstance(stable.get("status"), dict) else device_status(client=adb)
    xml_result = _dump_screen_xml_with_retries(client=adb, attempts=3, interval_seconds=1)
    screenshot_result = take_screenshot(client=adb)
    return {
        "ok": bool(stable.get("ok")) and bool(xml_result.get("ok")) and bool(screenshot_result.get("ok")),
        "foreground_package": status.get("foreground_package"),
        "xml_path": xml_result.get("path"),
        "screenshot_path": screenshot_result.get("path"),
        "status": status,
        "xml": xml_result,
        "screenshot": screenshot_result,
        "diagnostics": {
            "foreground_stability": stable,
            "xml_dump_attempts": xml_result.get("attempts", []),
        },
    }


def parse_ui_xml(xml_path: str | Path) -> list[dict[str, object]]:
    """Parse a uiautomator XML dump into relevant UI nodes."""

    path = Path(xml_path)
    tree = ET.parse(path)
    nodes: list[dict[str, object]] = []
    for element in tree.iter("node"):
        node = _node_from_element(element)
        if _is_relevant_node(node):
            nodes.append(node)
    return nodes


def summarize_screen(client: AdbClient | None = None) -> dict[str, object]:
    """Probe and summarize the current screen for later manual workflow modeling."""

    probe = probe_current_screen(client=client)
    xml_path = probe.get("xml_path")
    nodes: list[dict[str, object]] = []
    parse_error: str | None = None
    if isinstance(xml_path, str) and xml_path:
        try:
            nodes = parse_ui_xml(xml_path)
        except ET.ParseError as exc:
            parse_error = f"Failed to parse UI XML: {exc}"
        except OSError as exc:
            parse_error = f"Failed to read UI XML: {exc}"

    clickable_elements = [node for node in nodes if node.get("clickable") is True]
    input_fields = [node for node in nodes if _is_input_field(node)]
    sensitive_elements = [node for node in clickable_elements if _has_sensitive_action(node)]

    return {
        "ok": bool(probe.get("ok")) and parse_error is None,
        "foreground_package": probe.get("foreground_package"),
        "possible_title": _possible_title(nodes),
        "xml_path": probe.get("xml_path"),
        "screenshot_path": probe.get("screenshot_path"),
        "clickable_elements": clickable_elements,
        "input_fields": input_fields,
        "sensitive_action_risk": {
            "found": bool(sensitive_elements),
            "terms": list(SENSITIVE_ACTION_TERMS),
            "elements": sensitive_elements,
        },
        "node_count": len(nodes),
        "parse_error": parse_error,
        "probe": probe,
    }


def summarize_nodes(
    nodes: list[dict[str, object]],
    foreground_package: str | None = None,
) -> dict[str, object]:
    """Summarize parsed nodes without touching a device. Useful for tests."""

    clickable_elements = [node for node in nodes if node.get("clickable") is True]
    input_fields = [node for node in nodes if _is_input_field(node)]
    sensitive_elements = [node for node in clickable_elements if _has_sensitive_action(node)]
    return {
        "foreground_package": foreground_package,
        "possible_title": _possible_title(nodes),
        "clickable_elements": clickable_elements,
        "input_fields": input_fields,
        "sensitive_action_risk": {
            "found": bool(sensitive_elements),
            "terms": list(SENSITIVE_ACTION_TERMS),
            "elements": sensitive_elements,
        },
        "node_count": len(nodes),
    }


def enterprise_app_package() -> str:
    return require_env_value(ENTERPRISE_APP_PACKAGE_ENV)


def _wait_for_stable_foreground(
    client: AdbClient,
    *,
    expected_package: str | None = None,
    attempts: int = 8,
    interval_seconds: float = 0.5,
) -> dict[str, object]:
    previous_package: str | None = None
    observations: list[dict[str, object]] = []
    last_status: dict[str, object] | None = None
    for attempt in range(1, attempts + 1):
        status = device_status(client=client)
        last_status = status
        foreground_package = status.get("foreground_package")
        observations.append(
            {
                "attempt": attempt,
                "ok": status.get("ok"),
                "foreground_package": foreground_package,
                "message": status.get("message"),
                "foreground_app": _command_result_summary(status.get("foreground_app")),
            }
        )
        if foreground_package and foreground_package == previous_package:
            expected_ok = expected_package is None or foreground_package == expected_package
            return {
                "ok": bool(status.get("ok")) and expected_ok,
                "stable": True,
                "foreground_package": foreground_package,
                "expected_package": expected_package,
                "status": status,
                "observations": observations,
            }
        previous_package = foreground_package if isinstance(foreground_package, str) else None
        if attempt < attempts:
            time.sleep(interval_seconds)
    return {
        "ok": False,
        "stable": False,
        "foreground_package": previous_package,
        "expected_package": expected_package,
        "status": last_status or {},
        "observations": observations,
    }


def _dump_screen_xml_with_retries(
    client: AdbClient,
    *,
    attempts: int,
    interval_seconds: float,
) -> dict[str, object]:
    results = []
    last_result: dict[str, object] | None = None
    for attempt in range(1, attempts + 1):
        result = dump_screen_xml(client=client)
        last_result = result
        results.append(
            {
                "attempt": attempt,
                "ok": result.get("ok"),
                "path": result.get("path"),
                "message": result.get("message"),
                "dump": _command_result_summary(result.get("dump")),
                "pull": _command_result_summary(result.get("pull")),
            }
        )
        if result.get("ok"):
            result["attempts"] = results
            return result
        if attempt < attempts:
            time.sleep(interval_seconds)
    fallback = dict(last_result or {})
    fallback["ok"] = False
    fallback["attempts"] = results
    fallback["message"] = "Failed to dump screen XML after retries."
    return fallback


def _command_result_summary(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    return {
        "returncode": getattr(value, "returncode", None),
        "stdout": getattr(value, "stdout", None),
        "stderr": getattr(value, "stderr", None),
        "timed_out": getattr(value, "timed_out", False),
        "command": getattr(value, "command", None),
    }


def _node_from_element(element: ET.Element) -> dict[str, object]:
    text = element.attrib.get("text", "")
    resource_id = element.attrib.get("resource-id", "")
    class_name = element.attrib.get("class", "")
    content_desc = element.attrib.get("content-desc", "")
    return {
        "text": text,
        "resource_id": resource_id,
        "class": class_name,
        "content_desc": content_desc,
        "clickable": _parse_bool(element.attrib.get("clickable")),
        "enabled": _parse_bool(element.attrib.get("enabled")),
        "bounds": _parse_bounds(element.attrib.get("bounds", "")),
    }


def _is_relevant_node(node: dict[str, object]) -> bool:
    return bool(
        node.get("text")
        or node.get("content_desc")
        or node.get("resource_id")
        or node.get("clickable") is True
    )


def _parse_bool(value: str | None) -> bool:
    return str(value).lower() == "true"


def _parse_bounds(value: str) -> dict[str, int] | None:
    if not value:
        return None
    normalized = value.replace("][", ",").replace("[", "").replace("]", "")
    parts = normalized.split(",")
    if len(parts) != 4:
        return None
    try:
        left, top, right, bottom = [int(part) for part in parts]
    except ValueError:
        return None
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": max(0, right - left),
        "height": max(0, bottom - top),
        "center_x": left + max(0, right - left) // 2,
        "center_y": top + max(0, bottom - top) // 2,
    }


def _is_input_field(node: dict[str, object]) -> bool:
    class_name = str(node.get("class", ""))
    if any(marker in class_name for marker in INPUT_CLASS_MARKERS):
        return True
    resource_id = str(node.get("resource_id", "")).lower()
    text = str(node.get("text", "")).lower()
    return any(marker in resource_id or marker in text for marker in ("input", "edit", "search", "输入"))


def _has_sensitive_action(node: dict[str, object]) -> bool:
    label = " ".join(
        str(node.get(key, ""))
        for key in ("text", "content_desc", "resource_id")
        if node.get(key)
    )
    return any(term in label for term in SENSITIVE_ACTION_TERMS)


def _possible_title(nodes: list[dict[str, object]]) -> str | None:
    for node in nodes:
        text = str(node.get("text") or node.get("content_desc") or "").strip()
        if _is_title_candidate(text, node) and not node.get("clickable"):
            return text
    for node in nodes:
        text = str(node.get("text") or node.get("content_desc") or "").strip()
        if _is_title_candidate(text, node):
            return text
    return None


def _is_title_candidate(text: str, node: dict[str, object]) -> bool:
    if not text or _has_sensitive_action(node):
        return False
    if any(marker in text for marker in NON_TITLE_TEXT_MARKERS):
        return False
    if _is_input_field(node):
        return False
    return True


__all__ = [
    "ENTERPRISE_APP_PACKAGE",
    "ENTERPRISE_APP_PACKAGE_ENV",
    "SENSITIVE_ACTION_TERMS",
    "enterprise_app_package",
    "open_enterprise_app",
    "probe_current_screen",
    "parse_ui_xml",
    "summarize_screen",
    "summarize_nodes",
]
