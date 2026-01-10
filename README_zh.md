# Nextalk

**专为 Linux 设计的高性能离线语音输入应用**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)]()
[![Wayland: Supported](https://img.shields.io/badge/Wayland-Supported-green.svg)]()

简体中文 | [English](README.md)

将语音实时转换为文本，通过 Fcitx5 输入法框架输入到任意应用程序。完全离线运行，保护您的隐私。

## 特性

- **离线识别** - 基于 Sherpa-onnx 流式双语模型 (中/英)，数据不出本地
- **极低延迟** - 端到端延迟 < 20ms，实时转录体验
- **透明悬浮窗** - 无边框胶囊 UI，呼吸灯动画，不干扰工作流程
- **Wayland 原生支持** - 系统快捷键和文本提交均支持 Wayland
- **焦点锁定** - 录音时切换窗口，文本仍提交到原窗口
- **模型可选** - 支持 int8 (快速) / standard (高精度) 模型切换

## 快速开始

### 安装

**Ubuntu/Debian:**

```bash
sudo dpkg -i nextalk_0.1.0-1_amd64.deb
```

**Fedora/CentOS/RHEL:**

```bash
sudo rpm -i nextalk-0.1.0-1.x86_64.rpm
```

安装后 Fcitx5 会自动重启以加载插件。

### 配置快捷键

应用通过系统全局快捷键触发，需手动配置：

**GNOME:**

1. 设置 → 键盘 → 查看和自定义快捷键 → 自定义快捷键
2. 点击"添加快捷键"
3. 名称: `Nextalk 语音输入`
4. 命令: `nextalk --toggle`
5. 快捷键: 按下 `Ctrl+Alt+V` (推荐)

**KDE Plasma:**

1. 系统设置 → 快捷键 → 自定义快捷键
2. 编辑 → 新建 → 全局快捷键 → 命令/URL
3. 触发器: 设置为 `Ctrl+Alt+V`
4. 动作: `nextalk --toggle`

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

### 非 Fcitx5 环境

如果未安装 Fcitx5，应用自动使用剪贴板模式：
- 识别的文字会复制到系统剪贴板
- UI 显示"已复制到剪贴板"提示
- 手动粘贴 (`Ctrl+V`) 到目标应用

### 系统托盘

应用支持系统托盘（在支持的桌面环境中），右键菜单提供:

- 显示/隐藏窗口
- 切换模型版本
- 打开配置目录
- 退出应用

> **注意**: GNOME 桌面不显示托盘图标是正常的，应用仍可通过 `nextalk --toggle` 命令使用。

## 系统要求

| 组件 | 要求 |
|------|------|
| **操作系统** | Linux (Ubuntu 22.04+ 推荐) |
| **显示服务** | X11 或 Wayland |
| **音频系统** | ALSA 或 PulseAudio |
| **输入法** | Fcitx5 |

## 配置

### 模型设置

通过系统托盘菜单切换：

| 版本 | 说明 |
|------|------|
| `int8` | 量化版本，速度快，内存占用小 (默认) |
| `standard` | 标准版本，识别精度更高 |

### 配置文件

高级配置: `~/.config/nextalk/settings.yaml`

```yaml
model:
  custom_url: ""    # 自定义模型下载地址
  type: int8        # 模型版本: int8 | standard

hotkey:
  key: v            # 主键 (仅供显示，实际由系统快捷键控制)
  modifiers:        # 修饰键
    - ctrl
    - alt
```

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

GNOME 桌面默认不显示系统托盘图标，这是正常现象。应用仍可通过命令行正常使用：

```bash
nextalk --toggle  # 切换录音状态
```

> **⚠️ 注意**: 不建议安装 AppIndicator 扩展，可能导致应用崩溃。如果已安装且出现崩溃，请参考下一节。

### 应用启动时崩溃 (段错误)

如果安装了 AppIndicator 扩展后应用崩溃，可禁用托盘功能：

```bash
NEXTALK_NO_TRAY=1 nextalk
```

配置系统快捷键时使用：

```bash
env NEXTALK_NO_TRAY=1 /opt/nextalk/nextalk --toggle
```

### 快捷键不响应

1. 确认已在系统设置中配置快捷键 (命令: `nextalk --toggle`)
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
  custom_url: "https://your-mirror/model.tar.bz2"
```

### 音频设备问题

```bash
pactl list sources  # 检查麦克风设备
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
