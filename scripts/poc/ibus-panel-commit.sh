#!/usr/bin/env bash
set -euo pipefail
# 用法：ibus-panel-commit.sh [--legacy] [delay_seconds] [text]
# docs/research/ibus-support-2026.md §8 测试矩阵，逐字读回核对：
# 1. ptyxis（Wayland）：应上屏。
# 2. ptyxis（GDK_BACKEND=x11）：应上屏。
# 3. xterm（XIM）：记录实际结果。
# 4. Qt X11 应用 / Electron（VS Code）：记录实际结果。
# 5. 文件管理器（无可编辑焦点）：应返回 ERR，不能静默丢弃。
# 6. 拼音引擎中英文模式 / 预编辑中途：不改变引擎状态。
# 7. emoji 选择器（Super+.）：记录实际行为。
method=CommitTextViaPanel
if [[ "${1:-}" == --legacy ]]; then
    method=CommitText
    shift
fi
if (( $# > 2 )); then
    echo '用法：ibus-panel-commit.sh [--legacy] [delay_seconds] [text]' >&2
    exit 2
fi
delay_seconds="${1:-3}"
text="${2-你好世界，Nextalk Panel 注入测试 OK}"
printf '请在 %s 秒内聚焦目标窗口的测试位置，即将调用 %s。\n' "$delay_seconds" "$method"
sleep "$delay_seconds"
gdbus call --session --dest org.gnome.Shell \
    --object-path /com/gonewx/nextalk/Inject \
    --method "com.gonewx.nextalk.Inject.$method" "$text"
