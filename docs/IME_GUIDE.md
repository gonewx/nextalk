# IME 配置指南

本文档提供了 NexTalk IME (输入法编辑器) 功能的详细配置指南和使用说明。

## 概述

NexTalk v3 引入了基于 IME 框架的文本注入功能，通过直接集成操作系统的输入法引擎来实现更稳定、更自然的文本输入体验。这一功能完全替代了之前的键盘模拟和剪贴板粘贴方法。

## 支持的平台和输入法

### Windows

- **支持的输入法**: 所有 Windows 内置输入法
- **技术实现**: Windows Text Services Framework (TSF)
- **常见输入法**:
  - 微软拼音
  - 搜狗输入法
  - QQ输入法
  - 百度输入法

### macOS

- **支持的输入法**: 所有 macOS 输入法
- **技术实现**: macOS Input Method Kit + AppleScript 回退
- **常见输入法**:
  - 系统拼音
  - 搜狗输入法 for Mac
  - 百度输入法 for Mac

### Linux

- **支持的框架**: IBus、Fcitx
- **技术实现**: DBus 接口 + X11 事件
- **常见输入法**:
  - IBus Pinyin
  - Fcitx Pinyin
  - Rime 输入法

## 配置文件详解

### 基础配置

```yaml
# 文本注入方式配置
text_injection:
  method: "ime"              # 使用 IME 方式注入
  auto_inject: true          # 自动注入识别结果
  inject_delay: 0.05         # 注入延迟(秒)
  format_text: true          # 格式化文本
  strip_whitespace: true     # 去除首尾空白

# IME 核心配置
ime:
  enabled: true              # 启用 IME 功能
  debug_mode: false          # 调试模式(开发用)
  fallback_enabled: true     # 启用回退机制
  fallback_methods: ["clipboard", "keyboard"]  # 回退方法顺序
```

### 平台特定配置

#### Windows 平台

```yaml
ime:
  platform_specific:
    windows:
      use_unicode: true           # 使用 Unicode 编码
      composition_timeout: 1.0    # 组合超时时间
      allow_clipboard_fallback: true  # 允许剪贴板回退
```

#### macOS 平台

```yaml
ime:
  platform_specific:
    macos:
      use_accessibility_api: true      # 使用辅助功能 API
      fallback_to_applescript: true    # AppleScript 回退
      composition_timeout: 1.0         # 组合超时时间
```

#### Linux 平台

```yaml
ime:
  platform_specific:
    linux:
      ime_frameworks: ["ibus", "fcitx"]  # 支持的框架
      dbus_timeout: 2.0                  # DBus 超时时间
      debug_mode: false                  # DBus 调试模式
```

## 高级配置选项

### 文本处理优化

```yaml
text_processing:
  format_text: true                    # 启用文本格式化
  strip_whitespace: true               # 去除多余空白
  normalize_punctuation: true          # 标准化标点符号
  segment_mixed_text: true             # 分段处理混合文本
  
  # CJK 文本处理
  cjk_optimization:
    optimize_spacing: true             # 优化 CJK 间距
    normalize_chinese_punctuation: true # 中文标点标准化
    handle_mixed_languages: true       # 混合语言处理
```

### 状态监控配置

```yaml
ime_monitoring:
  monitor_interval: 0.1               # 监控间隔(秒)
  focus_change_debounce: 0.05         # 焦点变化去抖动
  ime_state_debounce: 0.02            # IME 状态去抖动
  enable_composition_monitoring: true  # 启用组合监控
  enable_focus_monitoring: true       # 启用焦点监控
```

## 权限设置

### Windows

1. **管理员权限** (推荐):
   - 右键 NexTalk 程序，选择"以管理员身份运行"
   - 或在快捷方式属性中设置始终以管理员身份运行

2. **Windows 安全中心**:
   - 打开 Windows 安全中心
   - 转到"应用和浏览器控制"
   - 确保 NexTalk 不被阻止

### macOS

1. **辅助功能权限** (必需):
   ```
   系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能
   ```
   - 点击锁图标解锁
   - 添加 NexTalk 或运行 NexTalk 的终端应用

2. **输入监控权限** (可选):
   ```
   系统偏好设置 → 安全性与隐私 → 隐私 → 输入监控
   ```

### Linux

1. **安装依赖包**:
   ```bash
   # Ubuntu/Debian
   sudo apt install xdotool python3-dbus python3-gi
   
   # Fedora/RHEL
   sudo dnf install xdotool python3-dbus python3-gobject
   
   # Arch Linux
   sudo pacman -S xdotool python-dbus python-gobject
   ```

2. **DBus 权限**:
   - 确保用户在 `audio` 和 `input` 组中
   - 检查 DBus 会话服务是否正常运行

## 故障排除

### 使用诊断工具

NexTalk 提供了专门的 IME 诊断工具：

```bash
# 完整诊断
python scripts/test_ime_injection.py --mode full

# 快速测试
python scripts/test_ime_injection.py --mode quick

# 详细输出
python scripts/test_ime_injection.py --mode full --verbose
```

### 常见问题和解决方案

#### 1. IME 初始化失败

**原因**: 缺少必要的系统库或权限不足

**解决方案**:
- Windows: 以管理员身份运行
- macOS: 检查辅助功能权限
- Linux: 安装必要的依赖包

#### 2. 文本注入失败

**原因**: 目标应用不兼容或 IME 状态异常

**解决方案**:
- 检查输入法是否正确激活
- 尝试在不同的应用中测试
- 启用回退模式

#### 3. 中文字符显示异常

**原因**: 字符编码问题或输入法配置错误

**解决方案**:
- 确保系统中文输入法正确安装
- 检查应用程序的字符编码设置
- 在配置中启用 Unicode 支持

#### 4. 特定应用兼容性问题

**已知兼容应用**:
- 文本编辑器: Notepad, VS Code, Sublime Text, Vim
- 浏览器: Chrome, Firefox, Edge, Safari
- 办公软件: Microsoft Office, LibreOffice
- 终端: Windows Terminal, iTerm2, GNOME Terminal

**不兼容应用**:
- 某些游戏内聊天框
- 部分旧版本软件
- 使用自定义输入框的应用

**解决方案**:
- 启用回退模式
- 尝试不同的注入方法
- 联系应用开发者改进兼容性

## 性能优化

### 减少延迟

```yaml
ime:
  performance:
    injection_delay: 0.01      # 降低注入延迟
    monitoring_interval: 0.05   # 减少监控间隔
    cache_ime_status: true      # 缓存 IME 状态
```

### 减少资源占用

```yaml
ime:
  performance:
    disable_composition_monitoring: true  # 禁用组合监控
    reduce_status_checks: true           # 减少状态检查
    lazy_initialization: true            # 延迟初始化
```

## API 参考

### IME 状态查询

```python
from nextalk.output.ime_manager import IMEManager

# 创建 IME 管理器
ime_manager = IMEManager(config)
await ime_manager.initialize()

# 获取 IME 状态
status = await ime_manager.get_ime_status()
print(f"当前 IME: {status.current_ime}")
print(f"是否活跃: {status.is_active}")

# 检测活跃的 IME
ime_info = await ime_manager.detect_active_ime()
if ime_info:
    print(f"IME 名称: {ime_info.name}")
    print(f"框架: {ime_info.framework}")
    print(f"语言: {ime_info.language}")
```

### 文本注入

```python
# 注入文本
result = await ime_manager.inject_text("你好，世界！")
if result.success:
    print(f"注入成功，用时: {result.injection_time:.3f}s")
else:
    print(f"注入失败: {result.error}")
```

### 状态监控

```python
from nextalk.output.ime_monitor import IMEStateMonitorManager

# 创建监控器
monitor = IMEStateMonitorManager(ime_manager, config)

# 注册事件处理器
def handle_ime_change(event, data):
    print(f"IME 状态改变: {data['new_status'].current_ime}")

monitor.add_event_handler(MonitorEvent.IME_STATUS_CHANGED, handle_ime_change)

# 启动监控
await monitor.start()
```

## 最佳实践

1. **始终启用回退模式**: 确保在 IME 不可用时有替代方案
2. **定期运行诊断**: 使用内置诊断工具检查系统状态
3. **合理配置延迟**: 根据系统性能调整注入延迟
4. **监控日志**: 定期查看日志文件排查潜在问题
5. **测试兼容性**: 在主要使用的应用中测试 IME 功能

## 升级和迁移

从旧版本升级到支持 IME 的版本时：

1. **备份配置文件**: 升级前备份现有配置
2. **更新配置格式**: 添加 IME 相关配置项
3. **测试功能**: 使用诊断工具验证 IME 功能
4. **调整设置**: 根据实际使用情况调整配置

## 开发者信息

### 扩展 IME 支持

如需为新平台或输入法添加支持：

1. 继承 `IMEAdapter` 基类
2. 实现必要的抽象方法
3. 在 `IMEManager` 中注册新适配器
4. 添加相应的配置选项
5. 编写单元测试和集成测试

### 贡献代码

欢迎为 IME 功能贡献代码：

1. Fork 项目并创建分支
2. 实现新功能或修复 Bug
3. 添加测试用例
4. 更新文档
5. 提交 Pull Request

---

更多信息请参考：
- [项目主页](../README.md)
- [API 文档](API.md)
- [问题反馈](https://github.com/nextalk/nextalk/issues)