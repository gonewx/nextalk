# NexTalk 故障排除指南

## 概述

本文档收集了 NexTalk 系统中常见问题及其解决方案，帮助用户快速定位和解决问题。

## 文本注入问题

### Portal 机制不工作

**问题描述**：
在 Wayland 环境下，Portal RemoteDesktop 机制无法正常工作，系统自动回退到 xdotool 机制。

**常见症状**：
- 环境检测显示 `Portal available: False`
- 在 Wayland 桌面上文本注入效果不理想
- 日志中出现 `No module named 'dbus'` 错误

**根本原因**：
虚拟环境中缺失 D-Bus Python 绑定模块。

**解决步骤**：

1. **检查症状**：
```bash
# 检查当前状态
python -c "
from nextalk.output.environment_detector import EnvironmentDetector
detector = EnvironmentDetector()
env = detector.detect_environment()
print(f'Display server: {env.display_server.value}')
print(f'Portal available: {env.portal_available}')
print(f'Recommended method: {env.recommended_method.value}')
"
```

2. **安装系统依赖**：
```bash
# Ubuntu/Debian
sudo apt install python3-dbus python3-gi

# Fedora/RHEL
sudo dnf install python3-dbus python3-gobject

# Arch Linux
sudo pacman -S python-dbus python-gobject
```

3. **链接到虚拟环境**：
```bash
# 进入虚拟环境的 site-packages 目录
cd .venv/lib/python3.*/site-packages

# 创建软链接
ln -sf /usr/lib/python3/dist-packages/dbus .
ln -sf /usr/lib/python3/dist-packages/_dbus_bindings.* .
ln -sf /usr/lib/python3/dist-packages/_dbus_glib_bindings.* .
ln -sf /usr/lib/python3/dist-packages/dbus_python*.egg-info .
ln -sf /usr/lib/python3/dist-packages/gi .
ln -sf /usr/lib/python3/dist-packages/PyGObject*.egg-info .
```

4. **验证修复**：
```bash
# 测试 dbus 导入
python -c "
try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    print('✅ D-Bus 模块可用')
except ImportError as e:
    print('❌ D-Bus 模块不可用:', e)
"

# 测试 Portal 机制
python -c "
from nextalk.output.text_injector import TextInjector
import asyncio

async def test():
    injector = TextInjector()
    success = await injector.initialize()
    if success:
        status = await injector.get_ime_status()
        method = status.get('active_method', 'unknown')
        print(f'✅ 文本注入器初始化成功，使用方法: {method}')
        if method == 'portal':
            print('✅ Portal 机制工作正常!')
    else:
        print('❌ 文本注入器初始化失败')
    await injector.cleanup()

asyncio.run(test())
"
```

### XDoTool 机制不工作

**问题描述**：
在 X11 环境下，xdotool 无法正常注入文本。

**常见症状**：
- 命令 `xdotool type "test"` 无效果
- 文本注入完全失效
- 日志中出现 xdotool 相关错误

**解决步骤**：

1. **检查 xdotool 安装**：
```bash
# 检查是否安装
which xdotool

# 安装 xdotool
sudo apt install xdotool  # Ubuntu/Debian
sudo dnf install xdotool  # Fedora/RHEL
sudo pacman -S xdotool    # Arch Linux
```

2. **检查 X11 环境**：
```bash
# 检查 X11 显示
echo $DISPLAY
# 应该显示类似 :0 或 :1

# 检查 X11 权限
xhost +local:
```

3. **测试 xdotool 功能**：
```bash
# 基础测试
xdotool version

# 功能测试（在文本编辑器中运行）
xdotool type "test message"
```

## 音频相关问题

### 音频设备检测失败

**问题描述**：
系统无法检测到音频设备或音频采集失败。

**解决步骤**：

1. **检查音频设备**：
```bash
# 列出音频设备
python -c "
import sounddevice as sd
print('可用音频设备:')
print(sd.query_devices())
"
```

2. **检查系统权限**：
```bash
# 检查用户是否在 audio 组
groups $USER | grep audio

# 添加到 audio 组（需要重新登录）
sudo usermod -a -G audio $USER
```

3. **安装音频依赖**：
```bash
# Ubuntu/Debian
sudo apt install portaudio19-dev python3-pyaudio

# Fedora/RHEL
sudo dnf install portaudio-devel

# 重新安装 sounddevice
pip install sounddevice --upgrade
```

## 网络连接问题

### FunASR 服务器连接失败

**问题描述**：
无法连接到 FunASR WebSocket 服务器。

**解决步骤**：

1. **检查服务器状态**：
```bash
# 检查服务器是否运行
ps aux | grep funasr

# 检查端口占用
netstat -tulpn | grep 10095
```

2. **启动 FunASR 服务器**：
```bash
# 启动服务器
python funasr_wss_server.py

# 等待模型加载完成
# 应该看到 "model loaded!" 消息
```

3. **测试连接**：
```bash
# 测试 WebSocket 连接
python -c "
import asyncio
import websockets

async def test_connection():
    try:
        uri = 'ws://localhost:10095'
        async with websockets.connect(uri) as websocket:
            print('✅ WebSocket 连接成功')
    except Exception as e:
        print(f'❌ WebSocket 连接失败: {e}')

asyncio.run(test_connection())
"
```

## 系统托盘问题

### 托盘图标不显示

**问题描述**：
系统托盘中没有显示 NexTalk 图标。

**解决步骤**：

1. **检查桌面环境支持**：
```bash
# 检查系统托盘支持
python -c "
import os
desktop = os.environ.get('XDG_CURRENT_DESKTOP', 'unknown')
print(f'桌面环境: {desktop}')

# 检查托盘服务
import subprocess
try:
    result = subprocess.run(['pgrep', '-f', 'tray'], capture_output=True)
    if result.returncode == 0:
        print('✅ 托盘服务运行中')
    else:
        print('❌ 未检测到托盘服务')
except:
    print('❌ 无法检查托盘服务')
"
```

2. **安装 GUI 依赖**：
```bash
# 安装托盘依赖
pip install -r requirements-gui.txt

# Ubuntu/Debian 系统依赖
sudo apt install python3-tk libappindicator3-1

# Fedora/RHEL
sudo dnf install tkinter libappindicator-gtk3
```

3. **手动启动托盘**：
```bash
# 仅启动托盘（调试用）
python -c "
from nextalk.ui.tray import create_system_tray
import asyncio

async def test_tray():
    tray = create_system_tray()
    print('托盘已启动，按 Ctrl+C 退出')
    try:
        await tray.run()
    except KeyboardInterrupt:
        print('托盘已停止')

asyncio.run(test_tray())
"
```

## 权限问题

### Linux 权限相关

**问题描述**：
在 Linux 系统上遇到权限相关的错误。

**解决步骤**：

1. **检查必要权限**：
```bash
# 检查用户组
id $USER

# 添加到必要组
sudo usermod -a -G audio,input $USER
```

2. **Wayland 权限**：
```bash
# 检查 Wayland 会话
echo $WAYLAND_DISPLAY

# 检查 Portal 权限（会弹出权限对话框）
python -c "
from nextalk.output.portal_injector import PortalInjector
import asyncio

async def test_portal():
    injector = PortalInjector()
    try:
        success = await injector.initialize()
        print(f'Portal 初始化: {\"成功\" if success else \"失败\"}')
    except Exception as e:
        print(f'Portal 错误: {e}')
    finally:
        await injector.cleanup()

asyncio.run(test_portal())
"
```

## 性能问题

### 文本注入延迟过高

**问题描述**：
文本注入有明显的延迟。

**解决步骤**：

1. **调整注入参数**：
```yaml
# 在 config/nextalk.yaml 中调整
text_injection:
  inject_delay: 0.05  # 减少延迟
  xdotool_delay: 0.01 # 减少按键间隔
```

2. **检查系统负载**：
```bash
# 检查 CPU 使用率
top

# 检查内存使用
free -h

# 检查磁盘 I/O
iostat -x 1
```

### 语音识别响应慢

**问题描述**：
语音识别响应时间过长。

**解决步骤**：

1. **检查模型加载**：
```bash
# 查看 FunASR 服务器日志
python funasr_wss_server.py --log-level DEBUG
```

2. **调整音频参数**：
```yaml
# 在 config/nextalk.yaml 中调整
audio:
  chunk_size: [5, 10, 5]  # 使用更小的块大小
  sample_rate: 16000      # 确保正确的采样率
```

## 调试技巧

### 启用详细日志

```bash
# 设置环境变量
export NEXTALK_DEBUG=1
export PYTHONPATH=$PWD

# 启动时启用详细日志
python -m nextalk --log-level DEBUG
```

### 使用调试脚本

```bash
# 环境检测调试
python -c "
from nextalk.output.environment_detector import EnvironmentDetector
detector = EnvironmentDetector()
debug_info = detector.get_debug_info()
import json
print(json.dumps(debug_info, indent=2))
"

# 文本注入器调试
python -c "
from nextalk.output.text_injector import TextInjector
import asyncio

async def debug_injector():
    injector = TextInjector()
    success = await injector.initialize()
    if success:
        report = injector.get_compatibility_report()
        import json
        print(json.dumps(report, indent=2, default=str))
    await injector.cleanup()

asyncio.run(debug_injector())
"
```

### 检查系统兼容性

```bash
# 运行完整兼容性检查
python scripts/verify_installation.py --verbose

# 检查特定功能
python -c "
from nextalk.output.injection_factory import get_injection_factory
import asyncio

async def check_compatibility():
    factory = get_injection_factory()
    available_methods = await factory.get_available_methods()
    print(f'可用的注入方法: {[m.value for m in available_methods]}')
    
    test_results = await factory.test_all_injectors()
    print('注入器测试结果:')
    for method, result in test_results.items():
        status = '✅ 通过' if result else '❌ 失败'
        print(f'  {method.value}: {status}')

asyncio.run(check_compatibility())
"
```

## 常用诊断命令

### 系统信息收集

```bash
# 创建诊断信息脚本
cat > diagnostic.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
from datetime import datetime

print("=== NexTalk 诊断信息 ===")
print(f"时间: {datetime.now()}")
print(f"Python: {sys.version}")
print(f"平台: {platform.platform()}")
print(f"架构: {platform.machine()}")
print()

print("=== 环境变量 ===")
for var in ['DISPLAY', 'WAYLAND_DISPLAY', 'XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP']:
    value = os.environ.get(var, '未设置')
    print(f"{var}: {value}")
print()

print("=== 已安装包 ===")
try:
    import dbus
    print("✅ dbus 可用")
except ImportError:
    print("❌ dbus 不可用")

try:
    import gi
    print("✅ gi (PyGObject) 可用")
except ImportError:
    print("❌ gi (PyGObject) 不可用")

try:
    import sounddevice
    print("✅ sounddevice 可用")
except ImportError:
    print("❌ sounddevice 不可用")

print()
print("=== 系统工具 ===")
tools = ['xdotool', 'wl-copy', 'xclip']
for tool in tools:
    try:
        result = subprocess.run(['which', tool], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {tool}: {result.stdout.strip()}")
        else:
            print(f"❌ {tool}: 未安装")
    except:
        print(f"❌ {tool}: 检查失败")

print()
print("=== NexTalk 模块测试 ===")
try:
    from nextalk.output.environment_detector import EnvironmentDetector
    detector = EnvironmentDetector()
    env = detector.detect_environment()
    print(f"✅ 环境检测: {env.display_server.value}")
    print(f"Portal 可用: {env.portal_available}")
    print(f"xdotool 可用: {env.xdotool_available}")
    print(f"推荐方法: {env.recommended_method.value}")
except Exception as e:
    print(f"❌ 环境检测失败: {e}")
EOF

python diagnostic.py
```

### 快速修复脚本

```bash
# 创建一键修复脚本
cat > fix_portal.sh << 'EOF'
#!/bin/bash
echo "=== NexTalk Portal 修复脚本 ==="

# 检查系统包
echo "检查系统依赖..."
if command -v apt &> /dev/null; then
    sudo apt install -y python3-dbus python3-gi
elif command -v dnf &> /dev/null; then
    sudo dnf install -y python3-dbus python3-gobject
elif command -v pacman &> /dev/null; then
    sudo pacman -S --needed python-dbus python-gobject
else
    echo "未识别的包管理器，请手动安装 python3-dbus 和 python3-gi"
fi

# 查找虚拟环境
if [ -d ".venv" ]; then
    SITE_PACKAGES=$(find .venv -name "site-packages" -type d | head -1)
    if [ -n "$SITE_PACKAGES" ]; then
        echo "在 $SITE_PACKAGES 中创建软链接..."
        cd "$SITE_PACKAGES"
        
        # 创建软链接
        ln -sf /usr/lib/python3/dist-packages/dbus . 2>/dev/null || \
        ln -sf /usr/lib/python3*/site-packages/dbus . 2>/dev/null
        
        ln -sf /usr/lib/python3/dist-packages/_dbus_bindings.* . 2>/dev/null || \
        ln -sf /usr/lib/python3*/site-packages/_dbus_bindings.* . 2>/dev/null
        
        ln -sf /usr/lib/python3/dist-packages/_dbus_glib_bindings.* . 2>/dev/null || \
        ln -sf /usr/lib/python3*/site-packages/_dbus_glib_bindings.* . 2>/dev/null
        
        ln -sf /usr/lib/python3/dist-packages/dbus_python*.egg-info . 2>/dev/null || \
        ln -sf /usr/lib/python3*/site-packages/dbus_python*.egg-info . 2>/dev/null
        
        ln -sf /usr/lib/python3/dist-packages/gi . 2>/dev/null || \
        ln -sf /usr/lib/python3*/site-packages/gi . 2>/dev/null
        
        ln -sf /usr/lib/python3/dist-packages/PyGObject*.egg-info . 2>/dev/null || \
        ln -sf /usr/lib/python3*/site-packages/PyGObject*.egg-info . 2>/dev/null
        
        echo "软链接创建完成"
        cd - > /dev/null
    else
        echo "未找到 site-packages 目录"
    fi
else
    echo "未找到虚拟环境，如果使用虚拟环境请先激活"
fi

echo "=== 修复完成，请测试 Portal 功能 ==="
EOF

chmod +x fix_portal.sh
```

## 获取帮助

如果以上解决方案无法解决您的问题，请：

1. 运行诊断脚本收集系统信息
2. 查看详细的错误日志
3. 在项目的 GitHub Issues 中提交问题
4. 提供完整的错误信息和系统环境

更多技术支持，请参考：
- [文本注入指南](TEXT_INJECTION_GUIDE.md)
- [安装指南](INSTALL.md)
- [API 文档](API.md)