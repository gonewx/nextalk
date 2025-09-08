# NexTalk 🎙️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Build Status](https://github.com/nextalk/nextalk/workflows/Build%20and%20Release/badge.svg)](https://github.com/nextalk/nextalk/actions)
[![codecov](https://codecov.io/gh/nextalk/nextalk/branch/main/graph/badge.svg)](https://codecov.io/gh/nextalk/nextalk)

个人轻量级实时语音识别与输入系统，让您通过语音快速输入文本到任何应用程序。

## ✨ 特性

- 🎙️ **实时语音识别** - 基于 FunASR 的高精度语音识别
- ⌨️ **全局快捷键** - 自定义快捷键随时启动语音输入
- 🖱️ **智能文本注入** - 支持IME框架的原生文本注入，兼容性更好
- 🌏 **多语言IME** - 完美支持中文、日文、韩文等输入法
- 🔄 **稳定连接** - WebSocket 自动重连，确保服务稳定
- 🖥️ **系统托盘** - 最小化到系统托盘，实时显示IME状态
- 🎯 **跨应用兼容** - 支持各种文本输入场景，包括浏览器、编辑器等
- 📊 **性能优化** - 低延迟、低资源占用
- 🔧 **灵活配置** - YAML 配置文件，轻松自定义
- 🛠️ **诊断工具** - 内置IME诊断工具，快速排查问题

## 🚀 快速开始

### 系统要求

- Python 3.8+
- Windows 10/11、macOS 10.15+、Linux (Ubuntu 20.04+)
- 麦克风设备
- FunASR 语音识别服务（必需，见下方说明）

#### IME 相关要求

**Windows:**
- 建议使用管理员权限运行以获得最佳兼容性
- 支持所有 Windows 内置输入法

**macOS:**
- 需要授予辅助功能权限（系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能）
- 支持所有 macOS 输入法

**Linux:**
- 支持 IBus 和 Fcitx 输入法框架
- 需要安装 `xdotool` 和相关 DBus 库：
  ```bash
  # Ubuntu/Debian
  sudo apt install xdotool python3-dbus python3-gi
  
  # Fedora/RHEL
  sudo dnf install xdotool python3-dbus python3-gobject
  ```

### 安装方式

#### 方式一：使用预构建版本（推荐）

从 [Releases](https://github.com/nextalk/nextalk/releases) 下载对应平台的安装包：

- **Windows**: `nextalk-windows-setup.exe`
- **macOS**: `nextalk-macos.dmg`
- **Linux**: `nextalk-linux-x86_64.tar.gz`

#### 方式二：从源码安装

```bash
# 克隆仓库
git clone https://github.com/nextalk/nextalk.git
cd nextalk

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装 NexTalk
pip install -e .

# 运行
nextalk
```

#### 方式三：使用 Docker

```bash
docker pull nextalk/nextalk:latest
docker run -d \
  --name nextalk \
  --device /dev/snd \
  -v ~/.config/nextalk:/config \
  nextalk/nextalk:latest
```

## 📖 使用说明

### 启动步骤

1. **启动 FunASR 服务器**（必需）：
   ```bash
   # 首次运行会下载模型（约 2-3GB）
   python funasr_wss_server.py
   ```
   等待看到 "model loaded!" 消息

2. **启动 NexTalk**（新终端）：
   ```bash
   nextalk  # 或 python -m nextalk
   ```

### 基本操作

1. **系统托盘**：NexTalk 启动后会在系统托盘显示图标
2. **开始识别**：按下快捷键（默认 `Ctrl+Alt+Space`）
3. **语音输入**：对着麦克风说话
4. **停止识别**：再次按下快捷键
5. **查看结果**：识别文本自动输入到光标位置

### 默认快捷键

| 功能 | 快捷键 | 说明 |
|------|--------|------|
| 开始/停止识别 | `Ctrl+Alt+Space` | 切换语音识别状态 |
| 清除结果 | `Ctrl+Alt+C` | 清除当前识别结果 |
| 退出程序 | `Ctrl+Alt+Q` | 完全退出 NexTalk |

### 配置文件

配置文件位置：
- Windows: `%APPDATA%\nextalk\config.yaml`
- macOS: `~/Library/Application Support/nextalk/config.yaml`
- Linux: `~/.config/nextalk/config.yaml`

示例配置：

```yaml
# 服务器配置
server:
  host: "127.0.0.1"
  port: 10095
  ssl: false

# 音频配置
audio:
  sample_rate: 16000
  channels: 1
  chunk_size: 1024
  device: "default"  # 或指定设备名称

# 快捷键配置
hotkeys:
  start_stop: "ctrl+alt+space"
  clear: "ctrl+alt+c"
  quit: "ctrl+alt+q"

# 界面配置
ui:
  show_tray: true
  start_minimized: false
  theme: "auto"  # auto, light, dark

# IME 文本注入配置
text_injection:
  method: "ime"  # ime, keyboard, clipboard
  auto_inject: true
  inject_delay: 0.05
  format_text: true
  strip_whitespace: true

# IME 特定配置
ime:
  enabled: true
  debug_mode: false
  fallback_enabled: true
  fallback_methods: ["clipboard", "keyboard"]
  platform_specific:
    windows:
      use_unicode: true
      composition_timeout: 1.0
    macos:
      use_accessibility_api: true
      fallback_to_applescript: true
    linux:
      ime_frameworks: ["ibus", "fcitx"]
      dbus_timeout: 2.0

# 高级配置
advanced:
  auto_reconnect: true
  reconnect_interval: 5
  log_level: "INFO"
  log_file: "~/.nextalk/logs/nextalk.log"
```

## 🛠️ 开发

### 项目结构

```
nextalk/
├── audio/          # 音频采集和处理
├── config/         # 配置管理
├── core/           # 核心控制逻辑
├── input/          # 快捷键和输入处理
├── network/        # WebSocket 通信
├── output/         # 文本输出和注入（包含IME支持）
├── ui/             # 用户界面
└── utils/          # 工具函数
```

## 🔧 IME 故障排除

### 使用诊断工具

NexTalk 提供了内置的 IME 诊断工具来帮助排查问题：

```bash
# 运行完整诊断
python scripts/test_ime_injection.py --mode full

# 快速测试
python scripts/test_ime_injection.py --mode quick --text "测试文本"

# 详细模式
python scripts/test_ime_injection.py --mode full --verbose
```

### 常见问题

#### 1. 文本注入失败

**症状**: 语音识别成功，但文本没有出现在目标应用中

**解决方案**:
- 检查 IME 是否正确启用：在系统托盘菜单中查看 "IME状态"
- 尝试切换到其他输入法
- 运行诊断工具检查兼容性
- 确认目标应用支持文本输入

#### 2. 权限问题

**Windows**:
- 以管理员身份运行 NexTalk
- 检查 Windows 安全中心的应用权限设置

**macOS**:
- 系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能
- 添加 NexTalk 或终端应用到允许列表

**Linux**:
- 确保 DBus 服务正常运行
- 检查 IBus/Fcitx 是否正确配置
- 验证 xdotool 权限

#### 3. 特定应用不兼容

**症状**: 在某些应用中无法注入文本

**解决方案**:
- 启用回退模式：在配置中设置 `ime.fallback_enabled: true`
- 尝试不同的注入方法：`text_injection.method` 设置为 `keyboard` 或 `clipboard`
- 查看应用兼容性列表

#### 4. 中文输入问题

**症状**: 中文字符显示异常或无法输入

**解决方案**:
- 确保系统中文输入法已正确安装和配置
- 检查应用程序的字符编码设置
- 在配置中启用 Unicode 支持

#### 5. 系统托盘 IME 状态显示异常

**症状**: 托盘菜单中 IME 状态显示不正确

**解决方案**:
- 重启 NexTalk 应用
- 检查输入法是否正常切换
- 查看日志文件获取详细错误信息

### 获取帮助

如果问题仍然存在：

1. 运行完整诊断并保存报告：
   ```bash
   python scripts/test_ime_injection.py --mode full --verbose > ime_diagnosis.log
   ```

2. 查看日志文件：
   - Windows: `%APPDATA%\nextalk\logs\`
   - macOS: `~/Library/Logs/nextalk/`
   - Linux: `~/.local/share/nextalk/logs/`

3. 提交 Issue 时请包含：
   - 操作系统版本
   - NexTalk 版本
   - 诊断报告
   - 详细的错误描述

### 构建项目

```bash
# 安装构建依赖
pip install -r requirements-build.txt

# 运行测试
make test

# 构建可执行文件
make build

# 创建分发包
make package

# 完整发布流程
make release
```

### 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📋 路线图

- [x] 核心语音识别功能
- [x] 系统托盘集成
- [x] 跨平台支持
- [x] **IME 框架集成** - 原生输入法支持，更好的兼容性
- [x] **多语言 IME 支持** - 完美支持中文、日文、韩文输入
- [x] **诊断工具** - IME 功能诊断和故障排除工具
- [ ] 自定义语音模型
- [ ] 云端同步配置
- [ ] 插件系统
- [ ] 移动端应用
- [ ] 语音命令系统
- [ ] 实时语音转写

## 🐛 问题反馈

遇到问题？请通过以下方式反馈：

1. [GitHub Issues](https://github.com/nextalk/nextalk/issues)
2. [讨论区](https://github.com/nextalk/nextalk/discussions)
3. 邮箱：contact@nextalk.dev

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 了解详情。

## 🙏 致谢

- [FunASR](https://github.com/alibaba-damo-academy/FunASR) - 语音识别引擎
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI 框架
- [pynput](https://github.com/moses-palmer/pynput) - 输入控制
- 所有贡献者和用户

## 🔗 相关链接

- [官方网站](https://nextalk.dev)
- [文档中心](https://nextalk.dev/docs)
- [更新日志](CHANGELOG.md)
- [开发博客](https://blog.nextalk.dev)

---

<p align="center">
  Made with ❤️ by NexTalk Team
</p>