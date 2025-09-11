# NexTalk 🎙️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Build Status](https://github.com/nextalk/nextalk/workflows/Build%20and%20Release/badge.svg)](https://github.com/nextalk/nextalk/actions)
[![codecov](https://codecov.io/gh/nextalk/nextalk/branch/main/graph/badge.svg)](https://codecov.io/gh/nextalk/nextalk)

个人轻量级实时语音识别与输入系统，让您通过语音快速输入文本到任何应用程序。

## ✨ 特性

- 🎙️ **实时语音识别** - 基于 FunASR 的高精度语音识别
- ⌨️ **全局快捷键** - 自定义快捷键随时启动语音输入
- 🖱️ **智能文本注入** - 基于Portal+XDoTool的现代化文本注入系统，兼容性更好
- 🌏 **跨平台支持** - 支持Linux Wayland/X11环境的自动适配
- 🔄 **稳定连接** - WebSocket 自动重连，确保服务稳定
- 🖥️ **系统托盘** - 最小化到系统托盘，实时显示识别状态
- 🎯 **跨应用兼容** - 支持各种文本输入场景，包括浏览器、编辑器等
- 📊 **性能优化** - 低延迟、低资源占用
- 🔧 **灵活配置** - YAML 配置文件，轻松自定义
- 🛠️ **诊断工具** - 内置文本注入诊断工具，快速排查问题

## 🚀 快速开始

### 系统要求

- Python 3.8+
- Windows 10/11、macOS 10.15+、Linux (Ubuntu 20.04+)
- 麦克风设备
- FunASR 语音识别服务（必需，见下方说明）

#### 文本注入系统要求

**Linux 主要支持:**
- 支持 Wayland 和 X11 显示服务器
- 自动Portal或XDoTool注入方式
- 需要安装基本依赖：
  ```bash
  # Ubuntu/Debian
  sudo apt install xdotool python3-dbus python3-gi
  
  # Fedora/RHEL
  sudo dnf install xdotool python3-dbus python3-gobject
  ```

**Windows 和 macOS:**
- 基础文本注入支持（通过pyautogui）
- 建议使用管理员权限获得最佳兼容性

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

# 现代化文本注入配置
text_injection:
  auto_inject: true
  inject_delay: 0.1
  preferred_method: "auto"  # auto, portal, xdotool
  fallback_enabled: true
  portal_timeout: 30.0
  xdotool_delay: 0.02
  retry_attempts: 3
  retry_delay: 0.5

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
├── output/         # 文本输出和注入（Portal+XDoTool系统）
├── ui/             # 用户界面
└── utils/          # 工具函数
```

## 🔧 文本注入故障排除

### 使用诊断工具

NexTalk 提供了内置的文本注入诊断工具来帮助排查问题：

```bash
# 运行完整诊断
python debug_inject.py

# 测试特定文本
echo "测试文本" | python debug_inject.py
```

### 常见问题

#### 1. 文本注入失败

**症状**: 语音识别成功，但文本没有出现在目标应用中

**解决方案**:
- 检查当前注入方法：查看日志中的注入策略选择
- 尝试手动切换注入方法：配置中设置 `preferred_method: "xdotool"` 或 `"portal"`
- 运行诊断工具检查兼容性
- 确认目标应用支持文本输入

#### 2. Linux环境问题

**Wayland环境**:
- 确保Portal服务正常运行：`systemctl --user status xdg-desktop-portal`
- 检查权限：某些应用可能需要特殊权限

**X11环境**:
- 确认xdotool已安装：`which xdotool`
- 检查X11权限：`xhost +local:`

#### 3. 特定应用不兼容

**症状**: 在某些应用中无法注入文本

**解决方案**:
- 启用回退机制：确保配置中 `fallback_enabled: true`
- 增加注入延迟：调整 `inject_delay` 参数
- 查看应用兼容性和日志输出

#### 4. 性能问题

**症状**: 文本注入速度慢或延迟高

**解决方案**:
- 减少重试延迟：调整 `retry_delay` 和 `xdotool_delay`
- 检查系统负载和资源占用
- 考虑切换到更快的注入方法

### 获取帮助

如果问题仍然存在：

1. 运行诊断并保存日志：
   ```bash
   python debug_inject.py > injection_diagnosis.log 2>&1
   ```

2. 查看详细日志：
   - 配置中设置 `log_level: "DEBUG"`
   - 检查日志文件中的注入相关错误

3. 提交 Issue 时请包含：
   - 操作系统版本和桌面环境
   - NexTalk 版本
   - 诊断报告和日志
   - 目标应用信息

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
- [x] **Portal+XDoTool 注入系统** - 现代化文本注入架构，更好的兼容性
- [x] **环境自动检测** - 智能检测Wayland/X11环境并选择最佳注入方式
- [x] **诊断工具** - 文本注入功能诊断和故障排除工具
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