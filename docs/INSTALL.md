# NexTalk 安装指南

## 依赖文件说明

项目包含多个依赖文件，根据您的需求选择安装：

| 文件 | 用途 | 何时需要 |
|------|------|----------|
| `requirements.txt` | 核心运行时依赖 | **必需** - NexTalk 客户端基础功能 |
| `requirements-gui.txt` | GUI 依赖 | 需要系统托盘图标时 |
| `requirements-server.txt` | FunASR 服务器依赖 | 运行语音识别服务器时 |
| `requirements-dev.txt` | 开发工具 | 开发和测试时 |
| `requirements-build.txt` | 构建工具 | 打包可执行文件时 |

## 安装方式

### 1. 最小化安装（仅客户端）

```bash
# 只安装核心依赖
pip install -r requirements.txt
```

适用于：
- 连接到远程 FunASR 服务器
- 不需要 GUI 界面
- 命令行使用

### 2. 标准安装（推荐）

```bash
# 安装核心依赖和 GUI
pip install -r requirements-gui.txt
```

适用于：
- 本地使用
- 需要系统托盘
- 日常使用

### 3. 完整安装（包含服务器）

```bash
# 安装所有运行时依赖
pip install -r requirements.txt
pip install -r requirements-server.txt
pip install -r requirements-gui.txt
```

或使用 uv 加速安装：

```bash
# 使用 uv（更快）
uv pip install -r requirements.txt
uv pip install -r requirements-server.txt
uv pip install -r requirements-gui.txt
```

适用于：
- 本地运行完整系统
- 不依赖外部服务器
- 开发和测试

### 4. 开发环境

```bash
# 安装所有依赖
pip install -r requirements.txt
pip install -r requirements-gui.txt
pip install -r requirements-dev.txt
pip install -r requirements-build.txt

# 安装为开发模式
pip install -e .
```

## 使用 uv 安装（推荐）

[uv](https://github.com/astral-sh/uv) 是一个快速的 Python 包管理器：

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv

# 使用 uv 安装依赖
uv pip install -r requirements.txt
```

## 使用 conda 安装

```bash
# 创建 conda 环境
conda create -n nextalk python=3.10
conda activate nextalk

# 安装依赖
pip install -r requirements.txt
```

## 系统特定说明

### Windows

```bash
# 可能需要安装 Visual C++ 构建工具
# 下载：https://visualstudio.microsoft.com/visual-cpp-build-tools/

# 安装依赖
pip install -r requirements.txt
```

### macOS

```bash
# 安装 Xcode 命令行工具（如果需要）
xcode-select --install

# 安装 PortAudio（音频支持）
brew install portaudio

# 安装依赖
pip install -r requirements.txt
```

### Linux (Ubuntu/Debian)

```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    python3-dev \
    portaudio19-dev \
    python3-tk \
    python3-pyaudio \
    python3-dbus \
    python3-gi \
    libgirepository-2.0-dev \
    libcairo2-dev \
    pkg-config \
    ffmpeg \
    libayatana-appindicator3-dev　\
    gir1.2-ayatanaappindicator3-0.1　\
    xdotool

# 安装 Python 依赖
pip install -r requirements.txt

### Linux (Fedora/RHEL)

```bash
# 安装系统依赖
sudo dnf install -y \
    gcc \
    gcc-c++ \
    make \
    python3-devel \
    portaudio-devel \
    python3-tkinter \
    python3-dbus \
    python3-gobject \
    gobject-introspection-devel \
    cairo-devel \
    pkgconfig \
    xdotool

# 安装 Python 依赖
pip install -r requirements.txt


## 故障排除

### 问题：`ssl` 模块安装失败

**原因**：`ssl` 是 Python 内置模块，不需要安装。

**解决**：使用更新后的 `requirements.txt` 文件。

### 问题：PyQt6 安装失败

**解决**：
```bash
# 尝试单独安装
pip install PyQt6 --upgrade

# 或跳过 GUI 依赖
pip install -r requirements.txt  # 仅安装核心依赖
```

### 问题：PyAudio 编译失败

**症状**：安装 GUI 依赖时出现 `error: command 'cc' failed: No such file or directory`

**原因**：缺少 C 编译器和相关构建工具

**解决**：
```bash
# Ubuntu/Debian
sudo apt install build-essential python3-dev portaudio19-dev

# Fedora/RHEL
sudo dnf install gcc gcc-c++ make python3-devel portaudio-devel

# 然后重试安装
uv pip install -r requirements-gui.txt
```

### 问题：sounddevice 安装失败

**解决**：
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev

# macOS
brew install portaudio

# 然后重试
pip install sounddevice
```

### 问题：pynput 在 Linux 上不工作

**解决**：
```bash
# 确保在 X11 环境下
echo $DISPLAY  # 应该显示 :0 或类似值

# 安装必要的库
sudo apt-get install python3-xlib

# 如果仍有权限问题，添加 X11 权限
xhost +local:
```

**运行应用**：
```bash
# 在授权 X11 权限后运行 NexTalk
xhost +local:
python -m nextalk -c config/nextalk.yaml
```

### 问题：PyGObject 安装失败

**症状**：安装 GUI 依赖时出现 `ERROR: Dependency 'girepository-2.0' is required but not found`

**原因**：缺少 girepository-2.0 开发包

**解决**：
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y libgirepository-2.0-dev libcairo2-dev pkg-config python3-dev

# Fedora/RHEL
sudo dnf install -y gobject-introspection-devel cairo-devel pkgconfig python3-devel

# 然后重试安装 PyGObject
uv pip install pycairo PyGObject
# 或
pip install pycairo PyGObject
```

### 问题：Portal 文本注入不工作

**症状**：在 Wayland 环境下文本注入失败，系统回退到 xdotool

**解决**：
```bash
# 1. 确认已安装必要的系统包
sudo apt install python3-dbus python3-gi  # Ubuntu/Debian
# 或
sudo dnf install python3-dbus python3-gobject  # Fedora/RHEL
```

**详细解决步骤**：请参考 [文本注入指南](docs/TEXT_INJECTION_GUIDE.md) 中的故障排除部分。

## 验证安装

安装完成后，运行验证脚本：

```bash
python scripts/verify_installation.py
```

应该看到所有核心依赖都已正确安装。

## 快捷键支持（Wayland 环境）

在 Wayland 环境下，系统全局热键可能无法正常工作。项目提供了 `toggle_recording.py` 脚本作为替代方案：

### 使用方法

```bash
# 直接运行切换录音状态
python toggle_recording.py
```

### 功能说明

- **智能切换**：如果 NexTalk 已运行，发送切换信号；否则自动启动应用
- **进程检测**：自动查找运行中的 NexTalk 进程
- **依赖检查**：启动前检查 FunASR 服务器是否运行

### 系统集成

可以将此脚本绑定到系统快捷键：

#### GNOME (Ubuntu/Fedora)
```bash
# 打开设置 -> 键盘 -> 查看和自定义快捷键 -> 自定义快捷键
# 添加新快捷键：
# 名称：NexTalk 切换
# 命令：python /path/to/nextalk/toggle_recording.py
# 快捷键：Ctrl+Shift+Space
```

#### KDE
```bash
# 系统设置 -> 快捷键 -> 自定义快捷键 -> 编辑 -> 新建 -> 全局快捷键 -> 命令/URL
# 触发器：Ctrl+Shift+Space
# 动作：python /path/to/nextalk/toggle_recording.py
```

### 注意事项

- 确保脚本路径正确
- FunASR 服务器必须先启动
- 脚本会在后台启动 NexTalk（无控制台输出）

## 卸载

```bash
# 卸载 NexTalk
pip uninstall nextalk

# 卸载所有依赖
pip uninstall -r requirements.txt -y
```

## 更多帮助

如果遇到问题：
1. 查看 [故障排除文档](docs/TROUBLESHOOTING.md)
2. 提交 [Issue](https://github.com/nextalk/nextalk/issues)
3. 查看 [讨论区](https://github.com/nextalk/nextalk/discussions)