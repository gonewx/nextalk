# NexTalk UI 组件

本目录包含NexTalk客户端的UI组件实现。

## 组件说明

### 焦点窗口 (focus_window.py)

焦点窗口是一个始终置顶的半透明窗口，用于在xdotool文本注入失败时显示转录文本。

**主要特点：**

- 在屏幕下方显示一个半透明的文本窗口
- 可自动淡出和隐藏
- 支持在独立线程中运行，不影响主应用程序
- 提供简单的API用于显示文本

**使用方法：**

```python
from nextalk_client.ui.focus_window import show_text

# 显示文本5秒
show_text("这是要显示的文本", duration_seconds=5)
```

**调试问题：**

如果焦点窗口未显示或不正常工作，请检查：

1. tkinter库是否已安装 (sudo apt install python3-tk)
2. 日志输出中是否有相关错误
3. 尝试增加显示时间以便于观察

### 托盘图标 (tray_icon.py)

系统托盘图标为NexTalk提供了一个常驻系统托盘的界面。

**主要功能：**

- 显示当前状态
- 提供菜单管理ASR模型和退出程序
- 直观地显示识别状态

### 通知 (notifications.py)

桌面通知模块用于发送系统通知。

**主要功能：**

- 显示错误和状态变更通知
- 支持不同的紧急级别

## 调试UI相关问题

当转录文字无法正常显示在焦点窗口时，可以尝试以下方法：

1. 检查xdotool的安装和权限：
   ```bash
   sudo apt install xdotool
   xdotool version
   ```

2. 测试xdotool基本功能：
   ```bash
   xdotool type "test"
   ```

3. 启用调试日志：
   ```bash
   NEXTALK_DEBUG=1 python -m nextalk_client.main
   ```

4. 检查tkinter是否正常工作：
   ```bash
   python -c "import tkinter; tkinter.Tk().mainloop()"
   ```

5. 显示窗口ID和名称：
   ```bash
   xdotool getactivewindow getwindowname
   ```

## 问题解决

如果文本输入仍然无法正常工作，请尝试：

1. 使用焦点窗口模式：转录文本会显示在一个始终置顶的窗口中
2. 使用剪贴板功能：转录文本会复制到系统剪贴板，可以手动粘贴
3. 切换到其他输入法或禁用当前输入法
4. 检查目标窗口是否接受文本输入 