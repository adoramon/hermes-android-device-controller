"""Public tool surface for Hermes skill integration."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .app_probe import (
    open_enterprise_app,
    parse_ui_xml,
    probe_current_screen,
    summarize_screen,
)
from .approval_report import build_approval_wechat_report
from .daily_approval_scheduler import run_daily_scan, run_once_if_due
from .device_status import device_status
from .enterprise_auth import (
    detect_sms_code_screen,
    handle_wechat_sms_code_message,
    login_with_credentials,
    submit_sms_code,
)
from .enterprise_approval_probe import (
    build_daily_approval_plan,
    detect_approval_menus,
    enter_approval_menu,
    probe_approval_menu,
)
from .enterprise_approval_executor import (
    execute_attendance_exception_approval,
    execute_comp_time_approval,
    execute_daily_approval_plan,
    execute_leave_approval_confirmed,
    execute_missing_clock_approval,
    execute_work_hour_approval_confirmed,
    validate_daily_approval_confirmation_flow,
)
from .ghostmapx import (
    apply_ghostmapx_location,
    geocode_address,
    open_ghostmapx,
    prepare_ghostmapx_location,
    probe_ghostmapx_screen,
)
from .input_actions import input_text, keyevent, open_app, swipe, tap
from .screen_reader import dump_screen_xml, take_screenshot


def android_device_status() -> dict[str, object]:
    return device_status()


def android_open_app(package_name: str):
    return open_app(package_name)


def android_input_tap(x: int, y: int):
    return tap(x, y)


def android_input_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
    return swipe(x1, y1, x2, y2, duration_ms)


def android_input_text(text: str):
    return input_text(text)


def android_keyevent(code: int):
    return keyevent(code)


def android_dump_screen_xml() -> dict[str, object]:
    return dump_screen_xml()


def android_take_screenshot() -> dict[str, object]:
    return take_screenshot()


def android_open_enterprise_app():
    return open_enterprise_app()


def android_probe_current_screen() -> dict[str, object]:
    return probe_current_screen()


def android_parse_current_ui() -> dict[str, object]:
    probe = probe_current_screen()
    xml_path = probe.get("xml_path")
    nodes = []
    parse_error = None
    if xml_path:
        try:
            nodes = parse_ui_xml(str(xml_path))
        except (ET.ParseError, OSError) as exc:
            parse_error = str(exc)
    return {
        "ok": bool(probe.get("ok")) and parse_error is None,
        "foreground_package": probe.get("foreground_package"),
        "xml_path": xml_path,
        "screenshot_path": probe.get("screenshot_path"),
        "nodes": nodes,
        "parse_error": parse_error,
        "probe": probe,
    }


def android_summarize_current_screen() -> dict[str, object]:
    return summarize_screen()


def android_enterprise_login() -> dict[str, object]:
    return login_with_credentials()


def android_enterprise_detect_sms_code() -> dict[str, object]:
    return detect_sms_code_screen()


def android_enterprise_submit_sms_code(code: str) -> dict[str, object]:
    return submit_sms_code(code)


def android_enterprise_handle_wechat_sms_code(text: str) -> dict[str, object]:
    return handle_wechat_sms_code_message(text)


def android_detect_approval_menus() -> dict[str, object]:
    return detect_approval_menus()


def android_build_daily_approval_plan() -> dict[str, object]:
    return build_daily_approval_plan()


def android_build_approval_wechat_report() -> dict[str, object]:
    return build_approval_wechat_report()


def android_probe_approval_menu(menu_name: str) -> dict[str, object]:
    return probe_approval_menu(menu_name)


def android_execute_daily_approval_plan(confirm_text: str) -> dict[str, object]:
    return execute_daily_approval_plan(confirm_text)


def android_execute_work_hour_approval(confirm_text: str = "") -> dict[str, object]:
    return execute_work_hour_approval_confirmed(confirm_text)


def android_execute_attendance_exception_approval(confirm_text: str = "") -> dict[str, object]:
    return execute_attendance_exception_approval(confirm_text)


def android_execute_leave_approval(confirm_text: str = "") -> dict[str, object]:
    return execute_leave_approval_confirmed(confirm_text)


def android_execute_comp_time_approval(confirm_text: str = "") -> dict[str, object]:
    return execute_comp_time_approval(confirm_text)


def android_execute_missing_clock_approval(confirm_text: str = "") -> dict[str, object]:
    return execute_missing_clock_approval(confirm_text)


def android_validate_approval_confirmation_flow(confirm_text: str = "") -> dict[str, object]:
    return validate_daily_approval_confirmation_flow(confirm_text)


def android_run_daily_approval_scan_once() -> dict[str, object]:
    return run_once_if_due()


def android_force_daily_approval_scan() -> dict[str, object]:
    return run_daily_scan()


def android_ghostmapx_geocode(
    address: str,
    provider: str = "auto",
    random_radius_meters: float = 50,
) -> dict[str, object]:
    return geocode_address(address, provider=provider, random_radius_meters=random_radius_meters)


def android_open_ghostmapx() -> dict[str, object]:
    return open_ghostmapx()


def android_probe_ghostmapx() -> dict[str, object]:
    return probe_ghostmapx_screen()


def android_prepare_ghostmapx_location(
    address: str,
    provider: str = "auto",
    random_radius_meters: float = 50,
) -> dict[str, object]:
    return prepare_ghostmapx_location(
        address,
        provider=provider,
        random_radius_meters=random_radius_meters,
    )


def android_apply_ghostmapx_location(
    address: str,
    provider: str = "auto",
    confirm_text: str = "",
    random_radius_meters: float = 50,
) -> dict[str, object]:
    return apply_ghostmapx_location(
        address,
        provider=provider,
        confirm_text=confirm_text,
        random_radius_meters=random_radius_meters,
    )


__all__ = [
    "android_device_status",
    "android_open_app",
    "android_input_tap",
    "android_input_swipe",
    "android_input_text",
    "android_keyevent",
    "android_dump_screen_xml",
    "android_take_screenshot",
    "android_open_enterprise_app",
    "android_probe_current_screen",
    "android_parse_current_ui",
    "android_summarize_current_screen",
    "android_enterprise_login",
    "android_enterprise_detect_sms_code",
    "android_enterprise_submit_sms_code",
    "android_enterprise_handle_wechat_sms_code",
    "android_detect_approval_menus",
    "android_build_daily_approval_plan",
    "android_build_approval_wechat_report",
    "android_probe_approval_menu",
    "android_execute_daily_approval_plan",
    "android_execute_work_hour_approval",
    "android_execute_attendance_exception_approval",
    "android_execute_leave_approval",
    "android_execute_comp_time_approval",
    "android_execute_missing_clock_approval",
    "android_validate_approval_confirmation_flow",
    "android_run_daily_approval_scan_once",
    "android_force_daily_approval_scan",
    "android_ghostmapx_geocode",
    "android_open_ghostmapx",
    "android_probe_ghostmapx",
    "android_prepare_ghostmapx_location",
    "android_apply_ghostmapx_location",
    "device_status",
    "open_app",
    "tap",
    "swipe",
    "input_text",
    "keyevent",
    "dump_screen_xml",
    "take_screenshot",
    "open_enterprise_app",
    "probe_current_screen",
    "parse_ui_xml",
    "summarize_screen",
    "login_with_credentials",
    "detect_sms_code_screen",
    "submit_sms_code",
    "handle_wechat_sms_code_message",
    "detect_approval_menus",
    "build_daily_approval_plan",
    "build_approval_wechat_report",
    "enter_approval_menu",
    "probe_approval_menu",
    "execute_daily_approval_plan",
    "execute_work_hour_approval_confirmed",
    "execute_attendance_exception_approval",
    "execute_leave_approval_confirmed",
    "execute_comp_time_approval",
    "execute_missing_clock_approval",
    "validate_daily_approval_confirmation_flow",
    "run_once_if_due",
    "run_daily_scan",
    "geocode_address",
    "open_ghostmapx",
    "probe_ghostmapx_screen",
    "prepare_ghostmapx_location",
    "apply_ghostmapx_location",
]
