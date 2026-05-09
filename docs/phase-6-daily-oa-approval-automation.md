# Phase 6: Daily OA Approval Report Automation

## Goal

Hermes can run one daily OA approval scan at a random time between 14:00 and
16:00, send a concise Markdown approval plan to WeChat, and then wait for the
user to reply:

```text
确认审批
```

The scheduled job never executes approvals by itself.

## Flow

1. The scheduler picks and stores one random time for the current day.
2. When the time arrives, it opens the enterprise approval app and builds a
   dry-run approval plan.
3. It saves the raw plan, Markdown report, copied screenshots, and copied UI
   XML under `var/oa_approval/runs/<run-id>/`.
4. It sends the Markdown report to WeChat through a Hermes deliver-only webhook.
5. The existing WeChat route waits for the user to reply `确认审批`.
6. Only that reply triggers controlled approval execution.
7. Hermes sends the execution result back to WeChat.

## Configuration

Add these values to local `.env`:

```dotenv
OA_APPROVAL_WECHAT_WEBHOOK_URL=http://127.0.0.1:8644/webhooks/oa-approval-report
OA_APPROVAL_WECHAT_WEBHOOK_SECRET=
OA_APPROVAL_WECHAT_CHAT_ID=
OA_APPROVAL_WINDOW_START=14:00
OA_APPROVAL_WINDOW_END=16:00
OA_APPROVAL_STATE_DIR=var/oa_approval
```

Do not commit `.env`.

The Hermes `sunny-wechat-lite` profile needs a deliver-only webhook route:

```yaml
platforms:
  webhook:
    enabled: true
    extra:
      routes:
        oa-approval-report:
          secret: "<same value as OA_APPROVAL_WECHAT_WEBHOOK_SECRET>"
          deliver_only: true
          deliver: weixin
          prompt: "{message}"
          deliver_extra:
            chat_id: "{chat_id}"
          rate_limit: 10
```

## Commands

Check whether the daily scan is due:

```bash
PYTHONPATH=src python3 scripts/daily_approval_scheduler.py --once
```

Run a report immediately for testing:

```bash
PYTHONPATH=src python3 scripts/daily_approval_scheduler.py --force
```

Run as a long-lived worker:

```bash
PYTHONPATH=src python3 scripts/daily_approval_scheduler.py --poll-seconds 60
```

## launchd

A practical launchd setup is to run `--once` every five minutes. The scheduler
state makes this safe: it only sends the report once per day and keeps the
random scheduled time stable.

Use a LaunchAgent that runs:

```bash
cd /Users/administrator/Code/hermes-android-device-controller
PYTHONPATH=src python3 scripts/daily_approval_scheduler.py --once
```

with `StartInterval` set to `300`.

## Retention

Runs older than 15 days are pruned automatically after each scan. Each retained
run stores:

- `plan.json`
- `report.md`
- `result.json`
- `artifacts.json`
- copied screenshot and UI XML files under `artifacts/`

## Safety

- The scheduled job does not click approval, pass, agree, submit, or confirm.
- The scheduled job only sends a dry-run report.
- Real approval execution still requires the exact WeChat phrase `确认审批`.
- Credentials remain local in `.env`.
- No SMS reading, risk-control bypass, anti-detection, Root, or Hook behavior is
  implemented.
