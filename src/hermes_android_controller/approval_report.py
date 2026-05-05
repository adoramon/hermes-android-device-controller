"""Concise WeChat-facing approval plan reports."""

from __future__ import annotations

from collections.abc import Mapping

from .adb_client import AdbClient
from .enterprise_approval_executor import CONFIRM_PHRASE
from .enterprise_approval_probe import build_daily_approval_plan


TABLE_HEADER = "| 审批类型 | 状态 | 数量 | 明细 | 处理方式 |"
TABLE_SEPARATOR = "|---|---:|---:|---|---|"


def build_approval_wechat_report(
    plan: Mapping[str, object] | None = None,
    client: AdbClient | None = None,
) -> dict[str, object]:
    """Build a short Markdown report suitable for WeChat replies.

    The returned payload intentionally omits raw dry-run JSON, XML paths,
    screenshot paths, and internal execution-guard fields.
    """

    source_plan = plan if plan is not None else build_daily_approval_plan(client=client)
    return {
        "ok": bool(source_plan.get("ok", True)),
        "mode": "wechat_approval_report",
        "markdown": format_approval_wechat_report(source_plan),
        "safety": {
            "auto_execute": False,
            "confirmation_required": True,
            "confirmation_phrase": CONFIRM_PHRASE,
        },
    }


def format_approval_wechat_report(plan: Mapping[str, object]) -> str:
    """Format a dry-run approval plan as the compact WeChat Markdown table."""

    rows = [TABLE_HEADER, TABLE_SEPARATOR]
    for menu in plan.get("menus", []):
        if not isinstance(menu, Mapping):
            continue
        rows.append(_format_menu_row(menu))
    rows.extend(["", "如确认执行，请回复：", CONFIRM_PHRASE])
    return "\n".join(rows)


def _format_menu_row(menu: Mapping[str, object]) -> str:
    menu_name = _cell(str(menu.get("menu_name") or "未知审批"))
    status = _cell(_display_status(menu))
    quantity = _cell(_display_quantity(menu))
    detail = _cell(_display_detail(menu))
    handling = _cell(_display_handling(menu))
    return f"| {menu_name} | {status} | {quantity} | {detail} | {handling} |"


def _display_status(menu: Mapping[str, object]) -> str:
    status = str(menu.get("status") or "")
    item_count = _int(menu.get("item_count"))
    if status == "has_items" and item_count > 0:
        return "待处理"
    if status == "empty" or item_count == 0:
        return "无数据"
    return "需人工核对"


def _display_quantity(menu: Mapping[str, object]) -> str:
    menu_name = str(menu.get("menu_name") or "")
    status = str(menu.get("status") or "")
    item_count = _int(menu.get("item_count"))
    if item_count <= 0:
        return "0"
    if status != "has_items":
        return f"{item_count} 条"
    if menu_name == "工时审批":
        project_count = _int(menu.get("project_count")) or item_count
        pending_people_count = _int(menu.get("pending_people_count"))
        if pending_people_count > 0:
            return f"{project_count} 项/{pending_people_count} 人"
        return f"{project_count} 项"
    return f"{item_count} 条"


def _display_detail(menu: Mapping[str, object]) -> str:
    status = str(menu.get("status") or "")
    item_count = _int(menu.get("item_count"))
    if status != "has_items" or item_count <= 0:
        return "暂无数据" if status == "empty" or item_count == 0 else "待人工核对"

    menu_name = str(menu.get("menu_name") or "")
    if menu_name == "工时审批":
        project_count = _int(menu.get("project_count")) or item_count
        pending_people_count = _int(menu.get("pending_people_count"))
        if pending_people_count > 0:
            return f"项目数 {project_count}，待审批 {pending_people_count} 人"
        return f"项目数 {project_count}"

    applicant_detail = _applicant_summary(menu.get("applicant_summary"))
    if applicant_detail:
        return applicant_detail

    labels = _item_labels(menu.get("items"))
    if labels:
        return "，".join(labels)
    return f"{item_count} 条待处理"


def _display_handling(menu: Mapping[str, object]) -> str:
    status = str(menu.get("status") or "")
    item_count = _int(menu.get("item_count"))
    suggested_action = str(menu.get("suggested_action") or "")
    if status == "empty" or item_count == 0:
        return "跳过"
    if status != "has_items" or suggested_action == "needs_manual_review":
        return "人工核对"
    return "确认后执行"


def _applicant_summary(value: object) -> str:
    if not isinstance(value, Mapping) or not value:
        return ""
    normalized = [(str(name), _int(count)) for name, count in value.items() if str(name)]
    if not normalized:
        return ""
    if all(count == 1 for _, count in normalized):
        return "，".join(name for name, _ in normalized)
    return "，".join(f"{name} {count}" for name, count in normalized)


def _item_labels(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    labels = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        label = item.get("applicant") or item.get("name") or item.get("label") or item.get("text")
        if isinstance(label, str) and label.strip():
            labels.append(label.strip())
    return labels


def _cell(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ").strip()


def _int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
