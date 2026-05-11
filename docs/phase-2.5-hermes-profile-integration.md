# Phase 2.5: Hermes Profile Integration

## 接入目标

让 configured Hermes Profile 能加载本仓库的本机 Skill，并通过本仓库的 Python 工具调用 USB 连接的 Pixel 6 ADB 控制能力。

本阶段只验证设备控制基础能力：ADB 状态、通用输入、屏幕读取、截图。不实现企业 App 打卡流程，不实现风控绕过、隐藏 Mock Location、反检测、Root 或 Hook。

## 软链接方式

目标链接：

```bash
$HERMES_PROFILE_DIR/skills/$HERMES_ANDROID_SKILL_LINK_NAME
```

指向：

```bash
$HERMES_ANDROID_SOURCE_DIR
```

创建链接：

```bash
cd $HERMES_ANDROID_SOURCE_DIR
bash scripts/link_to_sunny_wechat_lite.sh
```

## 自测命令

```bash
cd $HERMES_ANDROID_SOURCE_DIR
bash scripts/verify_hermes_profile_link.sh
PYTHONPATH=src python3 scripts/hermes_preflight.py
```

`hermes_preflight.py` 会检查：

- `hermes_android_controller.skill_tools` 是否可导入
- `android_device_status()` 是否可调用

它不会操作任何企业 App。

## Hermes 重启命令

创建或更新 Skill 软链接后，重启 Hermes 进程以重新扫描 Skills：

```bash
launchctl list | grep -i hermes
```

如果 Hermes 以 launchd 服务运行，按实际服务名执行：

```bash
launchctl kickstart -k gui/$(id -u)/<hermes-service-name>
```

如果 Hermes 是前台 TUI/CLI 进程，退出后重新启动对应 profile：

```bash
hermes --profile <configured-profile>
```

## 微信测试话术

用于验证 Hermes 是否加载了本 Skill，可在微信侧发送：

```text
检查 Pixel 6 ADB 状态
```

预期 Hermes 会使用本仓库能力检查设备状态，只返回设备连接与响应情况。

可继续发送：

```text
对 Pixel 6 执行 Hermes Android preflight
```

预期 Hermes 运行本仓库 preflight，返回 import 和 ADB 状态结果。不应操作企业 App。

## 故障排查

### Skill 未加载

检查软链接和 `SKILL.md`：

```bash
ls -ld $HERMES_PROFILE_DIR/skills/$HERMES_ANDROID_SKILL_LINK_NAME
ls -l $HERMES_PROFILE_DIR/skills/$HERMES_ANDROID_SKILL_LINK_NAME/SKILL.md
```

然后重启 Hermes，让 profile 重新扫描 Skills。

### 微信回复误路由到 Apple Calendar

如果微信侧发送：

```text
运行 Hermes Android preflight
```

却回复当前 profile 只包含 Apple Calendar 或找不到 Android preflight，先从本仓库运行：

```bash
cd $HERMES_ANDROID_SOURCE_DIR
bash scripts/verify_hermes_profile_link.sh
PYTHONPATH=src python3 scripts/hermes_preflight.py
```

若两个命令都通过，说明本仓库和 ADB 侧是好的，问题通常在 Hermes 当前微信运行实例的 profile 路由上下文：重启配置的 Hermes profile，让 `.skills_prompt_snapshot.json` 和 `SOUL.md` 重新进入当前对话上下文。

建议在 profile 的 Android 路由提示中明确加入：

```text
当用户说“运行 Hermes Android preflight”“检查 Pixel 6 ADB 状态”“检查安卓手机状态”时，必须使用 $HERMES_ANDROID_SOURCE_DIR/SKILL.md，并运行本仓库 scripts/hermes_preflight.py 或 scripts/verify_hermes_profile_link.sh；不得回答该项目是 Apple Calendar 项目。
```

### Python import 失败

使用 `PYTHONPATH=src` 从仓库根目录运行：

```bash
cd $HERMES_ANDROID_SOURCE_DIR
PYTHONPATH=src python3 -c 'from hermes_android_controller.skill_tools import android_device_status; print(android_device_status()["message"])'
```

如果仍失败，检查当前目录是否为仓库根目录，或安装 editable package：

```bash
python3 -m pip install -e .
```

### adb 找不到

确认 Android Platform Tools 已安装并在 `PATH`：

```bash
command -v adb
adb devices -l
```

若 Hermes 由 launchd 启动，注意 launchd 环境的 `PATH` 可能比交互式 shell 更短，需要在启动配置中加入 platform-tools 路径。

### Pixel unauthorized/offline

查看设备状态：

```bash
adb devices -l
```

`unauthorized`：解锁 Pixel 6，接受 USB debugging 授权提示。

`offline`：重新插拔 USB，必要时运行：

```bash
adb kill-server
adb start-server
adb devices -l
```
