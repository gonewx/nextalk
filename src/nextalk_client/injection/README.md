# NexTalk 智能文本注入器

## 概述

NexTalk 现在支持多种文本注入方式，能够自动选择最佳的注入方法，确保在不同环境下都能可靠地将识别的文本注入到活动窗口。

## 注入方法

### 1. 输入法框架（推荐）

- **Fcitx** - 支持 Fcitx5 和 Fcitx4，通过 D-Bus 接口直接提交文本
- **IBus** - 通过 D-Bus 接口与 IBus 通信，直接提交文本到输入上下文

优点：
- 最可靠，完美支持中文和其他 Unicode 字符
- 不依赖剪贴板，不会干扰用户的剪贴板内容
- 速度快，直接提交文本

### 2. 剪贴板粘贴

通过以下方式实现：
- 保存当前剪贴板内容
- 将文本复制到剪贴板
- 模拟 Ctrl+V 粘贴操作
- 恢复原剪贴板内容

优点：
- 兼容性好，支持所有字符
- 速度较快

缺点：
- 会短暂修改剪贴板

### 3. 模拟键盘输入

使用 pyautogui 或 xdotool 模拟键盘按键。

优点：
- 不需要剪贴板
- 简单直接

缺点：
- 速度较慢
- 可能有编码问题

## 配置

在 `~/.config/nextalk/client.ini` 中配置：

```ini
[Client]
; 注入器类型 (smart, legacy, fallback)
injector_type=smart

; 后备注入方法 (paste, type, xdotool, auto)
fallback_method=auto
```

### 配置选项说明

**injector_type**:
- `smart` - 智能注入器，自动选择最佳方法（推荐）
- `legacy` - 旧版注入器，使用 pyautogui/pyclip
- `fallback` - 只使用后备方法（剪贴板/模拟键入）

**fallback_method**:
- `auto` - 自动选择（默认）
- `paste` - 剪贴板粘贴
- `type` - 模拟键盘输入
- `xdotool` - Linux xdotool 工具

## 自动检测

系统会自动检测并优先使用：
1. 当前运行的输入法框架（Fcitx/IBus）
2. 如果检测到 Fcitx，优先使用 Fcitx
3. 如果检测到 IBus，优先使用 IBus
4. 如果都没有，使用后备方法

检测方式：
- 环境变量（GTK_IM_MODULE, QT_IM_MODULE 等）
- 运行的进程（fcitx5, fcitx, ibus-daemon）
- D-Bus 服务

## 依赖

### 必需依赖
无

### 可选依赖

输入法框架支持：
```bash
pip install dbus-python
```

后备方法支持：
```bash
pip install pyautogui pyclip
# 或
pip install pyautogui pyperclip
```

Linux 特定：
```bash
sudo apt-get install xdotool  # Debian/Ubuntu
sudo dnf install xdotool      # Fedora
```

## 测试

运行测试脚本：
```bash
cd nextalk
python test_injector.py
```

运行单元测试：
```bash
python -m pytest tests/client/unit/test_injector.py -v
```

## 故障排除

### Fcitx/IBus 注入器不工作

1. 确保输入法服务正在运行：
```bash
# Fcitx
ps aux | grep fcitx

# IBus
ps aux | grep ibus-daemon
```

2. 检查 D-Bus 服务：
```bash
dbus-send --session --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames
```

3. 确保安装了 python-dbus：
```bash
pip install dbus-python
```

### 后备方法不工作

1. 检查依赖安装：
```bash
pip list | grep -E "pyautogui|pyclip|pyperclip"
```

2. 检查 xdotool（Linux）：
```bash
which xdotool
```

### 调试

启用调试日志查看详细信息：
```bash
python scripts/run_client.py --log-level DEBUG
```