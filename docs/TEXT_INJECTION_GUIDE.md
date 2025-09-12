# NexTalk 文本注入系统指南

## 概述

NexTalk 采用现代化的文本注入架构，基于Portal+XDoTool双重策略，为Linux环境提供最佳的文本注入体验。系统能够自动检测运行环境并智能选择最适合的注入方法。

## 架构设计

### 注入策略层次

```
┌─────────────────────────────────────┐
│         InjectionFactory            │  策略工厂
│    (自动环境检测与策略选择)          │
└─────────────┬───────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────┐         ┌────▼──────┐
│ Portal │         │ XDoTool   │  具体注入器
│ 注入器  │         │ 注入器     │
└────────┘         └───────────┘
```

### 核心组件

1. **InjectionFactory**: 策略工厂，负责环境检测和注入器选择
2. **PortalInjector**: 使用XDG Desktop Portal进行文本注入
3. **XDoToolInjector**: 使用xdotool进行传统X11注入
4. **EnvironmentDetector**: 环境检测器，识别Wayland/X11等环境

## 注入方法详解

### Portal 注入 (推荐)

Portal注入是现代Linux桌面环境的标准方法，通过XDG Desktop Portal API实现：

**优势:**
- 原生Wayland支持
- 更好的安全性和权限控制
- 与桌面环境深度集成
- 支持现代应用程序

**工作原理:**
1. 通过DBus连接到`org.freedesktop.portal.Desktop`
2. 使用RemoteDesktop portal获取输入权限
3. 调用KeyboardInject方法进行文本注入

**适用环境:**
- GNOME (Wayland/X11)
- KDE Plasma (Wayland/X11)
- 其他支持XDG Portal的桌面环境

### XDoTool 注入 (回退方案)

XDoTool是传统的X11文本注入方法：

**优势:**
- 成熟稳定，兼容性好
- 支持所有X11应用程序
- 配置简单，依赖较少

**工作原理:**
1. 使用xdotool命令行工具
2. 直接向X11窗口发送键盘事件
3. 支持Unicode和特殊字符

**适用环境:**
- 传统X11桌面环境
- 不支持Portal的应用程序
- Portal注入失败时的回退方案

## 环境检测逻辑

系统启动时会自动检测运行环境：

```python
# 检测顺序
1. 检查Wayland环境 ($WAYLAND_DISPLAY)
2. 检查X11环境 ($DISPLAY)
3. 检测Portal服务可用性
4. 检查xdotool工具可用性
5. 选择最佳注入策略
```

### 检测结果示例

| 环境 | Portal可用 | XDoTool可用 | 选择策略 |
|------|------------|-------------|----------|
| Wayland + GNOME | ✓ | ✓ | Portal优先 |
| X11 + KDE | ✓ | ✓ | Portal优先 |
| X11 + i3wm | ✗ | ✓ | XDoTool only |
| Wayland (旧版) | ✗ | ✗ | 错误状态 |

## 配置选项

### 基础配置

```yaml
text_injection:
  # 自动注入识别结果
  auto_inject: true
  
  # 注入延迟(秒) - 给目标应用准备时间
  inject_delay: 0.1
  
  # 首选注入方法
  preferred_method: "auto"  # auto, portal, xdotool
  
  # 启用回退机制
  fallback_enabled: true
```

### 高级配置

```yaml
text_injection:
  # Portal特定配置
  portal_timeout: 30.0
  portal_retry_attempts: 3
  
  # XDoTool特定配置
  xdotool_delay: 0.02      # 按键间隔
  xdotool_retry_attempts: 3
  
  # 通用重试配置
  retry_delay: 0.5
  max_retry_attempts: 3
```

### 策略选择配置

```yaml
text_injection:
  # 策略选择模式
  selection_strategy: "auto"  # auto, prefer_portal, prefer_xdotool, portal_only, xdotool_only
  
  # 环境特定覆盖
  environment_overrides:
    wayland: "portal_only"
    x11: "prefer_portal"
```

## 故障排除

### 常见问题

#### 1. Portal注入失败 - 虚拟环境依赖问题

**症状:** 在Wayland环境下Portal机制不工作，系统回退到xdotool

**根本原因:** 虚拟环境中缺失D-Bus Python绑定

**诊断步骤:**
```bash
# 检查dbus模块是否可导入
python -c "
try:
    import dbus
    print('✓ dbus模块可用')
except ImportError as e:
    print('✗ dbus模块不可用:', e)
"

# 检查环境检测结果
python -c "
from nextalk.output.environment_detector import EnvironmentDetector
detector = EnvironmentDetector()
env = detector.detect_environment()
print(f'Portal available: {env.portal_available}')
print(f'Display server: {env.display_server.value}')
print(f'Recommended method: {env.recommended_method.value}')
"
```

**解决方案:**
```bash
# 1. 确认系统已安装必要包
sudo apt install python3-dbus python3-gi

# 2. 在项目根目录执行软链接命令
cd .venv/lib/python3.*/site-packages
ln -sf /usr/lib/python3/dist-packages/dbus .
ln -sf /usr/lib/python3/dist-packages/_dbus_bindings.* .
ln -sf /usr/lib/python3/dist-packages/_dbus_glib_bindings.* .
ln -sf /usr/lib/python3/dist-packages/dbus_python*.egg-info .
ln -sf /usr/lib/python3/dist-packages/gi .
ln -sf /usr/lib/python3/dist-packages/PyGObject*.egg-info .

# 3. 验证修复
python -c "
from nextalk.output.text_injector import TextInjector
import asyncio

async def test():
    injector = TextInjector()
    success = await injector.initialize()
    if success:
        status = await injector.get_ime_status()
        print(f'✓ Active method: {status.get(\"active_method\")}')
        if status.get('active_method') == 'portal':
            print('✓ Portal机制工作正常!')
    await injector.cleanup()

asyncio.run(test())
"
```

**验证成功标志:**
- `Portal available: True`
- `Active method: portal` (在Wayland环境下)
- Portal会话能够正常建立并获得键盘权限

#### 2. Portal服务问题

**症状:** 即使依赖正常但Portal仍无法使用

**诊断步骤:**
```bash
# 检查Portal服务状态
systemctl --user status xdg-desktop-portal

# 检查Portal接口
busctl --user list | grep portal

# 测试Portal权限
python -c "
import dbus
bus = dbus.SessionBus()
proxy = bus.get_object('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop')
print('Portal服务可用')
"
```

**解决方案:**
- 重启Portal服务: `systemctl --user restart xdg-desktop-portal`
- 检查桌面环境Portal支持
- 切换到xdotool回退模式

#### 3. XDoTool注入失败

**症状:** 在X11环境下无法注入文本

**诊断步骤:**
```bash
# 检查xdotool安装
which xdotool

# 测试xdotool功能
xdotool type "test"

# 检查X11权限
echo $DISPLAY
xhost +local:
```

**解决方案:**
- 安装xdotool: `sudo apt install xdotool`
- 设置X11权限: `xhost +local:`
- 检查目标应用X11兼容性

#### 4. 环境检测错误

**症状:** 系统选择了错误的注入方法

**诊断步骤:**
```bash
# 运行环境检测
python -c "
from nextalk.output.environment_detector import detect_environment
print(detect_environment())
"

# 查看检测日志
python debug_inject.py
```

**解决方案:**
- 手动指定注入方法
- 检查环境变量设置
- 更新配置文件

### 性能优化

#### 注入延迟调优

```yaml
# 快速注入 (可能不稳定)
text_injection:
  inject_delay: 0.05
  xdotool_delay: 0.01
  
# 标准注入 (推荐)
text_injection:
  inject_delay: 0.1
  xdotool_delay: 0.02
  
# 稳定注入 (兼容性最好)
text_injection:
  inject_delay: 0.2
  xdotool_delay: 0.05
```

#### 重试策略优化

```yaml
# 快速失败模式
text_injection:
  retry_attempts: 1
  retry_delay: 0.1
  
# 平衡模式 (推荐)
text_injection:
  retry_attempts: 3
  retry_delay: 0.5
  
# 顽强模式
text_injection:
  retry_attempts: 5
  retry_delay: 1.0
```

## 开发者指南

### 添加新的注入器

1. 继承BaseInjector类
2. 实现必要的抽象方法
3. 在InjectionFactory中注册
4. 添加对应的环境检测逻辑

### 示例代码

```python
from nextalk.output.base_injector import BaseInjector
from nextalk.output.injection_models import InjectionResult

class CustomInjector(BaseInjector):
    async def inject_text(self, text: str) -> InjectionResult:
        # 实现自定义注入逻辑
        pass
    
    async def initialize(self) -> bool:
        # 实现初始化逻辑
        pass
```

### 调试技巧

```python
# 启用详细日志
import logging
logging.getLogger('nextalk.output').setLevel(logging.DEBUG)

# 使用调试脚本
python debug_inject.py --verbose

# 监控注入性能
python -c "
from nextalk.output.injection_factory import get_injection_factory
factory = get_injection_factory()
print(factory.get_statistics())
"
```

## 兼容性列表

### 已测试的桌面环境

| 桌面环境 | Wayland | X11 | Portal | XDoTool | 状态 |
|----------|---------|-----|---------|---------|------|
| GNOME 40+ | ✓ | ✓ | ✓ | ✓ | 完全支持 |
| KDE Plasma 5.24+ | ✓ | ✓ | ✓ | ✓ | 完全支持 |
| Sway | ✓ | - | ✓ | - | Portal only |
| i3wm | - | ✓ | ✗ | ✓ | XDoTool only |
| XFCE | - | ✓ | 部分 | ✓ | 主要XDoTool |

### 已测试的应用程序

| 应用程序 | Portal | XDoTool | 备注 |
|----------|---------|---------|------|
| Firefox | ✓ | ✓ | 完全支持 |
| Chrome/Chromium | ✓ | ✓ | 完全支持 |
| VSCode | ✓ | ✓ | 完全支持 |
| Terminal | ✓ | ✓ | 完全支持 |
| LibreOffice | ✓ | ✓ | 完全支持 |
| Electron Apps | ✓ | ✓ | 大部分支持 |

## 更新日志

### v0.1.0
- 初始Portal+XDoTool架构实现
- 自动环境检测功能
- 基础回退机制

### 未来计划
- Windows和macOS平台支持
- 更多注入方法集成
- 性能监控和优化
- 应用程序特定优化