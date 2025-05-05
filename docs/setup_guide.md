# NexTalk 安装指南

本文档提供了在Linux系统上安装和配置NexTalk的详细指南。NexTalk是一个轻量级的实时本地语音识别和输入系统，使用Whisper模型进行语音识别，并能自动将识别出的文本输入到活动窗口中。

## 系统要求

### 硬件要求
- 支持CUDA的NVIDIA GPU（推荐用于更快的语音识别）
  - 对于使用`tiny.en`或`small.en`模型，2GB显存足够
  - 对于使用`base.en`模型，建议至少4GB显存
- 或CPU（性能会较慢）
- 麦克风

### 操作系统
- Linux（已在Ubuntu 20.04+和Debian 11+上测试）
- 支持X11的窗口系统（用于文本注入功能）

### 软件依赖
- Python 3.10或更高版本
- uv包管理器（推荐）或pip
- CUDA工具包（如果使用GPU）
- 系统依赖项:
  - `xdotool`（用于文本注入）
  - `libnotify-bin`（用于桌面通知）
  - 音频库: `portaudio19-dev`, `python3-pyaudio`
- 可选依赖项:
  - FunASR库（用于中文语音识别）

## 安装步骤

### 1. 安装系统依赖

```bash
# 安装系统工具依赖
sudo apt update
sudo apt install -y xdotool libnotify-bin

# 安装音频库依赖
sudo apt install -y portaudio19-dev python3-pyaudio

# 安装Python开发工具
sudo apt install -y python3-dev python3-pip
```

### 2. 安装uv包管理器（推荐）

```bash
# 使用官方的安装脚本
curl -sSf https://install.python-poetry.org | python3 -
```

### 3. 克隆NexTalk仓库

```bash
git clone https://github.com/nextalk/nextalk.git
cd nextalk
```

### 4. 设置Python环境

使用uv（推荐）:

```bash
# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
uv sync
```

或使用pip:

```bash
# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e .
```

### 5. 安装FunASR（可选）

如果您需要更好的中文语音识别支持，可以安装FunASR库：

```bash
# 使用pip安装FunASR
pip install funasr
```

有关FunASR的更多信息，请参阅[FunASR官方文档](https://github.com/alibaba-damo-academy/FunASR)。

### 6. 配置NexTalk

NexTalk首次运行时会自动创建默认配置文件，但您也可以手动设置：

```bash
# 创建用户配置目录
mkdir -p ~/.config/nextalk

# 复制默认配置到用户目录
cp config/default_config.ini ~/.config/nextalk/config.ini
```

## 配置文件

默认配置文件位于`~/.config/nextalk/config.ini`，您可以根据需要修改以下设置：

```ini
[Client]
; 全局热键组合，用于激活/停用语音识别
hotkey=ctrl+shift+space
; 服务器WebSocket连接地址
server_url=ws://127.0.0.1:8000
; 默认语言设置
language=en
; 音频后端设置 (alsa, pulse, oss)
audio_backend=pulse

[Server]
; 默认语音识别模型
; Whisper模型选项: small.en, base.en, large-v3等
; FunASR模型选项: paraformer-zh, paraformer-zh-streaming, SenseVoiceSmall等
default_model=small.en-int8
; 语音活动检测敏感度 (0-3)
vad_sensitivity=2
; 计算设备 (cuda, cpu)
device=cuda
; 计算精度类型
compute_type=int8
; 默认语言设置 (en, zh, auto等)
language=en
; FunASR使用的VAD模型
funasr_vad_model=fsmn-vad
```

### 关键配置选项

- **hotkey**: 用于激活/停用语音识别的键盘组合
- **server_url**: 服务器WebSocket地址，默认为本地端口8000
- **audio_backend**: 音频后端，可选值包括：
  - `pulse`: 使用PulseAudio（推荐，默认值）
  - `alsa`: 使用ALSA
  - `oss`: 使用OSS
- **default_model**: 语音识别模型，可选：
  - Whisper模型: `tiny.en-int8`（最小最快）、`small.en-int8`（平衡）、`base.en-int8`（更准确）
  - FunASR模型: `paraformer-zh`（标准中文）、`paraformer-zh-streaming`（流式中文）
- **device**: 计算设备，`cuda`(GPU)或`cpu`
- **vad_sensitivity**: 语音活动检测敏感度，0-3之间的值（3最敏感）
- **language**: 默认语言，例如`en`（英语）、`zh`（中文）或`auto`（自动检测）
- **funasr_vad_model**: FunASR使用的VAD模型，默认为`fsmn-vad`

## 首次运行

### 1. 启动服务器

在一个终端窗口运行:

```bash
cd nextalk
source .venv/bin/activate
python scripts/run_server.py
```

首次运行时，NexTalk将自动下载所选Whisper模型（默认为`small.en-int8`）。这可能需要一些时间，具体取决于您的网络速度。

### 2. 启动客户端

在另一个终端窗口运行:

```bash
cd nextalk
source .venv/bin/activate
python scripts/run_client.py
```

客户端启动后，将在系统托盘显示NexTalk图标。

## 常见问题解决

### 音频设备问题

如果遇到音频设备检测问题，请确保:

- 麦克风已正确连接并设置为默认输入设备
- 用户有访问音频设备的权限: `sudo usermod -a -G audio $USER`（需要重新登录生效）
- 如果遇到ALSA相关错误（如 "ALSA lib pcm_dmix.c:1032:(snd_pcm_dmix_open) unable to open slave"），尝试修改配置文件将音频后端改为PulseAudio:
  ```ini
  [Client]
  audio_backend=pulse
  ```
- 如果PulseAudio也有问题，且您确认系统支持ALSA，可以尝试:
  ```ini
  [Client]
  audio_backend=alsa
  ```

### CUDA相关问题

如果使用GPU但遇到CUDA错误:

- 确保已安装兼容的CUDA工具包和驱动
- 检查CUDA是否正确配置: `nvcc --version`
- 如果持续出现问题，尝试切换到CPU模式，在配置文件中设置`device=cpu`

### 文本注入问题

如果语音识别正常但文本未能正确输入到活动窗口:

- 确保`xdotool`已正确安装: `which xdotool`
- 确认您的窗口系统支持X11（Wayland可能存在兼容性问题）
- 检查应用程序是否允许外部输入

## 下一步

安装完成后，请参阅[用户指南](user_guide.md)了解如何使用NexTalk的完整功能。 