# Nextalk

**专为 Linux 设计的高性能离线语音输入应用**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)]()
[![Wayland: Supported](https://img.shields.io/badge/Wayland-Supported-green.svg)]()

简体中文 | [English](README.md)

将语音实时转换为文本，通过 Fcitx5 输入法框架输入到任意应用程序。完全离线运行，保护您的隐私。

## 特性

- **离线识别** - 基于 Sherpa-onnx 双引擎：SenseVoice 离线引擎（默认，高精度、多语言、自动标点）+ Zipformer 流式引擎（可选，边说边出字），数据不出本地
- **低延迟** - 流式引擎实时转录，文本上屏链路延迟 < 20ms
- **透明悬浮窗** - 无边框胶囊 UI，呼吸灯动画，不干扰工作流程
- **Wayland 原生支持** - 系统快捷键和文本提交均支持 Wayland
- **双语界面** - 中英双语 UI，托盘菜单即可切换
- **引擎与模型可选** - 托盘菜单热切换引擎及 Zipformer int8/standard 版本

## 快速开始

### 安装

**Ubuntu/Debian:**

```bash
# 推荐: apt 会自动安装依赖
sudo apt install ./nextalk_0.2.13-1_amd64.deb
```

> 若使用 `sudo dpkg -i` 安装，dpkg 不会解析依赖，提示缺依赖时需再执行 `sudo apt -f install` 补齐。

**Fedora/CentOS/RHEL:**

```bash
# 推荐: dnf 会自动安装依赖
sudo dnf install ./nextalk-0.2.13-1.x86_64.rpm
```

安装后 Fcitx5 会自动重启以加载插件。

**运行时依赖:**

| 依赖 | 说明 |
|------|------|
| `fcitx5` (≥ 5.0) | 必需，文本上屏通道（deb/rpm 已声明，包管理器自动安装） |
| `libgtk-3-0` / `gtk3` | 必需（包管理器自动安装） |
| PulseAudio 或 PipeWire (`pipewire-pulse`) | 音频采集，主流发行版默认自带 |
| `xdg-desktop-portal` + 桌面对应 backend | 快捷键自动注册所需（GNOME 48+/KDE 5.27+ 自带，无需手装） |
| `libayatana-appindicator3-1` / `libayatana-appindicator-gtk3` | 托盘运行库（0.2.13 起 deb/rpm 已声明，包管理器自动安装） |
| `gnome-shell-extension-appindicator` | **仅 GNOME**：显示托盘图标所需的扩展，装后需启用并重登会话（详见[常见问题](#系统托盘图标不显示-gnomefedora)）；KDE 原生支持无需安装 |

### 配置快捷键

**开箱即用（支持的桌面环境）：** 在 KDE Plasma 5.27+、GNOME 48+、Hyprland 上，应用首次启动会经 XDG Desktop Portal 自动注册全局快捷键（默认 `Super+Z`）。系统会弹出一次授权对话框，确认后立即生效，**无需进入系统设置手动配置**。

**回退（手动配置）：** 在不支持 Portal GlobalShortcuts 的环境（GNOME <48、wlroots/Sway、Ubuntu 22.04/24.04 默认会话）下，应用会静默降级到系统快捷键。此时需手动配置并绑定 `nextalk-toggle` 命令：

**GNOME:**

1. 设置 → 键盘 → 查看和自定义快捷键 → 自定义快捷键
2. 点击"添加快捷键"
3. 名称: `Nextalk 语音输入`
4. 命令: `nextalk-toggle`
5. 快捷键: 按下 `Super+Z` (推荐；`Alt+Space` 已被 GNOME 窗口菜单占用，勿用)

**KDE Plasma:**

1. 系统设置 → 快捷键 → 自定义快捷键
2. 编辑 → 新建 → 全局快捷键 → 命令/URL
3. 触发器: 设置为 `Super+Z`
4. 动作: `nextalk-toggle`

> 当前快捷键模式（Portal / 系统）会在托盘菜单中以只读项显示。

### 使用

1. **启动应用** - 从应用菜单启动 Nextalk，或运行 `nextalk`
2. **按下快捷键** - 悬浮窗出现并开始录音
3. **说话** - 实时看到识别的文字
4. **再次按下快捷键** - 停止录音，文字自动输入到当前应用
5. **或等待自动提交** - 停顿后自动提交文字

> **首次运行**: 应用会自动下载语音识别模型 (~200MB)

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--toggle` | 切换录音状态 (用于系统快捷键) |
| `audio` | 管理音频输入设备 (交互模式) |
| `audio <序号>` | 按序号直接设置音频设备 |
| `audio --list` | 列出可用设备 (机器可读格式) |
| `audio default` | 恢复系统默认设备 |
| `--help` | 显示帮助信息 |
| `--version` | 显示版本号 |

### 非 Fcitx5 环境

如果未安装 Fcitx5，应用自动使用剪贴板模式：
- 识别的文字会复制到系统剪贴板
- UI 显示"已复制到剪贴板"提示
- 手动粘贴 (`Ctrl+V`) 到目标应用

### 系统托盘

应用支持系统托盘（在支持的桌面环境中），右键菜单提供:

- 显示/隐藏窗口
- **重新连接 Fcitx5** - 输入法通道断开时手动重连
- **快捷键模式（只读）** - 显示当前生效的快捷键方式：`快捷键: Super+Z (Portal 自动注册)` 或 `快捷键: 系统设置 (nextalk-toggle)`
- 模型设置 - 切换 ASR 引擎 (SenseVoice / Zipformer) 与 Zipformer 模型版本 (int8 / 标准)
- 切换界面语言 (中文 / English)
- **音频输入设备** - 选择可用的音频输入设备
- 设置 - 打开配置目录
- 退出应用

> **注意**: GNOME 桌面需安装并启用 `gnome-shell-extension-appindicator` 扩展才会显示托盘图标（KDE 原生支持），详见[常见问题](#系统托盘图标不显示-gnomefedora)。无托盘时应用仍可通过 `nextalk --toggle` 命令使用。

## 系统要求

| 组件 | 要求 |
|------|------|
| **操作系统** | Linux (Ubuntu 22.04+ 推荐) |
| **显示服务** | X11 或 Wayland |
| **音频系统** | PulseAudio 或 PipeWire（`pipewire-pulse`） |
| **输入法** | Fcitx5 |

## 配置

### 引擎与模型设置

通过系统托盘菜单切换：

| 引擎 | 说明 |
|------|------|
| `sensevoice` (默认) | 离线引擎：VAD 分段后整段识别，精度高，自动标点，多语言 (zh/en/ja/ko/yue) |
| `zipformer` | 流式引擎：边听边识别，文字逐字出现 |

Zipformer 版本：`int8`（速度快、内存小）/ `standard`（精度更高）。

### 配置文件

高级配置: `~/.config/nextalk/settings.yaml`

```yaml
model:
  # ASR 引擎: zipformer | sensevoice
  engine: sensevoice

  zipformer:
    type: int8        # 模型版本: int8 | standard
    custom_url: ""    # 自定义模型下载地址 (留空使用默认)

  sensevoice:
    use_itn: true     # 逆文本正则化
    language: auto    # auto | zh | en | ja | ko | yue
    custom_url: ""

audio:
  input_device: "default"  # 音频输入设备: "default" 或设备名称
```

**音频设备选择:**
- 使用 `"default"` 自动选择系统默认音频设备
- 指定设备名称（如 `"Built-in Audio Analog Stereo"`）使用特定设备
- 使用 `nextalk audio` 命令或系统托盘菜单交互式选择设备

**快捷键配置:**
支持的桌面环境下经 XDG Desktop Portal 自动注册（无需配置）；否则通过桌面环境的原生设置配置，不在此配置文件中。请参阅 [配置快捷键](#配置快捷键) 章节了解设置方法。

## 从源码构建

### 前置条件

```bash
# Ubuntu/Debian
sudo apt install fcitx5 fcitx5-dev libportaudio2 portaudio19-dev cmake build-essential

# 安装 Flutter: https://flutter.dev/docs/get-started/install/linux
```

### 本地构建

```bash
# 使用 Makefile (推荐)
make build

# 或分步构建
make build-flutter    # Flutter 客户端
make build-addon      # Fcitx5 插件
```

### Docker 构建 (跨发行版兼容)

推荐使用 Docker 构建以确保跨发行版兼容性：

```bash
# 增量编译 (推荐)
make docker-build

# 重新完整编译
make docker-rebuild

# 只编译 Flutter
make docker-build-flutter

# 只编译插件
make docker-build-addon
```

### 安装插件

```bash
make install-addon          # 用户级安装
make install-addon-system   # 系统级安装 (需要 sudo)
```

### 运行

```bash
make run          # 开发模式
make run-release  # Release 版本
```

### 构建安装包

```bash
./scripts/build-pkg.sh --deb   # DEB 包
./scripts/build-pkg.sh --rpm   # RPM 包
./scripts/build-pkg.sh --all   # 全部格式
```

输出位于 `dist/` 目录。

> 📦 维护者发布新版本、CI/CD 自动化、版本管理等完整流程，请参阅 [构建与发布指南](docs/build-and-release_zh.md)。

## 卸载

**Ubuntu/Debian:**

```bash
sudo dpkg -r nextalk
```

**Fedora/CentOS/RHEL:**

```bash
sudo rpm -e nextalk
```

用户数据保留在 `~/.local/share/nextalk/`，如需完全清理请手动删除。

## 项目结构

```
nextalk/
├── voice_capsule/        # Flutter 客户端
│   └── lib/
│       ├── main.dart     # 入口
│       ├── ffi/          # FFI 绑定 (sherpa, portaudio)
│       ├── services/     # 业务逻辑
│       │   ├── asr/      # ASR 引擎抽象层
│       │   └── ...       # 其他服务
│       ├── ui/           # Widget 组件
│       └── l10n/         # 国际化
├── addons/fcitx5/        # Fcitx5 C++ 插件
├── docs/                 # 设计文档
├── scripts/              # 构建脚本
├── libs/                 # 预编译动态库
├── packaging/            # DEB/RPM 模板
└── Makefile              # 构建入口
```

详细架构设计: [docs/architecture.md](docs/architecture.md)

## 开发

```bash
make test       # 运行测试
make analyze    # 代码分析
make clean      # 清理构建
make help       # 查看所有命令
```

## 常见问题

### 系统托盘图标不显示 (GNOME/Fedora)

GNOME 桌面默认不显示 AppIndicator 托盘图标，需要安装并启用 `gnome-shell-extension-appindicator` 扩展：

```bash
# Debian/Ubuntu
sudo apt install gnome-shell-extension-appindicator

# Fedora
sudo dnf install gnome-shell-extension-appindicator
```

安装后**注销并重新登录**（Wayland 会话必须重登才能加载扩展），然后确认扩展已启用：

```bash
gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com
```

重启 Nextalk 后托盘图标即出现。KDE Plasma 原生支持托盘，无需任何配置。

不装扩展时托盘不可见，但应用功能不受影响，仍可通过命令行使用：

```bash
nextalk --toggle  # 切换录音状态
```

### 应用启动时崩溃 (段错误)

0.2.13 已修复 Fedora 上因旧版 `libappindicator` 库导致的启动段错误（托盘插件已改为优先加载 ayatana 实现）。如仍遇到托盘相关崩溃，可临时禁用托盘功能排查：

```bash
NEXTALK_NO_TRAY=1 nextalk
```

配置系统快捷键时使用（回退模式）：

```bash
nextalk-toggle
```

### 快捷键不响应

1. 确认已在系统设置中配置快捷键 (命令: `nextalk-toggle`)
2. 确认 Nextalk 应用正在运行 (检查系统托盘)
3. 测试命令行: `nextalk --toggle`

### 文字无法输入到应用

确保 Fcitx5 插件已正确安装：

```bash
ls ~/.local/lib/fcitx5/libnextalk.so
ls ~/.local/share/fcitx5/addon/nextalk.conf
fcitx5 -r  # 重启 Fcitx5
```

如果不使用 Fcitx5，应用会自动使用剪贴板模式。

### 模型下载失败

配置自定义下载地址或使用代理：

```yaml
# ~/.config/nextalk/settings.yaml
model:
  zipformer:
    custom_url: "https://your-mirror/zipformer-model.tar.bz2"
  sensevoice:
    custom_url: "https://your-mirror/sensevoice-model.tar.bz2"
```

### 音频设备问题

如果遇到 "Audio device busy" 错误（如使用 EasyEffects 时），可以选择其他音频输入设备：

**方法一: CLI 交互模式**
```bash
nextalk audio       # 进入交互模式选择设备
```

**方法二: CLI 直接选择**
```bash
nextalk audio --list  # 列出可用设备
nextalk audio 2       # 按序号选择设备
nextalk audio default # 恢复系统默认
```

**方法三: 系统托盘**
右键托盘图标 → 音频输入设备 → 从可用设备中选择

**调试命令:**
```bash
nextalk audio --list  # 查看应用检测到的设备
pactl list sources    # 系统级调试命令
```

## 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 致谢

- [Sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) - 高性能离线语音识别引擎
- [Fcitx5](https://github.com/fcitx/fcitx5) - 现代化输入法框架
- [Flutter](https://flutter.dev) - 跨平台 UI 框架

## 许可证

[MIT License](LICENSE)

---

**问题反馈**: [GitHub Issues](../../issues)
