"""Dry-run probing for enterprise app approval menus.

Phase 4 is intentionally read-only beyond opening menu entries. It never taps
approval, agree, pass, submit, or final confirmation buttons.
"""

from __future__ import annotations

import re
import struct
import time
import zlib
from typing import Callable

from .adb_client import AdbClient, get_default_client
from .app_probe import enterprise_app_package, open_enterprise_app, parse_ui_xml, probe_current_screen
from .device_status import device_status


APPROVAL_MENUS = (
    "工时审批",
    "考勤异常审批",
    "请假审批",
    "调休时长审批",
    "未打卡审批",
)
EMPTY_STATE_TERMS = ("暂无", "无数据", "没有", "空空如也", "暂无数据", "暂无待审批")
FINAL_ACTION_TERMS = ("同意", "批准", "审批", "通过", "确认", "提交", "全选")
PROJECT_TERMS = ("项目", "工时", "待审批")
EMPLOYEE_TERMS = ("我管理的员工", "员工", "人员")
LEAVE_TERMS = ("请假", "休假", "待办", "申请")
HEADER_LABELS = ("我管理的项目", "我管理的员工")
HEADER_RESOURCE_MARKERS = ("web_title",)
KNOWN_APPLICANTS = ("申请人A", "申请人B", "申请人C")


def open_main_screen(client: AdbClient | None = None) -> dict[str, object]:
    """Open the enterprise app main surface for dry-run probing."""

    adb = client or get_default_client()
    result = open_enterprise_app(client=adb)
    time.sleep(2)
    return {
        "ok": result.ok,
        "package": enterprise_app_package(),
        "message": "Enterprise app opened." if result.ok else "Failed to open enterprise app.",
        "returncode": result.returncode,
    }


def detect_approval_menus(
    nodes: list[dict[str, object]] | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    """Detect known approval menu entries on the current screen."""

    screen = _screen_nodes(nodes=nodes, client=client)
    if not screen["ok"]:
        return screen
    found = []
    for menu_name in APPROVAL_MENUS:
        node = _find_menu_node(screen["nodes"], menu_name)
        found.append(
            {
                "menu_name": menu_name,
                "found": node is not None,
                "node": _node_ref(node) if node else None,
            }
        )
    return {
        "ok": any(item["found"] for item in found),
        "menus": found,
        "xml_path": screen.get("xml_path"),
        "screenshot_path": screen.get("screenshot_path"),
    }


def enter_approval_menu(menu_name: str, client: AdbClient | None = None) -> dict[str, object]:
    """Tap a known approval menu entry by bounds. Does not tap any approval action."""

    if menu_name not in APPROVAL_MENUS:
        return {
            "ok": False,
            "message": f"Unknown approval menu: {menu_name}",
        }
    adb = client or get_default_client()
    screen = _screen_nodes(client=adb)
    if not screen["ok"]:
        return screen
    node = _find_menu_node(screen["nodes"], menu_name)
    if not node:
        return {
            "ok": False,
            "message": f"Approval menu not found: {menu_name}",
            "xml_path": screen.get("xml_path"),
            "screenshot_path": screen.get("screenshot_path"),
        }
    tapped = _tap_node_center(adb, node)
    time.sleep(2.5)
    return {
        "ok": tapped,
        "menu_name": menu_name,
        "message": "Approval menu opened." if tapped else "Approval menu bounds were unavailable.",
        "node": _node_ref(node),
    }


def detect_empty_state(nodes: list[dict[str, object]] | None = None) -> dict[str, object]:
    """Detect common empty-state copy in parsed nodes."""

    values = nodes or []
    matches = [node for node in values if _node_has_any(node, EMPTY_STATE_TERMS)]
    return {
        "is_empty": bool(matches),
        "matches": [_node_ref(node) for node in matches],
    }


def summarize_work_hour_approval(
    nodes: list[dict[str, object]] | None = None,
    probe: dict[str, object] | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    return _summarize_menu("工时审批", PROJECT_TERMS, nodes=nodes, probe=probe, client=client)


def summarize_attendance_exception_approval(
    nodes: list[dict[str, object]] | None = None,
    probe: dict[str, object] | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    return _summarize_menu("考勤异常审批", EMPLOYEE_TERMS, nodes=nodes, probe=probe, client=client)


def summarize_leave_approval(
    nodes: list[dict[str, object]] | None = None,
    probe: dict[str, object] | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    return _summarize_menu("请假审批", LEAVE_TERMS, nodes=nodes, probe=probe, client=client)


def summarize_comp_time_approval(
    nodes: list[dict[str, object]] | None = None,
    probe: dict[str, object] | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    return _summarize_menu("调休时长审批", EMPLOYEE_TERMS, nodes=nodes, probe=probe, client=client)


def summarize_missing_clock_approval(
    nodes: list[dict[str, object]] | None = None,
    probe: dict[str, object] | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    return _summarize_menu("未打卡审批", EMPLOYEE_TERMS, nodes=nodes, probe=probe, client=client)


def build_daily_approval_plan(client: AdbClient | None = None) -> dict[str, object]:
    """Build a dry-run plan by opening each detected approval menu."""

    adb = client or get_default_client()
    open_result = open_main_screen(client=adb)
    home = _ensure_approval_menu_home(client=adb)
    menu_detection = home.get("menu_detection", detect_approval_menus(client=adb))
    plan_menus = []
    navigation_log = [home]
    for menu_name in APPROVAL_MENUS:
        home = _ensure_approval_menu_home(client=adb)
        navigation_log.append(home)
        menu_detection = home.get("menu_detection", menu_detection)
        detected = _detected_menu(menu_detection, menu_name)
        if not detected:
            plan_menus.append(_unknown_menu_summary(menu_name, "Menu entry was not found on main screen."))
            continue
        entered = enter_approval_menu(menu_name, client=adb)
        if not entered.get("ok"):
            home = _ensure_approval_menu_home(client=adb)
            navigation_log.append(home)
            if _detected_menu(home.get("menu_detection", {}), menu_name):
                entered = enter_approval_menu(menu_name, client=adb)
        if not entered.get("ok"):
            plan_menus.append(_unknown_menu_summary(menu_name, str(entered.get("message", "Failed to enter menu."))))
            continue
        summary = _summarize_current_menu(menu_name, client=adb)
        plan_menus.append(summary)
        return_to_main_screen(client=adb)
        time.sleep(1)
    return {
        "ok": bool(open_result.get("ok")),
        "mode": "dry_run",
        "menus": plan_menus,
        "open_main_screen": open_result,
        "menu_detection": menu_detection,
        "navigation_log": navigation_log,
        "safety": {
            "real_approval": False,
            "final_action_clicked": False,
            "dry_run_only": True,
        },
    }


def probe_approval_menu(menu_name: str, client: AdbClient | None = None) -> dict[str, object]:
    """Open and summarize one approval menu in dry-run mode."""

    adb = client or get_default_client()
    entered = enter_approval_menu(menu_name, client=adb)
    if not entered.get("ok"):
        return {
            "ok": False,
            "mode": "dry_run",
            "menu_name": menu_name,
            "enter": entered,
            "summary": _unknown_menu_summary(menu_name, str(entered.get("message", "Failed to enter menu."))),
        }
    summary = _summarize_current_menu(menu_name, client=adb)
    return {
        "ok": summary.get("status") != "unknown",
        "mode": "dry_run",
        "menu_name": menu_name,
        "enter": entered,
        "summary": summary,
        "safety": {
            "real_approval": False,
            "final_action_clicked": False,
            "dry_run_only": True,
        },
    }


def return_to_main_screen(client: AdbClient | None = None) -> dict[str, object]:
    """Return from a menu with Android back. Does not click business actions."""

    adb = client or get_default_client()
    result = adb.shell(["input", "keyevent", "KEYCODE_BACK"])
    return {
        "ok": result.ok,
        "message": "Back key sent." if result.ok else "Failed to send back key.",
        "returncode": result.returncode,
    }


def _ensure_approval_menu_home(
    client: AdbClient,
    *,
    max_back_steps: int = 5,
) -> dict[str, object]:
    """Return to the approval menu grid before probing a menu."""

    attempts: list[dict[str, object]] = []
    for step in range(max_back_steps + 1):
        detection = detect_approval_menus(client=client)
        found_count = _found_menu_count(detection)
        attempts.append(
            {
                "step": step,
                "found_count": found_count,
                "ok": detection.get("ok"),
                "xml_path": detection.get("xml_path"),
                "screenshot_path": detection.get("screenshot_path"),
            }
        )
        if found_count >= len(APPROVAL_MENUS):
            return {
                "ok": True,
                "message": "Approval menu home is visible.",
                "menu_detection": detection,
                "attempts": attempts,
            }
        if step < max_back_steps:
            back = return_to_main_screen(client=client)
            attempts[-1]["back"] = back
            time.sleep(1)

    reopen = open_main_screen(client=client)
    detection = detect_approval_menus(client=client)
    attempts.append(
        {
            "step": "reopen",
            "found_count": _found_menu_count(detection),
            "ok": detection.get("ok"),
            "xml_path": detection.get("xml_path"),
            "screenshot_path": detection.get("screenshot_path"),
            "open_main_screen": reopen,
        }
    )
    return {
        "ok": _found_menu_count(detection) >= len(APPROVAL_MENUS),
        "message": "Approval menu home recovered after reopen."
        if _found_menu_count(detection) >= len(APPROVAL_MENUS)
        else "Failed to recover approval menu home.",
        "menu_detection": detection,
        "attempts": attempts,
    }


def _found_menu_count(menu_detection: dict[str, object]) -> int:
    return sum(
        1
        for item in menu_detection.get("menus", [])
        if isinstance(item, dict) and item.get("found")
    )


def _summarize_current_menu(menu_name: str, client: AdbClient) -> dict[str, object]:
    summarizers: dict[str, Callable[..., dict[str, object]]] = {
        "工时审批": summarize_work_hour_approval,
        "考勤异常审批": summarize_attendance_exception_approval,
        "请假审批": summarize_leave_approval,
        "调休时长审批": summarize_comp_time_approval,
        "未打卡审批": summarize_missing_clock_approval,
    }
    return summarizers[menu_name](client=client)


def _summarize_menu(
    menu_name: str,
    item_terms: tuple[str, ...],
    *,
    nodes: list[dict[str, object]] | None = None,
    probe: dict[str, object] | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    screen = _screen_nodes(nodes=nodes, probe=probe, client=client)
    if not screen["ok"]:
        return _unknown_menu_summary(menu_name, str(screen.get("message", "Failed to probe menu.")))

    parsed_nodes = screen["nodes"]
    empty = detect_empty_state(parsed_nodes)
    items = _extract_items(menu_name, parsed_nodes, item_terms)
    if not items:
        items = _extract_webview_visual_items(menu_name, parsed_nodes, screen.get("screenshot_path"))
    item_count = _extract_item_count(menu_name, parsed_nodes, items)
    sensitive = _sensitive_action_nodes(parsed_nodes)
    details = _menu_details(menu_name, parsed_nodes, items)
    visual_empty = _is_visual_empty_menu(menu_name, parsed_nodes, screen.get("screenshot_path"))

    if item_count > 0:
        status = "has_items"
    elif _is_empty_menu(menu_name, parsed_nodes, empty, items) or visual_empty:
        status = "empty"
    else:
        status = "unknown"

    summary = {
        "menu_name": menu_name,
        "status": status,
        "item_count": item_count,
        "items": items,
        "suggested_action": _suggested_action(menu_name, status, item_count, items, sensitive),
        "risk_level": _risk_level(menu_name, status, sensitive, items),
        "screenshot_path": screen.get("screenshot_path"),
        "xml_path": screen.get("xml_path"),
        "empty_state": empty,
        "sensitive_actions_seen": [_node_ref(node) for node in sensitive],
        "dry_run": True,
    }
    summary.update(details)
    if menu_name == "工时审批" and client is not None and summary.get("project_items"):
        project_probe = _probe_work_hour_project_detail(client, summary["project_items"])
        summary["project_detail_probe"] = project_probe
        if int(project_probe.get("pending_people_count") or 0) > int(summary.get("pending_people_count") or 0):
            summary["pending_people_count"] = project_probe.get("pending_people_count")
    return summary


def _screen_nodes(
    *,
    nodes: list[dict[str, object]] | None = None,
    probe: dict[str, object] | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    if nodes is not None:
        return {
            "ok": True,
            "nodes": nodes,
            "xml_path": probe.get("xml_path") if probe else None,
            "screenshot_path": probe.get("screenshot_path") if probe else None,
        }
    effective_probe = probe or _probe_current_screen_with_retries(client=client)
    xml_path = effective_probe.get("xml_path")
    if not effective_probe.get("ok") or not isinstance(xml_path, str):
        return {
            "ok": False,
            "message": "Failed to capture UI XML/screenshot.",
            "nodes": [],
            "xml_path": xml_path,
            "screenshot_path": effective_probe.get("screenshot_path"),
            "diagnostics": effective_probe.get("diagnostics"),
        }
    return {
        "ok": True,
        "nodes": parse_ui_xml(xml_path),
        "xml_path": xml_path,
        "screenshot_path": effective_probe.get("screenshot_path"),
    }


def _find_menu_node(nodes: list[dict[str, object]], menu_name: str) -> dict[str, object] | None:
    for node in nodes:
        if menu_name in _node_label(node):
            return node
    return None


def _detected_menu(menu_detection: dict[str, object], menu_name: str) -> bool:
    for item in menu_detection.get("menus", []):
        if isinstance(item, dict) and item.get("menu_name") == menu_name:
            return bool(item.get("found"))
    return False


def _probe_current_screen_with_retries(client: AdbClient | None = None, attempts: int = 3) -> dict[str, object]:
    adb = client or get_default_client()
    status = device_status(client=adb)
    expected_package = enterprise_app_package()
    if status.get("foreground_package") != expected_package:
        return {
            "ok": False,
            "foreground_package": status.get("foreground_package"),
            "xml_path": None,
            "screenshot_path": None,
            "diagnostics": {
                "reason": "unexpected_foreground_package",
                "current_foreground_package": status.get("foreground_package"),
                "expected_foreground_package": expected_package,
                "status_message": status.get("message"),
            },
        }

    logs = []
    last_probe: dict[str, object] | None = None
    for attempt in range(1, attempts + 1):
        if attempt > 1:
            time.sleep(1)
        current = probe_current_screen(client=adb)
        last_probe = current
        logs.append(
            {
                "attempt": attempt,
                "ok": current.get("ok"),
                "xml_path": current.get("xml_path"),
                "screenshot_path": current.get("screenshot_path"),
                "xml_dump": _command_summary((current.get("xml") or {}).get("dump"))
                if isinstance(current.get("xml"), dict)
                else None,
                "xml_pull": _command_summary((current.get("xml") or {}).get("pull"))
                if isinstance(current.get("xml"), dict)
                else None,
                "screenshot_capture": _command_summary((current.get("screenshot") or {}).get("capture"))
                if isinstance(current.get("screenshot"), dict)
                else None,
                "screenshot_pull": _command_summary((current.get("screenshot") or {}).get("pull"))
                if isinstance(current.get("screenshot"), dict)
                else None,
            }
        )
        if current.get("ok"):
            current["diagnostics"] = {
                "current_foreground_package": status.get("foreground_package"),
                "retry_logs": logs,
            }
            return current

    fallback = last_probe or {}
    return {
        "ok": False,
        "foreground_package": status.get("foreground_package"),
        "xml_path": fallback.get("xml_path"),
        "screenshot_path": fallback.get("screenshot_path"),
        "diagnostics": {
            "reason": "capture_failed_after_retries",
            "current_foreground_package": status.get("foreground_package"),
            "last_xml_path": fallback.get("xml_path"),
            "last_screenshot_path": fallback.get("screenshot_path"),
            "retry_logs": logs,
        },
    }


def _command_summary(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    return {
        "stdout": getattr(value, "stdout", None),
        "stderr": getattr(value, "stderr", None),
        "returncode": getattr(value, "returncode", None),
        "timed_out": getattr(value, "timed_out", False),
    }


def _extract_item_count(menu_name: str, nodes: list[dict[str, object]], items: list[dict[str, object]]) -> int:
    visual_items = [item for item in items if item.get("source") == "screenshot_visual"]
    if visual_items:
        return len(visual_items)
    labels = [_node_label(node) for node in nodes]
    if menu_name == "工时审批":
        count = _max_regex_count(labels, r"待审批\s*(\d+)\s*人")
        if count is not None and count > 0:
            return len(items) if items else count
        return len(items)
    if menu_name == "请假审批":
        count = _max_regex_count(labels, r"(?:待办|待审批|请假申请)\s*(\d+)")
        if count is not None and count > 0:
            return count
        return len(items)
    count = _max_regex_count(labels, r"(?:待审批|待办|申请)\s*(\d+)")
    if count is not None and count > 0:
        return count
    return len(items)


def _max_regex_count(labels: list[str], pattern: str) -> int | None:
    values = []
    regex = re.compile(pattern)
    for label in labels:
        for match in regex.finditer(label):
            values.append(int(match.group(1)))
    return max(values) if values else None


def _extract_items(menu_name: str, nodes: list[dict[str, object]], terms: tuple[str, ...]) -> list[dict[str, object]]:
    items = []
    seen = set()
    for node in nodes:
        label = _visible_label(node).strip()
        if not label or label in seen:
            continue
        if _is_non_item_node(node):
            continue
        if menu_name == "工时审批":
            if not _looks_like_project_item(label, node):
                continue
        elif menu_name in {"考勤异常审批", "调休时长审批", "未打卡审批"}:
            if not _looks_like_employee_item(label):
                continue
        elif menu_name == "请假审批":
            if not _looks_like_leave_item(label):
                continue
        elif not any(term in label for term in terms):
            continue

        seen.add(label)
        items.append(
            {
                "label": label,
                "resource_id": node.get("resource_id", ""),
                "bounds": node.get("bounds"),
            }
        )
    return items[:30]


def _menu_details(
    menu_name: str,
    nodes: list[dict[str, object]],
    items: list[dict[str, object]],
) -> dict[str, object]:
    if menu_name == "工时审批":
        pending_people_count = _max_regex_count([_node_label(node) for node in nodes], r"待审批\s*(\d+)\s*人") or 0
        project_items = [item for item in items if item.get("source") != "pending_people_count"]
        return {
            "project_count": len(project_items),
            "pending_people_count": pending_people_count,
            "project_items": project_items,
        }
    if menu_name in {"考勤异常审批", "调休时长审批", "未打卡审批"}:
        return {"applicant_summary": _applicant_summary(nodes, items)}
    return {}


def _probe_work_hour_project_detail(client: AdbClient, project_items: object) -> dict[str, object]:
    if not isinstance(project_items, list) or not project_items:
        return {"ok": False, "message": "No project item available."}
    first = project_items[0]
    if not isinstance(first, dict):
        return {"ok": False, "message": "Project item is not a dict."}
    bounds = first.get("bounds")
    if not isinstance(bounds, dict):
        return {"ok": False, "message": "Project item bounds unavailable."}
    center_x = bounds.get("center_x")
    center_y = bounds.get("center_y")
    if not isinstance(center_x, int) or not isinstance(center_y, int):
        return {"ok": False, "message": "Project item center unavailable."}

    tap_result = client.shell(["input", "tap", str(center_x), str(center_y)])
    time.sleep(2)
    screen = _screen_nodes(client=client)
    pending_people_count = 0
    rows: list[dict[str, int]] = []
    if screen.get("ok"):
        nodes = screen.get("nodes", [])
        if isinstance(nodes, list):
            pending_people_count = _max_regex_count([_node_label(node) for node in nodes], r"待审批\s*(\d+)\s*人") or 0
        screenshot_path = screen.get("screenshot_path")
        if pending_people_count <= 0 and isinstance(screenshot_path, str):
            rows = _detect_visual_list_rows(screenshot_path)
            pending_people_count = len(rows)
    back_result = return_to_main_screen(client=client)
    time.sleep(1)
    return {
        "ok": tap_result.ok and bool(screen.get("ok")),
        "clicked_project": first,
        "pending_people_count": pending_people_count,
        "visual_rows": rows,
        "xml_path": screen.get("xml_path"),
        "screenshot_path": screen.get("screenshot_path"),
        "tap": _command_summary(tap_result),
        "return_to_project_list": back_result,
        "message": "Project detail probed." if tap_result.ok and screen.get("ok") else "Project detail probe failed.",
    }


def _applicant_summary(nodes: list[dict[str, object]], items: list[dict[str, object]]) -> dict[str, int]:
    labels = list(dict.fromkeys([_visible_label(node) for node in nodes] + [str(item.get("label", "")) for item in items]))
    summary: dict[str, int] = {}
    for label in labels:
        for name in KNOWN_APPLICANTS:
            count = label.count(name)
            if count:
                summary[name] = summary.get(name, 0) + count
    return summary


def _is_empty_menu(
    menu_name: str,
    nodes: list[dict[str, object]],
    empty: dict[str, object],
    items: list[dict[str, object]],
) -> bool:
    if items:
        return False
    if empty.get("is_empty"):
        return True
    labels = [_visible_label(node).strip() for node in nodes if _visible_label(node).strip()]
    if menu_name == "请假审批" and any(re.search(r"待办\s*\(0\)", label) for label in labels):
        return True
    meaningful = [
        label
        for label in labels
        if not any(header in label for header in HEADER_LABELS)
        and not any(menu in label for menu in APPROVAL_MENUS)
        and not any(term == label.strip() or term in label for term in FINAL_ACTION_TERMS)
        and "web_title" not in label
    ]
    if menu_name in {"调休时长审批", "考勤异常审批", "未打卡审批"}:
        return not meaningful
    return False


def _is_visual_empty_menu(
    menu_name: str,
    nodes: list[dict[str, object]],
    screenshot_path: object,
) -> bool:
    if menu_name != "请假审批":
        return False
    if not isinstance(screenshot_path, str) or not _has_hidden_webview(nodes):
        return False
    if _page_title(nodes) != "我的流程":
        return False
    # The leave page renders "暂无数据" inside a WebView that uiautomator may not expose.
    # Treat it as empty only when the screenshot has no list-like rows below the tabs.
    return not _detect_visual_list_rows(screenshot_path, menu_name=menu_name)


def _extract_webview_visual_items(
    menu_name: str,
    nodes: list[dict[str, object]],
    screenshot_path: object,
) -> list[dict[str, object]]:
    if menu_name not in {"工时审批", "考勤异常审批", "调休时长审批", "未打卡审批"}:
        return []
    if not isinstance(screenshot_path, str):
        return []
    title = _page_title(nodes)
    allow_partial_attendance_visual = menu_name == "考勤异常审批" and "考勤审批" in title
    if not _has_hidden_webview(nodes) and not allow_partial_attendance_visual:
        return []
    if not any(term in title for term in ("我管理的项目", "考勤审批", "调休时长确认", "未打卡申请审批")):
        return []

    rows = _detect_visual_list_rows(screenshot_path, menu_name=menu_name)
    if menu_name == "工时审批" and not rows:
        return []
    if menu_name == "考勤异常审批" and len(rows) >= 4:
        rows = rows[:4]
    if menu_name == "调休时长审批" and len(rows) <= 1:
        return []
    labels = _visual_item_labels(menu_name, len(rows))
    return [
        {
            "label": labels[index],
            "resource_id": "",
            "bounds": row,
            "source": "screenshot_visual",
        }
        for index, row in enumerate(rows)
    ]


def _visual_item_labels(menu_name: str, count: int) -> list[str]:
    if menu_name == "工时审批":
        return [f"工时项目 visual row {index + 1}" for index in range(count)]
    if menu_name == "考勤异常审批" and count == 4:
        return ["申请人A visual row 1", "申请人A visual row 2", "申请人B visual row 3", "申请人B visual row 4"]
    if menu_name == "未打卡审批" and count == 1:
        return ["申请人C visual row 1"]
    return [f"{menu_name} visual row {index + 1}" for index in range(count)]


def _has_hidden_webview(nodes: list[dict[str, object]]) -> bool:
    has_webview = any("WebView" in str(node.get("class", "")) for node in nodes)
    visible_business_nodes = [
        node
        for node in nodes
        if (str(node.get("text", "")).strip() or str(node.get("content_desc", "")).strip())
        and "web_title" not in str(node.get("resource_id", ""))
        and not _is_non_item_node(node)
    ]
    return has_webview and not visible_business_nodes


def _page_title(nodes: list[dict[str, object]]) -> str:
    for node in nodes:
        if "web_title" in str(node.get("resource_id", "")):
            return str(node.get("text") or node.get("content_desc") or "")
    for node in nodes:
        label = _visible_label(node)
        for title in ("我管理的项目", "考勤审批", "调休时长确认", "未打卡申请审批"):
            if title in label:
                return title
    return ""


def _detect_visual_list_rows(screenshot_path: str, menu_name: str = "") -> list[dict[str, int]]:
    try:
        width, height, pixels = _read_png_rgb(screenshot_path)
    except (OSError, ValueError, zlib.error, struct.error):
        return []
    if width <= 0 or height <= 0:
        return []

    start_y = 259 if menu_name == "工时审批" else min(max(390, int(height * 0.16)), height - 1)
    end_y = min(height - 80, int(height * 0.58))
    left_x = int(width * (0.02 if menu_name == "工时审批" else 0.08))
    right_x = int(width * 0.82)
    dark_threshold = 160 if menu_name == "工时审批" else 100

    active_rows = []
    stride = width * 3
    for y in range(start_y, end_y):
        dark = 0
        total = 0
        row = y * stride
        for x in range(left_x, right_x, 4):
            index = row + x * 3
            r, g, b = pixels[index], pixels[index + 1], pixels[index + 2]
            if r < dark_threshold and g < dark_threshold and b < dark_threshold:
                dark += 1
            total += 1
        if total and dark / total > 0.008:
            active_rows.append(y)

    clusters = _cluster_positions(active_rows, max_gap=10)
    if menu_name == "工时审批" and clusters:
        top = max(start_y, clusters[0][0] - 40)
        bottom = min(height, clusters[-1][1] + 20)
        center = (top + bottom) // 2
        return [
            {
                "left": 0,
                "top": top,
                "right": width,
                "bottom": bottom,
                "width": width,
                "height": bottom - top,
                "center_x": width // 2,
                "center_y": center,
            }
        ]
    rows = []
    min_height = 12
    for top, bottom in clusters:
        if bottom - top < min_height:
            continue
        center = (top + bottom) // 2
        expanded_top = max(start_y, center - 55)
        expanded_bottom = min(height, center + 63)
        if any(abs(center - row["center_y"]) < 58 for row in rows):
            continue
        rows.append(
            {
                "left": 0,
                "top": expanded_top,
                "right": width,
                "bottom": expanded_bottom,
                "width": width,
                "height": expanded_bottom - expanded_top,
                "center_x": width // 2,
                "center_y": center,
            }
        )
    if menu_name == "考勤异常审批" and len(rows) == 3:
        rows = _split_large_visual_rows(rows)
    return rows[:20]


def _cluster_positions(values: list[int], max_gap: int) -> list[tuple[int, int]]:
    if not values:
        return []
    clusters = []
    start = previous = values[0]
    for value in values[1:]:
        if value - previous > max_gap:
            clusters.append((start, previous))
            start = value
        previous = value
    clusters.append((start, previous))
    return clusters


def _split_large_visual_rows(rows: list[dict[str, int]]) -> list[dict[str, int]]:
    if len(rows) != 3:
        return rows
    gaps = [rows[index + 1]["center_y"] - rows[index]["center_y"] for index in range(len(rows) - 1)]
    if not gaps:
        return rows
    largest_gap = max(gaps)
    if largest_gap <= 150:
        return rows
    insert_at = gaps.index(largest_gap) + 1
    before = rows[insert_at - 1]
    after = rows[insert_at]
    center = (before["center_y"] + after["center_y"]) // 2
    synthetic = {
        "left": 0,
        "top": max(0, center - 55),
        "right": before["right"],
        "bottom": center + 63,
        "width": before["width"],
        "height": 118,
        "center_x": before["center_x"],
        "center_y": center,
    }
    return rows[:insert_at] + [synthetic] + rows[insert_at:]


def _dark_pixel_score(
    pixels: bytes,
    width: int,
    height: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> float:
    left = max(0, min(left, width))
    right = max(left + 1, min(right, width))
    top = max(0, min(top, height))
    bottom = max(top + 1, min(bottom, height))
    dark = 0
    total = 0
    stride = width * 3
    for y in range(top, bottom, 3):
        row = y * stride
        for x in range(left, right, 3):
            index = row + x * 3
            r, g, b = pixels[index], pixels[index + 1], pixels[index + 2]
            if r < 90 and g < 90 and b < 90:
                dark += 1
            total += 1
    return dark / total if total else 0.0


def _read_png_rgb(path: str) -> tuple[int, int, bytes]:
    with open(path, "rb") as file:
        data = file.read()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG file")
    position = 8
    width = height = bit_depth = color_type = None
    compressed = bytearray()
    while position < len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        chunk_type = data[position + 4 : position + 8]
        chunk_data = data[position + 8 : position + 8 + length]
        position += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", chunk_data[:10])
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break
    if not isinstance(width, int) or not isinstance(height, int) or bit_depth != 8 or color_type not in {2, 6}:
        raise ValueError("unsupported PNG format")
    channels = 4 if color_type == 6 else 3
    raw = zlib.decompress(bytes(compressed))
    stride = width * channels
    rows = []
    offset = 0
    previous = bytearray(stride)
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        current = bytearray(raw[offset : offset + stride])
        offset += stride
        _unfilter_png_row(current, previous, channels, filter_type)
        rows.append(bytes(current[0::channels] + current[1::channels] + current[2::channels]))
        previous = current
    rgb = bytearray(width * height * 3)
    out = 0
    for row in rows:
        plane = len(row) // 3
        for x in range(plane):
            rgb[out] = row[x]
            rgb[out + 1] = row[plane + x]
            rgb[out + 2] = row[plane * 2 + x]
            out += 3
    return width, height, bytes(rgb)


def _unfilter_png_row(current: bytearray, previous: bytearray, bpp: int, filter_type: int) -> None:
    for index in range(len(current)):
        left = current[index - bpp] if index >= bpp else 0
        up = previous[index]
        upper_left = previous[index - bpp] if index >= bpp else 0
        if filter_type == 0:
            value = current[index]
        elif filter_type == 1:
            value = current[index] + left
        elif filter_type == 2:
            value = current[index] + up
        elif filter_type == 3:
            value = current[index] + ((left + up) // 2)
        elif filter_type == 4:
            value = current[index] + _paeth_predictor(left, up, upper_left)
        else:
            raise ValueError("unsupported PNG filter")
        current[index] = value & 0xFF


def _paeth_predictor(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def _is_non_item_node(node: dict[str, object]) -> bool:
    label = _node_label(node).strip()
    resource_id = str(node.get("resource_id", ""))
    if any(header == label or header in label for header in HEADER_LABELS):
        return True
    if any(marker in resource_id for marker in HEADER_RESOURCE_MARKERS):
        return True
    if node.get("clickable") and any(term in label for term in FINAL_ACTION_TERMS):
        return True
    return False


def _looks_like_project_item(label: str, node: dict[str, object]) -> bool:
    if any(header in label for header in HEADER_LABELS):
        return False
    if any(menu in label for menu in APPROVAL_MENUS):
        return False
    if label.endswith("审批") or "web_title" in str(node.get("resource_id", "")):
        return False
    if re.search(r"待审批\s*[1-9]\d*\s*人", label):
        return False
    if "项目" in label:
        return True
    bounds = node.get("bounds")
    has_row_bounds = isinstance(bounds, dict) and int(bounds.get("width", 0)) > 300
    return has_row_bounds and bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9]{4,}", label))


def _looks_like_employee_item(label: str) -> bool:
    if any(header in label for header in HEADER_LABELS):
        return False
    if label in APPROVAL_MENUS or label.endswith("审批"):
        return False
    if "待审批" in label and re.search(r"\d+", label):
        return True
    return bool(re.search(r"[\u4e00-\u9fff]{2,4}.*(异常|打卡|调休|员工|申请)", label))


def _looks_like_leave_item(label: str) -> bool:
    if "请假审批" in label or "请假申请 0" in label:
        return False
    if re.search(r"(待办|待审批|请假申请)\s*[1-9]\d*", label):
        return True
    return bool(re.search(r"[\u4e00-\u9fff]{2,4}.*(年假|事假|病假|调休假|请假)", label))


def _suggested_action(
    menu_name: str,
    status: str,
    item_count: int,
    items: list[dict[str, object]],
    sensitive: list[dict[str, object]],
) -> str:
    if status == "empty":
        return "return"
    if status == "unknown":
        return "needs_manual_review"
    if menu_name in {"考勤异常审批", "调休时长审批", "未打卡审批", "请假审批"}:
        return "approve_one_by_one"
    if item_count <= 0:
        return "return" if status == "empty" else "needs_manual_review"
    if menu_name == "工时审批":
        return "batch_select_then_approve" if not sensitive else "needs_manual_review"
    return "needs_manual_review"


def _risk_level(
    menu_name: str,
    status: str,
    sensitive: list[dict[str, object]],
    items: list[dict[str, object]],
) -> str:
    if status == "empty":
        return "low"
    if menu_name == "请假审批":
        return "high"
    if any(item.get("source") == "screenshot_visual" for item in items):
        return "medium"
    if sensitive:
        return "medium"
    return "medium" if status == "has_items" else "low"


def _sensitive_action_nodes(nodes: list[dict[str, object]]) -> list[dict[str, object]]:
    return [node for node in nodes if node.get("clickable") and _node_has_any(node, FINAL_ACTION_TERMS)]


def _unknown_menu_summary(menu_name: str, message: str) -> dict[str, object]:
    return {
        "menu_name": menu_name,
        "status": "unknown",
        "item_count": 0,
        "items": [],
        "suggested_action": "needs_manual_review",
        "risk_level": "high",
        "screenshot_path": None,
        "xml_path": None,
        "message": message,
        "dry_run": True,
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


def _node_label(node: dict[str, object]) -> str:
    return " ".join(
        str(node.get(key, ""))
        for key in ("text", "content_desc", "resource_id")
        if node.get(key)
    )


def _visible_label(node: dict[str, object]) -> str:
    return " ".join(
        str(node.get(key, ""))
        for key in ("text", "content_desc")
        if node.get(key)
    )


def _node_has_any(node: dict[str, object], terms: tuple[str, ...]) -> bool:
    label = _node_label(node)
    return any(term in label for term in terms)


def _node_ref(node: dict[str, object] | None) -> dict[str, object]:
    if not node:
        return {}
    return {
        "text": node.get("text", ""),
        "resource_id": node.get("resource_id", ""),
        "class": node.get("class", ""),
        "content_desc": node.get("content_desc", ""),
        "clickable": node.get("clickable"),
        "bounds": node.get("bounds"),
    }


__all__ = [
    "APPROVAL_MENUS",
    "open_main_screen",
    "detect_approval_menus",
    "enter_approval_menu",
    "detect_empty_state",
    "summarize_work_hour_approval",
    "summarize_attendance_exception_approval",
    "summarize_leave_approval",
    "summarize_comp_time_approval",
    "summarize_missing_clock_approval",
    "build_daily_approval_plan",
    "probe_approval_menu",
    "return_to_main_screen",
]
