# Phase 5.5: WeChat Approval Plan Report

Phase 5.5 adds a concise WeChat-facing report for the Phase 4 dry-run approval
plan. The report itself is display-only; execution is handled separately by
`android_execute_daily_approval_plan` or by the scheduler when local auto
execution is enabled.

## WeChat Output

Recommended WeChat wording:

```text
生成打卡审批报告
```

Hermes should treat that as equivalent to `生成微信审批计划报告`, then reply with
only the Markdown table and confirmation prompt:

```markdown
| 审批类型 | 状态 | 数量 | 明细 | 处理方式 |
|---|---:|---:|---|---|
| 工时审批 | 待处理 | 1 项/4 人 | 项目数 1，待审批 4 人 | 确认后执行 |
| 考勤异常审批 | 待处理 | 4 条 | 申请人A 2，申请人B 2 | 确认后执行 |
| 请假审批 | 无数据 | 0 | 暂无数据 | 跳过 |
| 调休时长审批 | 无数据 | 0 | 暂无数据 | 跳过 |
| 未打卡审批 | 待处理 | 1 条 | 申请人C | 确认后执行 |

如确认执行，请回复：
确认审批
```

Do not include:

- `risk_level`
- XML paths
- Screenshot paths
- Raw dry-run JSON
- `.env` values

## Tool

Use:

```python
from hermes_android_controller.skill_tools import android_build_approval_wechat_report

report = android_build_approval_wechat_report()
print(report["markdown"])
```

The tool builds a fresh dry-run plan, formats it for WeChat, and returns a compact
payload containing the Markdown report and confirmation requirement.

## Execution Boundary

The report does not approve anything.
Execution still requires either the exact user reply:

```text
确认审批
```

or local `.env` setting `OA_APPROVAL_AUTO_EXECUTE=true`.

Approval execution remains handled by `android_execute_daily_approval_plan`.
