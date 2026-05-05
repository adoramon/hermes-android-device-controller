"""Controlled enterprise approval execution.

Phase 5 requires a fresh dry-run plan and an explicit confirmation phrase
before any approval action is attempted.
"""

from __future__ import annotations

import time
from typing import Iterable

from .adb_client import AdbClient, get_default_client
from .app_probe import ENTERPRISE_APP_PACKAGE, parse_ui_xml, probe_current_screen
from .device_status import device_status
from .enterprise_approval_probe import (
    APPROVAL_MENUS,
    build_daily_approval_plan,
    enter_approval_menu,
    return_to_main_screen,
)


CONFIRM_PHRASE = "确认审批"
VALIDATION_CONFIRM_PHRASE = "确认执行审批前验证"
SKIPPED_ACTIONS = {"needs_manual_review"}
SENSITIVE_ACTION_TERMS = ("确认", "提交", "通过", "同意", "批准", "审批")
SAFE_EXECUTION_ACTIONS = {"batch_select_then_approve", "approve_one_by_one"}
BATCH_EMPLOYEE_MENUS = ("考勤异常审批", "调休时长审批", "未打卡审批")


def execute_daily_approval_plan(confirm_text: str, client: AdbClient | None = None) -> dict[str, object]:
    """Execute a controlled approval plan only after exact confirmation."""

    if confirm_text != CONFIRM_PHRASE:
        return _refused_result("Confirmation phrase mismatch.")

    adb = client or get_default_client()
    plan = build_daily_approval_plan(client=adb)
    results = []
    for menu in plan.get("menus", []):
        if not isinstance(menu, dict):
            continue
        menu_name = str(menu.get("menu_name", ""))
        decision = _execution_decision(menu)
        if not decision["execute"]:
            results.append(
                {
                    "menu_name": menu_name,
                    "executed": False,
                    "status": "skipped",
                    "reason": decision["reason"],
                    "plan_status": menu.get("status"),
                    "risk_level": menu.get("risk_level"),
                    "suggested_action": menu.get("suggested_action"),
                }
            )
            continue
        results.append(_execute_menu_by_name(menu_name, client=adb, confirmed=True))
    return {
        "ok": all(bool(result.get("ok", True)) for result in results),
        "mode": "controlled_execution",
        "confirmed": True,
        "dry_run_plan": plan,
        "results": results,
        "safety": {
            "confirmation_required": True,
            "confirmation_phrase": CONFIRM_PHRASE,
            "bypass_controls": False,
            "root_or_hook": False,
        },
    }


def validate_daily_approval_confirmation_flow(
    confirm_text: str,
    client: AdbClient | None = None,
) -> dict[str, object]:
    """Open pre-final approval dialogs, inspect them, and never click final confirm."""

    if confirm_text != VALIDATION_CONFIRM_PHRASE:
        return {
            "ok": False,
            "executed": False,
            "status": "refused",
            "message": "Pre-final validation confirmation phrase mismatch.",
            "required_confirm_text": VALIDATION_CONFIRM_PHRASE,
        }

    adb = client or get_default_client()
    plan = build_daily_approval_plan(client=adb)
    results = []
    for menu in plan.get("menus", []):
        if not isinstance(menu, dict):
            continue
        decision = _execution_decision(menu)
        if not decision["execute"]:
            results.append(
                {
                    "menu_name": menu.get("menu_name"),
                    "validated": False,
                    "status": "skipped",
                    "reason": decision["reason"],
                    "plan_status": menu.get("status"),
                    "risk_level": menu.get("risk_level"),
                    "item_count": menu.get("item_count"),
                }
            )
            continue
        results.append(_validate_menu_confirmation_flow(menu, client=adb))
    return {
        "ok": all(result.get("status") in {"validated", "skipped"} for result in results),
        "mode": "pre_final_confirmation_validation",
        "dry_run_plan": plan,
        "results": results,
        "safety": {
            "selected_items": True,
            "approval_button_clicked": True,
            "final_confirmation_clicked": False,
            "final_confirm_button_only_detected": True,
            "bypass_controls": False,
            "root_or_hook": False,
        },
    }


def execute_work_hour_approval(
    client: AdbClient | None = None,
    *,
    confirmed: bool = False,
) -> dict[str, object]:
    if not confirmed:
        return _refused_result("Work-hour approval requires confirmed daily execution.")
    adb = client or get_default_client()
    enter = enter_approval_menu("工时审批", client=adb)
    if not enter.get("ok"):
        return _execution_error("工时审批", "Failed to enter menu.", enter)
    logs = []
    page = _capture_nodes(adb)
    if not page["ok"]:
        return _execution_error("工时审批", "Failed to capture menu page.", page)
    project_choice = _find_first_choice_left_of_terms(page["nodes"], ("项目", "待审批"))
    if not project_choice:
        return _needs_manual_review("工时审批", "Project selection control was not found.", page)
    logs.append(_click_node(adb, project_choice, clicked_text="project_choice", sensitive_action=False))
    approve_button = _find_clickable_action(_current_nodes(adb), ("审批",))
    if not approve_button:
        return _needs_manual_review("工时审批", "Approval button was not found after project selection.", page, logs)
    logs.append(_click_node(adb, approve_button, clicked_text=_node_label(approve_button), sensitive_action=True))
    confirm = _click_first_confirmation(adb, logs)
    return _execution_result("工时审批", logs, confirm)


def execute_batch_employee_approval(
    menu_name: str,
    client: AdbClient | None = None,
    *,
    confirmed: bool = False,
) -> dict[str, object]:
    if not confirmed:
        return _refused_result(f"{menu_name} requires confirmed daily execution.")
    if menu_name not in BATCH_EMPLOYEE_MENUS:
        return _execution_error(menu_name, "Menu is not supported by batch employee approval.", {})
    adb = client or get_default_client()
    enter = enter_approval_menu(menu_name, client=adb)
    if not enter.get("ok"):
        return _execution_error(menu_name, "Failed to enter menu.", enter)
    logs = []
    page = _capture_nodes(adb)
    if not page["ok"]:
        return _execution_error(menu_name, "Failed to capture menu page.", page)
    employee_choice = _find_first_choice_left_of_terms(page["nodes"], ("我管理的员工", "员工"))
    if not employee_choice:
        employee_choice = _webview_batch_control(menu_name, page, "employee_choice")
    if not employee_choice:
        return _needs_manual_review(menu_name, "Employee selection control was not found.", page)
    logs.append(_click_node(adb, employee_choice, clicked_text="employee_choice", sensitive_action=False))
    approve_button = _find_clickable_action(_current_nodes(adb), ("审批",))
    if not approve_button:
        approve_button = _webview_batch_control(menu_name, _capture_nodes(adb), "approve_button")
    if not approve_button:
        return _needs_manual_review(menu_name, "Approval button was not found after employee selection.", page, logs)
    logs.append(_click_node(adb, approve_button, clicked_text=_node_label(approve_button), sensitive_action=True))
    confirm = _click_first_confirmation(adb, logs)
    return _execution_result(menu_name, logs, confirm)


def execute_leave_approval(
    client: AdbClient | None = None,
    *,
    confirmed: bool = False,
) -> dict[str, object]:
    if not confirmed:
        return _refused_result("Leave approval requires confirmed daily execution.")
    adb = client or get_default_client()
    enter = enter_approval_menu("请假审批", client=adb)
    if not enter.get("ok"):
        return _execution_error("请假审批", "Failed to enter menu.", enter)
    logs = []
    page = _capture_nodes(adb)
    if not page["ok"]:
        return _execution_error("请假审批", "Failed to capture menu page.", page)
    if _has_ambiguous_leave_fields(page["nodes"]):
        return _needs_manual_review("请假审批", "Ambiguous leave fields or remarks were detected.", page)
    action = _find_clickable_action(page["nodes"], ("同意", "通过", "批准", "审批"))
    if not action:
        return _needs_manual_review("请假审批", "No explicit leave approval action was found.", page)
    logs.append(_click_node(adb, action, clicked_text=_node_label(action), sensitive_action=True))
    confirm = _click_first_confirmation(adb, logs)
    return _execution_result("请假审批", logs, confirm)


def execute_attendance_exception_approval(confirm_text: str = "", client: AdbClient | None = None) -> dict[str, object]:
    if confirm_text != CONFIRM_PHRASE:
        return _refused_result("Confirmation phrase mismatch.")
    return execute_batch_employee_approval("考勤异常审批", client=client, confirmed=True)


def execute_comp_time_approval(confirm_text: str = "", client: AdbClient | None = None) -> dict[str, object]:
    if confirm_text != CONFIRM_PHRASE:
        return _refused_result("Confirmation phrase mismatch.")
    return execute_batch_employee_approval("调休时长审批", client=client, confirmed=True)


def execute_missing_clock_approval(confirm_text: str = "", client: AdbClient | None = None) -> dict[str, object]:
    if confirm_text != CONFIRM_PHRASE:
        return _refused_result("Confirmation phrase mismatch.")
    return execute_batch_employee_approval("未打卡审批", client=client, confirmed=True)


def execute_work_hour_approval_confirmed(confirm_text: str = "", client: AdbClient | None = None) -> dict[str, object]:
    if confirm_text != CONFIRM_PHRASE:
        return _refused_result("Confirmation phrase mismatch.")
    return execute_work_hour_approval(client=client, confirmed=True)


def execute_leave_approval_confirmed(confirm_text: str = "", client: AdbClient | None = None) -> dict[str, object]:
    if confirm_text != CONFIRM_PHRASE:
        return _refused_result("Confirmation phrase mismatch.")
    return execute_leave_approval(client=client, confirmed=True)


def _execution_decision(menu: dict[str, object]) -> dict[str, object]:
    if int(menu.get("item_count") or 0) <= 0:
        return {"execute": False, "reason": "item_count=0"}
    if menu.get("status") != "has_items":
        return {"execute": False, "reason": f"status={menu.get('status')}"}
    if menu.get("risk_level") == "high":
        return {"execute": False, "reason": "risk_level=high"}
    if menu.get("suggested_action") in SKIPPED_ACTIONS:
        return {"execute": False, "reason": f"suggested_action={menu.get('suggested_action')}"}
    if menu.get("suggested_action") not in SAFE_EXECUTION_ACTIONS:
        return {"execute": False, "reason": f"unsupported suggested_action={menu.get('suggested_action')}"}
    return {"execute": True, "reason": "eligible"}


def _execute_menu_by_name(menu_name: str, client: AdbClient, confirmed: bool) -> dict[str, object]:
    if menu_name == "工时审批":
        return execute_work_hour_approval(client=client, confirmed=confirmed)
    if menu_name == "请假审批":
        return execute_leave_approval(client=client, confirmed=confirmed)
    if menu_name in BATCH_EMPLOYEE_MENUS:
        return execute_batch_employee_approval(menu_name, client=client, confirmed=confirmed)
    return _execution_error(menu_name, "Unsupported menu.", {})


def _validate_menu_confirmation_flow(menu: dict[str, object], client: AdbClient) -> dict[str, object]:
    menu_name = str(menu.get("menu_name", ""))
    enter = enter_approval_menu(menu_name, client=client)
    if not enter.get("ok"):
        return _validation_error(menu_name, "Failed to enter menu.", enter)

    logs: list[dict[str, object]] = []
    page = _capture_nodes(client)
    if not page.get("ok"):
        return _validation_error(menu_name, "Failed to capture menu page.", page, logs)

    selection = _validation_selection_control(menu_name, menu, page)
    if not selection:
        return _validation_manual_review(menu_name, "Selection control was not found.", page, logs, client)
    logs.append(_click_node(client, selection, clicked_text=str(selection.get("text") or "selection"), sensitive_action=False))

    if menu_name == "工时审批":
        time.sleep(1)
        page = _capture_nodes(client)
        if not page.get("ok"):
            return _validation_error(menu_name, "Failed to capture work-hour detail page.", page, logs)
        detail_selection = _validation_work_hour_detail_selection(menu, page)
        if detail_selection:
            logs.append(
                _click_node(
                    client,
                    detail_selection,
                    clicked_text=str(detail_selection.get("text") or "work_hour_detail_selection"),
                    sensitive_action=False,
                )
            )

    approve_page = _capture_nodes(client)
    approve_button = _find_clickable_action(approve_page.get("nodes", []), ("审批",))
    if not approve_button:
        approve_button = _webview_batch_control(menu_name, approve_page, "approve_button")
    if not approve_button:
        approve_button = _webview_top_right_approve_control(approve_page)
    if not approve_button:
        return _validation_manual_review(
            menu_name, "Approval button was not found after selection.", approve_page, logs, client
        )

    logs.append(_click_node(client, approve_button, clicked_text=_node_label(approve_button), sensitive_action=True))
    time.sleep(1)
    dialog = _capture_nodes(client)
    inspection = _inspect_confirmation_surface(dialog)
    cleanup = _cleanup_after_validation(client, menu_name)
    return {
        "ok": bool(inspection.get("has_final_confirmation_candidate")),
        "menu_name": menu_name,
        "validated": bool(inspection.get("has_final_confirmation_candidate")),
        "status": "validated" if inspection.get("has_final_confirmation_candidate") else "needs_manual_review",
        "message": "Final confirmation surface detected; final confirmation was not clicked."
        if inspection.get("has_final_confirmation_candidate")
        else "Approval dialog did not expose a final confirmation candidate.",
        "click_logs": logs,
        "dialog_probe": {
            "xml_path": dialog.get("xml_path"),
            "screenshot_path": dialog.get("screenshot_path"),
            "current_foreground_package": dialog.get("current_foreground_package"),
        },
        "confirmation_surface": inspection,
        "cleanup": cleanup,
        "safety": {
            "final_confirmation_clicked": False,
        },
    }


def _validation_selection_control(
    menu_name: str,
    menu: dict[str, object],
    page: dict[str, object],
) -> dict[str, object] | None:
    nodes = page.get("nodes", [])
    if not isinstance(nodes, list):
        nodes = []
    if menu_name == "工时审批":
        project_items = menu.get("project_items") or menu.get("items") or []
        if isinstance(project_items, list) and project_items:
            first = project_items[0]
            if isinstance(first, dict) and isinstance(first.get("bounds"), dict):
                return {"text": "work_hour_project", "class": "android.view.View", "clickable": True, "bounds": first["bounds"]}
        return _find_first_choice_left_of_terms(nodes, ("项目", "待审批"))
    if menu_name in BATCH_EMPLOYEE_MENUS:
        return _find_first_choice_left_of_terms(nodes, ("我管理的员工", "员工")) or _webview_batch_control(
            menu_name, page, "employee_choice"
        )
    return _find_first_choice_left_of_terms(nodes, ("待办", "请假", "申请"))


def _validation_work_hour_detail_selection(menu: dict[str, object], page: dict[str, object]) -> dict[str, object] | None:
    select_all = _work_hour_detail_select_all_control(page)
    if select_all:
        return select_all
    nodes = page.get("nodes", [])
    if isinstance(nodes, list):
        selector = _find_first_choice_left_of_terms(nodes, ("待审批", "工时", "人员", "员工"))
        if selector:
            return selector
    detail_probe = menu.get("project_detail_probe")
    if isinstance(detail_probe, dict):
        rows = detail_probe.get("visual_rows")
        if isinstance(rows, list) and rows:
            first = rows[0]
            if isinstance(first, dict) and isinstance(first.get("center_y"), int):
                return {
                    "text": "work_hour_first_person_choice",
                    "class": "android.view.View",
                    "clickable": True,
                    "bounds": _centered_bounds(48, int(first["center_y"]), 96, 96),
                }
    return None


def _work_hour_detail_select_all_control(page: dict[str, object]) -> dict[str, object] | None:
    nodes = page.get("nodes", [])
    if not isinstance(nodes, list):
        return None
    title_node = None
    for node in nodes:
        label = _node_label(node)
        bounds = node.get("bounds")
        if (
            isinstance(bounds, dict)
            and "项目" in label
            and bounds.get("top", 99999) < 430
            and bounds.get("center_y", 0) > 250
        ):
            title_node = node
            break
    if not title_node:
        for node in nodes:
            label = _node_label(node)
            bounds = node.get("bounds")
            if isinstance(bounds, dict) and label.strip() == "审批" and bounds.get("top", 99999) < 430:
                title_node = node
                break
    if not title_node:
        return None
    bounds = title_node.get("bounds")
    if not isinstance(bounds, dict) or not isinstance(bounds.get("center_y"), int):
        return None
    screen_width = int(_screen_bounds(nodes).get("right", 1080))
    return {
        "text": "work_hour_select_all",
        "class": "android.view.View",
        "clickable": True,
        "bounds": _centered_bounds(max(48, int(screen_width * 0.064)), int(bounds["center_y"]), 96, 96),
    }


def _webview_top_right_approve_control(page: dict[str, object]) -> dict[str, object] | None:
    nodes = page.get("nodes", [])
    if not isinstance(nodes, list) or not any("WebView" in str(node.get("class", "")) for node in nodes):
        return None
    width = _screen_bounds(nodes).get("right", 1080)
    return {
        "text": "webview_审批",
        "class": "android.widget.Button",
        "clickable": True,
        "bounds": _centered_bounds(int(width * 0.853), 327, 190, 96),
    }


def _inspect_confirmation_surface(page: dict[str, object]) -> dict[str, object]:
    nodes = page.get("nodes", [])
    if not isinstance(nodes, list):
        nodes = []
    pass_options = [_node_ref(node) for node in nodes if any(term in _node_label(node) for term in ("通过", "同意", "批准"))]
    reject_options = [_node_ref(node) for node in nodes if any(term in _node_label(node) for term in ("不通过", "驳回", "拒绝"))]
    final_candidates = [
        _node_ref(node)
        for node in nodes
        if _has_bounds(node) and any(term in _node_label(node) for term in ("确认", "提交", "确定"))
    ]
    cancel_candidates = [
        _node_ref(node)
        for node in nodes
        if _has_bounds(node) and any(term in _node_label(node) for term in ("取消", "返回", "关闭"))
    ]
    return {
        "ok": bool(page.get("ok")),
        "has_pass_option": bool(pass_options),
        "has_reject_option": bool(reject_options),
        "has_final_confirmation_candidate": bool(final_candidates),
        "pass_options": pass_options,
        "reject_options": reject_options,
        "final_confirmation_candidates": final_candidates,
        "cancel_candidates": cancel_candidates,
        "final_confirmation_clicked": False,
    }


def _cleanup_after_validation(client: AdbClient, menu_name: str) -> list[dict[str, object]]:
    logs = []
    for reason in ("dismiss_confirmation_surface", "return_to_menu_home"):
        result = return_to_main_screen(client=client)
        logs.append({"reason": reason, "result": result})
        time.sleep(1)
    if menu_name == "工时审批":
        result = return_to_main_screen(client=client)
        logs.append({"reason": "return_from_work_hour_project", "result": result})
        time.sleep(1)
    return logs


def _validation_manual_review(
    menu_name: str,
    message: str,
    page: dict[str, object],
    logs: list[dict[str, object]],
    client: AdbClient,
) -> dict[str, object]:
    cleanup = _cleanup_after_validation(client, menu_name)
    return {
        "ok": False,
        "menu_name": menu_name,
        "validated": False,
        "status": "needs_manual_review",
        "message": message,
        "xml_path": page.get("xml_path"),
        "screenshot_path": page.get("screenshot_path"),
        "click_logs": logs,
        "cleanup": cleanup,
        "safety": {"final_confirmation_clicked": False},
    }


def _validation_error(
    menu_name: str,
    message: str,
    details: dict[str, object],
    logs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "ok": False,
        "menu_name": menu_name,
        "validated": False,
        "status": "failed",
        "message": message,
        "details": details,
        "click_logs": logs or [],
        "safety": {"final_confirmation_clicked": False},
    }


def _capture_nodes(adb: AdbClient, attempts: int = 3) -> dict[str, object]:
    status = device_status(client=adb)
    if status.get("foreground_package") != ENTERPRISE_APP_PACKAGE:
        return {
            "ok": False,
            "nodes": [],
            "current_foreground_package": status.get("foreground_package"),
            "last_xml_path": None,
            "last_screenshot_path": None,
            "adb": {
                "reason": "unexpected_foreground_package",
                "status_message": status.get("message"),
            },
        }

    logs = []
    last_probe: dict[str, object] | None = None
    for attempt in range(1, attempts + 1):
        if attempt > 1:
            time.sleep(1)
        probe = probe_current_screen(client=adb)
        last_probe = probe
        logs.append(_capture_attempt_log(attempt, probe))
        xml_path = probe.get("xml_path")
        if probe.get("ok") and isinstance(xml_path, str):
            return {
                "ok": True,
                "probe": probe,
                "nodes": parse_ui_xml(xml_path),
                "xml_path": xml_path,
                "screenshot_path": probe.get("screenshot_path"),
                "current_foreground_package": status.get("foreground_package"),
                "retry_logs": logs,
            }

    fallback = last_probe or {}
    return {
        "ok": False,
        "probe": fallback,
        "nodes": [],
        "current_foreground_package": status.get("foreground_package"),
        "last_xml_path": fallback.get("xml_path"),
        "last_screenshot_path": fallback.get("screenshot_path"),
        "adb": {
            "reason": "capture_failed_after_retries",
            "retry_logs": logs,
        },
    }


def _capture_attempt_log(attempt: int, probe: dict[str, object]) -> dict[str, object]:
    return {
        "attempt": attempt,
        "ok": probe.get("ok"),
        "xml_path": probe.get("xml_path"),
        "screenshot_path": probe.get("screenshot_path"),
        "xml_dump": _command_summary((probe.get("xml") or {}).get("dump"))
        if isinstance(probe.get("xml"), dict)
        else None,
        "xml_pull": _command_summary((probe.get("xml") or {}).get("pull"))
        if isinstance(probe.get("xml"), dict)
        else None,
        "screenshot_capture": _command_summary((probe.get("screenshot") or {}).get("capture"))
        if isinstance(probe.get("screenshot"), dict)
        else None,
        "screenshot_pull": _command_summary((probe.get("screenshot") or {}).get("pull"))
        if isinstance(probe.get("screenshot"), dict)
        else None,
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


def _current_nodes(adb: AdbClient) -> list[dict[str, object]]:
    page = _capture_nodes(adb)
    return page["nodes"] if page.get("ok") else []


def _click_node(
    adb: AdbClient,
    node: dict[str, object],
    *,
    clicked_text: str,
    sensitive_action: bool,
) -> dict[str, object]:
    before = _capture_nodes(adb)
    bounds = node.get("bounds") if isinstance(node, dict) else None
    clicked = False
    if isinstance(bounds, dict) and isinstance(bounds.get("center_x"), int) and isinstance(bounds.get("center_y"), int):
        clicked = adb.shell(["input", "tap", str(bounds["center_x"]), str(bounds["center_y"])]).ok
    time.sleep(1)
    after = _capture_nodes(adb)
    return {
        "clicked": clicked,
        "clicked_text": clicked_text,
        "clicked_bounds": bounds,
        "sensitive_action": sensitive_action,
        "before_xml_path": before.get("xml_path"),
        "before_screenshot_path": before.get("screenshot_path"),
        "after_xml_path": after.get("xml_path"),
        "after_screenshot_path": after.get("screenshot_path"),
    }


def _click_first_confirmation(adb: AdbClient, logs: list[dict[str, object]]) -> dict[str, object]:
    failures = 0
    for _ in range(2):
        nodes = _current_nodes(adb)
        confirm = _find_clickable_action(nodes, ("确认", "提交", "通过", "同意", "批准"))
        if not confirm:
            failures += 1
            if failures >= 2:
                return {
                    "ok": False,
                    "needs_manual_review": True,
                    "message": "Confirmation action not found twice.",
                }
            time.sleep(1)
            continue
        log = _click_node(adb, confirm, clicked_text=_node_label(confirm), sensitive_action=True)
        logs.append(log)
        return {
            "ok": bool(log.get("clicked")),
            "needs_manual_review": not bool(log.get("clicked")),
            "message": "Confirmation action clicked." if log.get("clicked") else "Confirmation click failed.",
            "log": log,
        }
    return {
        "ok": False,
        "needs_manual_review": True,
        "message": "Confirmation action was not completed.",
    }


def _find_clickable_action(nodes: Iterable[dict[str, object]], terms: tuple[str, ...]) -> dict[str, object] | None:
    for node in nodes:
        if node.get("clickable") and any(term in _node_label(node) for term in terms):
            return node
    return None


def _find_first_choice_left_of_terms(
    nodes: list[dict[str, object]],
    terms: tuple[str, ...],
) -> dict[str, object] | None:
    labeled = [node for node in nodes if any(term in _node_label(node) for term in terms)]
    candidates = [node for node in nodes if node.get("clickable") and _looks_like_selector(node)]
    for label_node in labeled:
        label_bounds = label_node.get("bounds")
        if not isinstance(label_bounds, dict):
            continue
        for candidate in candidates:
            bounds = candidate.get("bounds")
            if not isinstance(bounds, dict):
                continue
            if bounds.get("center_x", 99999) < label_bounds.get("center_x", 0):
                return candidate
    return candidates[0] if candidates else None


def _webview_batch_control(menu_name: str, page: dict[str, object], control: str) -> dict[str, object] | None:
    if menu_name not in BATCH_EMPLOYEE_MENUS:
        return None
    nodes = page.get("nodes", [])
    if not isinstance(nodes, list) or not _is_hidden_webview_batch_page(nodes):
        return None
    screen_bounds = _screen_bounds(nodes)
    width = screen_bounds.get("right", 1080)
    if control == "employee_choice":
        bounds = _centered_bounds(int(width * 0.045), 327, 96, 96)
        return {"text": "webview_employee_choice", "class": "android.view.View", "clickable": True, "bounds": bounds}
    if control == "approve_button":
        bounds = _centered_bounds(int(width * 0.853), 327, 190, 96)
        return {"text": "webview_审批", "class": "android.widget.Button", "clickable": True, "bounds": bounds}
    return None


def _is_hidden_webview_batch_page(nodes: list[dict[str, object]]) -> bool:
    has_webview = any("WebView" in str(node.get("class", "")) for node in nodes)
    title = ""
    for node in nodes:
        if "web_title" in str(node.get("resource_id", "")):
            title = str(node.get("text") or node.get("content_desc") or "")
            break
    return has_webview and title in {"考勤审批", "调休时长确认", "未打卡申请审批"}


def _screen_bounds(nodes: list[dict[str, object]]) -> dict[str, int]:
    for node in nodes:
        bounds = node.get("bounds")
        if isinstance(bounds, dict) and bounds.get("left") == 0 and bounds.get("top") == 0:
            return {
                "left": int(bounds.get("left", 0)),
                "top": int(bounds.get("top", 0)),
                "right": int(bounds.get("right", 1080)),
                "bottom": int(bounds.get("bottom", 2400)),
            }
    return {"left": 0, "top": 0, "right": 1080, "bottom": 2400}


def _centered_bounds(center_x: int, center_y: int, width: int, height: int) -> dict[str, int]:
    left = center_x - width // 2
    top = center_y - height // 2
    return {
        "left": left,
        "top": top,
        "right": left + width,
        "bottom": top + height,
        "width": width,
        "height": height,
        "center_x": center_x,
        "center_y": center_y,
    }


def _looks_like_selector(node: dict[str, object]) -> bool:
    class_name = str(node.get("class", ""))
    text = _node_label(node)
    return "CheckBox" in class_name or "RadioButton" in class_name or text.strip() in {"□", "☐", "", ""}


def _has_ambiguous_leave_fields(nodes: list[dict[str, object]]) -> bool:
    labels = " ".join(_node_label(node) for node in nodes)
    return any(term in labels for term in ("备注必填", "原因不明", "异常", "附件缺失", "需人工确认"))


def _execution_result(menu_name: str, logs: list[dict[str, object]], confirm: dict[str, object]) -> dict[str, object]:
    ok = bool(confirm.get("ok"))
    return {
        "ok": ok,
        "menu_name": menu_name,
        "executed": ok,
        "status": "completed" if ok else "needs_manual_review",
        "needs_manual_review": bool(confirm.get("needs_manual_review", not ok)),
        "click_logs": logs,
        "confirmation": confirm,
    }


def _needs_manual_review(
    menu_name: str,
    message: str,
    page: dict[str, object],
    logs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "ok": False,
        "menu_name": menu_name,
        "executed": False,
        "status": "needs_manual_review",
        "needs_manual_review": True,
        "message": message,
        "xml_path": page.get("xml_path"),
        "screenshot_path": page.get("screenshot_path"),
        "click_logs": logs or [],
    }


def _execution_error(menu_name: str, message: str, details: dict[str, object]) -> dict[str, object]:
    result = {
        "ok": False,
        "menu_name": menu_name,
        "executed": False,
        "status": "failed",
        "message": message,
        "details": details,
    }
    if isinstance(details, dict):
        result.update(
            {
                "current_foreground_package": details.get("current_foreground_package"),
                "last_screenshot_path": details.get("last_screenshot_path") or details.get("screenshot_path"),
                "last_xml_path": details.get("last_xml_path") or details.get("xml_path"),
                "adb": details.get("adb"),
            }
        )
    return result


def _refused_result(message: str) -> dict[str, object]:
    return {
        "ok": False,
        "executed": False,
        "status": "refused",
        "message": message,
        "required_confirm_text": CONFIRM_PHRASE,
    }


def _node_label(node: dict[str, object]) -> str:
    return " ".join(
        str(node.get(key, ""))
        for key in ("text", "content_desc", "resource_id")
        if node.get(key)
    )


def _node_ref(node: dict[str, object]) -> dict[str, object]:
    return {
        "text": node.get("text", ""),
        "resource_id": node.get("resource_id", ""),
        "class": node.get("class", ""),
        "content_desc": node.get("content_desc", ""),
        "clickable": bool(node.get("clickable")),
        "bounds": node.get("bounds"),
    }


def _has_bounds(node: dict[str, object]) -> bool:
    bounds = node.get("bounds")
    return isinstance(bounds, dict) and isinstance(bounds.get("center_x"), int) and isinstance(bounds.get("center_y"), int)


__all__ = [
    "CONFIRM_PHRASE",
    "VALIDATION_CONFIRM_PHRASE",
    "execute_daily_approval_plan",
    "validate_daily_approval_confirmation_flow",
    "execute_work_hour_approval",
    "execute_batch_employee_approval",
    "execute_leave_approval",
    "execute_attendance_exception_approval",
    "execute_comp_time_approval",
    "execute_missing_clock_approval",
    "execute_work_hour_approval_confirmed",
    "execute_leave_approval_confirmed",
]
