"""Daily OA approval report scheduler.

This module schedules and sends the dry-run approval report. Real approval
execution remains gated by the WeChat confirmation phrase or local
OA_APPROVAL_AUTO_EXECUTE authorization.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import random
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from .artifact_archive import collect_artifacts, prune_old_runs, runs_dir
from .approval_report import format_approval_wechat_report
from .env_config import env_value
from .enterprise_approval_probe import build_daily_approval_plan


DEFAULT_STATE_DIR = Path("var/oa_approval")
DEFAULT_WINDOW_START = "14:00"
DEFAULT_WINDOW_END = "16:00"
RETENTION_DAYS = 15


def run_once_if_due(now: dt.datetime | None = None) -> dict[str, object]:
    """Run today's scan only when the current time is inside/after the window."""

    load_local_env()
    current = now or dt.datetime.now()
    state = load_state()
    today = current.date().isoformat()
    if state.get("last_report_date") == today:
        return {"ok": True, "status": "skipped", "reason": "already_ran_today", "date": today}

    scheduled_at = scheduled_datetime_for_day(current.date(), state=state)
    save_state(state)
    window_end = dt.datetime.combine(current.date(), _parse_time(os.getenv("OA_APPROVAL_WINDOW_END", DEFAULT_WINDOW_END)))
    if current > window_end:
        return {
            "ok": True,
            "status": "skipped",
            "reason": "missed_daily_window",
            "date": today,
            "scheduled_at": scheduled_at.isoformat(timespec="seconds"),
            "window_end": window_end.isoformat(timespec="seconds"),
        }
    if current < scheduled_at:
        return {
            "ok": True,
            "status": "waiting",
            "date": today,
            "scheduled_at": scheduled_at.isoformat(timespec="seconds"),
        }

    result = run_daily_scan(current)
    state["last_report_date"] = today
    state["last_report_at"] = current.isoformat(timespec="seconds")
    if result.get("safety", {}).get("auto_execute"):
        state.pop("pending_confirmation", None)
        state["last_auto_execution"] = {
            "date": today,
            "report_run_id": result.get("run_id"),
            "created_at": current.isoformat(timespec="seconds"),
            "ok": result.get("execution", {}).get("ok"),
        }
    else:
        state["pending_confirmation"] = {
            "date": today,
            "report_run_id": result.get("run_id"),
            "created_at": current.isoformat(timespec="seconds"),
            "confirm_phrase": "确认审批",
        }
    save_state(state)
    prune_old_runs()
    return result


def run_daily_worker(poll_seconds: int = 60) -> None:
    """Run forever, checking whether today's random scan time has arrived."""

    while True:
        result = run_once_if_due()
        _append_worker_log(result)
        time.sleep(max(10, poll_seconds))


def run_daily_scan(now: dt.datetime | None = None) -> dict[str, object]:
    """Open the enterprise app, build the dry-run plan, persist artifacts, and push WeChat."""

    load_local_env()
    current = now or dt.datetime.now()
    run_id = current.strftime("%Y%m%d-%H%M%S")
    run_dir = runs_dir() / run_id
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    plan = build_daily_approval_plan()
    markdown = format_approval_wechat_report(plan)
    artifacts = collect_artifacts(plan, artifacts_dir)

    _write_json(run_dir / "plan.json", plan)
    (run_dir / "report.md").write_text(markdown, encoding="utf-8")
    _write_json(run_dir / "artifacts.json", artifacts)

    send_result = send_wechat_markdown(markdown)
    execution_result = None
    execution_send_result = None
    if _auto_execute_enabled():
        from .enterprise_approval_executor import execute_daily_approval_plan

        execution_result = execute_daily_approval_plan("")
        execution_send_result = send_wechat_markdown(_format_execution_wechat_report(execution_result))
    result = {
        "ok": (
            bool(plan.get("ok", True))
            and bool(send_result.get("ok"))
            and (execution_result is None or bool(execution_result.get("ok")))
            and (execution_send_result is None or bool(execution_send_result.get("ok")))
        ),
        "status": "sent" if send_result.get("ok") else "send_failed",
        "mode": "daily_oa_approval_scan",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "report_path": str(run_dir / "report.md"),
        "plan_path": str(run_dir / "plan.json"),
        "artifact_count": len(artifacts),
        "send": send_result,
        "execution_send": execution_send_result,
        "execution": execution_result,
        "safety": {
            "auto_execute": execution_result is not None,
            "confirmation_required": execution_result is None,
            "confirmation_phrase": "确认审批",
            "auto_execute_env": "OA_APPROVAL_AUTO_EXECUTE",
        },
    }
    _write_json(run_dir / "result.json", result)
    return result


def _format_execution_wechat_report(execution: dict[str, object]) -> str:
    results = execution.get("results", [])
    if not isinstance(results, list):
        results = []
    authorization = execution.get("authorization")
    authorization_mode = authorization.get("mode", "") if isinstance(authorization, dict) else ""
    final_home = execution.get("final_home")
    returned_home = bool(final_home.get("ok")) if isinstance(final_home, dict) else False
    lines = [
        "## 今日审批执行结果",
        "",
        f"- 总体状态：{'成功' if execution.get('ok') else '需要检查'}",
        f"- 授权方式：{authorization_mode}",
        f"- 已退回主界面：{'是' if returned_home else '否'}",
        "",
        "| 菜单 | 状态 | 结果 |",
        "| --- | --- | --- |",
    ]
    for item in results:
        if not isinstance(item, dict):
            continue
        menu_name = str(item.get("menu_name", ""))
        if item.get("executed") is False or item.get("status") == "skipped":
            status = "跳过"
            detail = str(item.get("reason", ""))
        else:
            status = "已执行" if item.get("ok") else "需检查"
            detail = str(item.get("message") or item.get("status") or "")
        lines.append(f"| {menu_name} | {status} | {detail} |")
    if not results:
        lines.append("| 无 | 无待执行审批 | - |")
    return "\n".join(lines)


def scheduled_datetime_for_day(day: dt.date, *, state: dict[str, Any] | None = None) -> dt.datetime:
    """Return the random scheduled datetime for a day, stable once stored."""

    values = state if state is not None else load_state()
    key = day.isoformat()
    schedules = values.setdefault("scheduled_times", {})
    if key not in schedules:
        start = _parse_time(os.getenv("OA_APPROVAL_WINDOW_START", DEFAULT_WINDOW_START))
        end = _parse_time(os.getenv("OA_APPROVAL_WINDOW_END", DEFAULT_WINDOW_END))
        schedules[key] = _random_time_between(start, end).strftime("%H:%M:%S")
    return dt.datetime.combine(day, dt.time.fromisoformat(schedules[key]))


def send_wechat_markdown(markdown: str) -> dict[str, object]:
    """Send Markdown through a Hermes deliver-only webhook route."""

    url = os.getenv("OA_APPROVAL_WECHAT_WEBHOOK_URL", "").strip()
    secret = os.getenv("OA_APPROVAL_WECHAT_WEBHOOK_SECRET", "").strip()
    chat_id = os.getenv("OA_APPROVAL_WECHAT_CHAT_ID", "").strip()
    if not url or not secret or not chat_id:
        return {
            "ok": False,
            "status": "not_configured",
            "message": "Set OA_APPROVAL_WECHAT_WEBHOOK_URL, OA_APPROVAL_WECHAT_WEBHOOK_SECRET, and OA_APPROVAL_WECHAT_CHAT_ID.",
        }

    body = json.dumps(
        {
            "event_type": "oa_approval_report",
            "message": markdown,
            "chat_id": chat_id,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Request-ID": f"oa-approval-{int(time.time())}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= response.status < 300,
                "status": response.status,
                "response": response_body[:1000],
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status": exc.code,
            "response": exc.read().decode("utf-8", errors="replace")[:1000],
        }
    except urllib.error.URLError as exc:
        return {"ok": False, "status": "url_error", "message": str(exc)}


def _auto_execute_enabled() -> bool:
    return env_value("OA_APPROVAL_AUTO_EXECUTE").lower() in {"1", "true", "yes", "on"}


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {"scheduled_times": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"scheduled_times": {}}
    return value if isinstance(value, dict) else {"scheduled_times": {}}


def load_local_env(path: str | Path = ".env") -> None:
    """Load simple KEY=VALUE pairs from a local .env without overriding env vars."""

    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def save_state(state: Mapping[str, Any]) -> None:
    _write_json(state_path(), state)


def state_dir() -> Path:
    return Path(os.getenv("OA_APPROVAL_STATE_DIR", str(DEFAULT_STATE_DIR)))


def state_path() -> Path:
    return state_dir() / "state.json"


def _parse_time(value: str) -> dt.time:
    hour, minute = value.split(":", 1)
    return dt.time(hour=int(hour), minute=int(minute[:2]))


def _random_time_between(start: dt.time, end: dt.time) -> dt.time:
    start_seconds = start.hour * 3600 + start.minute * 60 + start.second
    end_seconds = end.hour * 3600 + end.minute * 60 + end.second
    if end_seconds <= start_seconds:
        raise ValueError("OA approval schedule end must be after start.")
    second = random.randint(start_seconds, end_seconds)
    return dt.time(hour=second // 3600, minute=(second % 3600) // 60, second=second % 60)


def _write_json(path: Path, value: Mapping[str, Any] | dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(value), ensure_ascii=False, indent=2), encoding="utf-8")


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value, key=str)]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _append_worker_log(result: Mapping[str, object]) -> None:
    log_path = state_dir() / "worker.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"ts": dt.datetime.now().isoformat(timespec="seconds"), **dict(result)}, ensure_ascii=False)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daily OA approval report scheduler.")
    parser.add_argument("--once", action="store_true", help="Check once and exit.")
    parser.add_argument("--force", action="store_true", help="Run the dry-run scan and push report immediately.")
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args(argv)

    if args.force:
        result = run_daily_scan()
    elif args.once:
        result = run_once_if_due()
    else:
        run_daily_worker(poll_seconds=args.poll_seconds)
        return 0

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
