# NexTalk 安装指南

本文档提供了在Linux系统上安装和配置NexTalk的详细指南。NexTalk是一个轻量级的实时本地语音识别和输入系统，使用FunASR模型进行语音识别，并能自动将识别出的文本输入到活动窗口中。

## 系统要求

### 硬件要求
- 支持CUDA的NVIDIA GPU（推荐用于更快的语音识别）。所需显存取决于具体 FunASR 模型：
  - 小型模型 (如 FunASR SenseVoice): 可能 2-4GB 显存即可。
  - 中型模型 (如 FunASR Paraformer标准版): 建议至少 4-6GB 显存。
  - 大型模型: 可能需要 8GB 或更多显存。
- 或 CPU（对于大多数 FunASR 模型，CPU 推理性能会显著慢于 GPU）。
- 麦克风。

### 操作系统
- Linux（已在Ubuntu 20.04+和Debian 11+上测试）。
- 支持X11的窗口系统（客户端的 `xdotool` 文本注入功能需要）。

### 软件依赖
- Python 3.10 或更高版本。
- `pip` 或 推荐的 `uv` 包管理器。
- FunASR 核心库 (`funasr`) 及其依赖 (包括 PyTorch 等)。
- CUDA 工具包 (如果使用 GPU，版本需与 PyTorch 和 FunASR 兼容)。
- 系统依赖项:
  - `xdotool` (客户端用于文本注入)。
  - `libnotify-bin` (客户端用于桌面通知)。
  - 音频库: `portaudio19-dev` (或兼容的 PortAudio 开发库)。
  - `python3-tk` (客户端的 `SimpleWindow` 和系统托盘图标需要)。

## 安装步骤

### 1. 安装系统依赖

```bash
# 更新包列表
sudo apt update

# 安装核心系统工具和库
sudo apt install -y git xdotool libnotify-bin portaudio19-dev python3-tk python3-dev python3-pip
```

### 2. 安装 uv (可选，但推荐用于包管理)

`uv` 是一个快速的 Python 包安装器和解析器。推荐参考 `uv` 的官方文档获取最新的安装指令: [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv)

通常，可以通过 pip (如果已安装) 或其他方式安装：
```bash
# 使用 pip 安装 uv (如果 pip 可用)
pip install uv
```

### 3. 克隆NexTalk仓库

```bash
git clone https://your-repository-url/nextalk.git # 请替换为实际的仓库URL
cd nextalk
```

### 4. 设置Python虚拟环境并安装依赖

建议在项目根目录 (包含 `pyproject.toml` 或 `requirements.txt` 的目录) 执行以下命令。

**使用 uv (推荐):**

```bash
# 创建或激活 .venv 虚拟环境
uv venv

# 激活虚拟环境 (Linux/macOS)
source .venv/bin/activate
# (Windows: .venv\Scripts\activate)

# 安装项目依赖 (包括开发依赖)
# 假设依赖在 pyproject.toml 中定义，并包含 "dev" extra
uv pip install -e ".[dev]"
# 或者，如果只有生产依赖或使用 requirements.txt:
# uv pip sync (如果使用 uv.lock)
# uv pip install -r requirements.txt
```

**使用 pip 和 venv (传统方式):**

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境 (Linux/macOS)
source .venv/bin/activate
# (Windows: .venv\Scripts\activate)

# 升级 pip
pip install --upgrade pip

# 安装项目依赖 (包括开发依赖)
# 假设依赖在 pyproject.toml 中定义，并包含 "dev" extra
pip install -e ".[dev]"
# 或者，如果使用 requirements 文件:
# pip install -r requirements.txt
# pip install -r requirements-dev.txt (如果开发依赖分开)
```

### 5. 安装FunASR核心引擎

FunASR 通常会作为项目依赖 (`funasr` 包) 被上一步自动安装。如果因为某种原因没有安装，可以手动安装：

```bash
# 在已激活的虚拟环境中
uv pip install funasr # 或者 pip install funasr
```

FunASR 模型文件会在首次运行时由 `FunASRModel` 根据配置自动从 ModelScope (或其他指定源) 下载并缓存到本地 (通常在 `~/.cache/modelscope/hub` 或类似路径)。一般无需手动下载模型。

### 6. 配置NexTalk

NexTalk 的配置文件是 `config.ini`。

1.  **复制默认配置**: 项目中提供了一个默认配置文件 `config/default_config.ini`。
    您需要将其复制到用户配置目录并根据需要进行修改：
    ```bash
    mkdir -p ~/.config/nextalk
    cp config/default_config.ini ~/.config/nextalk/client.ini
    cp config/default_config.ini ~/.config/nextalk/server.ini
    ```
2.  **修改配置**: 分别编辑 `~/.config/nextalk/client.ini` 和 `~/.config/nextalk/server.ini` 以符合您的设置。
    关键配置项将在下一节中解释。

    **注意**: `scripts/run_server.py` 和 `scripts/run_client.py` 脚本也支持通过命令行参数或环境变量覆盖部分配置项，这对于临时测试或特定部署场景很有用。

## 配置文件

- **客户端配置**: `~/.config/nextalk/client.ini`
- **服务端配置**: `~/.config/nextalk/server.ini`

默认配置文件位于 `~/.config/nextalk/client.ini 和 ~/.config/nextalk/server.ini` (您需要从 `config/default_config.ini` 复制并创建它)。
您可以根据需要修改以下设置。

**[Client]**

-   `hotkey`: 用于激活/停用语音识别的全局热键组合。
    *   示例: `ctrl+shift+space`, `alt+z`
    *   默认: `ctrl+shift+space` (在 `client_logic.py` 中可能有硬编码或最终的默认值)
-   `server_url`: NexTalk 服务器的完整 WebSocket URL。
    *   示例: `ws://localhost:8000/ws/stream`, `wss://yourdomain.com/ws/stream`
    *   默认: `ws://127.0.0.1:8000/ws/stream` (由 `client_logic.py` 提供)
-   `use_ssl`: 是否对 WebSocket 连接使用 SSL/TLS (wss://)。如果 `server_url` 以 `wss://` 开头，通常会自动处理。
    *   值: `true` 或 `false`
    *   默认: `false`
-   `enable_focus_window`: 当文本注入失败时，是否启用备选的简单文本窗口来显示结果。
    *   值: `true` 或 `false`
    *   默认: `true` (可能由 `client_logic.py` 或 `config/loader.py` 决定)
-   `focus_window_duration`: 简单文本窗口显示转录结果的持续时间（秒）。
    *   示例: `5`, `10`
    *   默认: `5` (可能由相关UI代码决定)

**[Server]**

-   `host`: 服务器监听的主机地址。
    *   示例: `0.0.0.0` (监听所有接口), `127.0.0.1` (仅本地)
    *   默认: `0.0.0.0` (由 `nextalk_server/config.py` 或 `run_server.py` 设置)
-   `port`: 服务器监听的端口。
    *   示例: `8000`, `8765`
    *   默认: `8000` (由 `nextalk_server/config.py` 或 `run_server.py` 设置)
-   `device`: FunASR 模型使用的计算设备。
    *   值: `cuda` (推荐, 使用NVIDIA GPU), `cpu`
    *   默认: `cuda` (如果可用，否则可能回退到 `cpu`，具体逻辑在 `FunASRModel`)
-   `ngpu`: (FunASR 参数) 使用的 GPU 数量，通常为 1 (如果 device 为 cuda)。
    *   默认: `1`
-   `ncpu`: (FunASR 参数) FunASR 可使用的 CPU核心数。
    *   默认: `4`
-   `asr_model`: FunASR 语音识别 (ASR) 模型名称或路径。这是核心模型。
    *   示例: `iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch` (一个Paraformer模型)
    *   参考 `nextalk_shared/constants.py` 中 `FUNASR_OFFLINE_MODEL` 或 `FUNASR_ONLINE_MODEL` 的默认值。
    *   FunASR 支持从 ModelScope 自动下载模型。
-   `asr_model_revision`: ASR 模型的版本。
    *   示例: `v1.2.3`, `master`
    *   默认: `None` 或 FunASR 的默认版本 (参考 `constants.py`)
-   `asr_model_streaming`: (可选) 如果使用独立的流式 ASR 模型，在此指定。如果 `asr_model` 本身支持流式，则此项可能不需要。
    *   示例: `iic/speech_paraformer_asr_streaming`
-   `vad_model`: FunASR 语音活动检测 (VAD) 模型名称或路径。
    *   示例: `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch` (一个FSMN VAD模型)
    *   参考 `nextalk_shared/constants.py` 中 `FUNASR_VAD_MODEL` 的默认值。
-   `vad_model_revision`: VAD 模型的版本。
-   `punc_model`: FunASR 标点恢复模型名称或路径。
    *   示例: `iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch` (一个CT-Transformer标点模型)
    *   参考 `nextalk_shared/constants.py` 中 `FUNASR_PUNC_MODEL` 的默认值。
-   `punc_model_revision`: 标点模型的版本。
-   `funasr_hotwords`: 热词列表，以换行符或特定分隔符分隔，用于提高特定词汇的识别准确率。具体格式请参考 FunASR 文档或 `FunASRModel` 实现。
    *   示例: `NexTalk\\nFunASR\\n自定义词汇`
-   `model_path`: (可选) FunASR 模型下载和缓存的根目录。如果未设置，FunASR 通常使用默认缓存路径 (如 `~/.cache/modelscope/hub`)。
    *   `scripts/run_server.py` 也支持通过 `--model-path` 命令行参数设置。

**注意**: 上述列表可能未包含所有可配置项。请检查 `config/default_config.ini` 的最新版本以及 `nextalk_server/config.py` 和 `nextalk_client/config/loader.py` 中的具体实现以获取完整和最准确的配置信息。

## 首次运行

成功安装并配置后，您可以启动 NexTalk。

### 1. 启动服务器

打开一个终端，进入 NexTalk 项目根目录，然后运行服务器脚本：

```bash
source .venv/bin/activate  # 激活虚拟环境 (如果尚未激活)
python scripts/run_server.py
```

服务器将开始监听指定的地址和端口 (默认为 `0.0.0.0:8000`)。首次运行时，如果配置的 FunASR 模型尚未缓存到本地，服务器会尝试下载它们，这可能需要一些时间。您可以通过服务器日志查看模型加载状态和任何潜在问题。

**常用服务器启动参数 (`scripts/run_server.py`):**
*   `--host <ip>`: 设置服务器监听的主机地址。
*   `--port <port>`: 设置服务器监听的端口。
*   `--device <cpu|cuda>`: 选择计算设备。
*   `--model-path <path>`: 指定模型缓存/搜索路径。
*   `--log-level <level>`: 设置日志级别 (debug, info, warning, error, critical)。
*   `--debug`: 快速启用调试日志级别。
*   `--log-file <file>`: 将日志输出到文件。
*   `--print-config`: 打印当前配置并退出，不启动服务器。
*   `--skip-preload`: 跳过模型预加载（服务器启动更快，但首次请求会因模型懒加载而变慢）。

### 2. 启动客户端

打开另一个终端，进入 NexTalk 项目根目录，然后运行客户端脚本：

```bash
source .venv/bin/activate  # 激活虚拟环境 (如果尚未激活)
python scripts/run_client.py
```

客户端将尝试连接到配置文件中 (`server_url`) 或通过命令行参数指定的服务器。连接成功后，系统托盘图标应该会出现，您可以通过热键开始使用语音识别。

**常用客户端启动参数 (`scripts/run_client.py`):**
*   `--server-host <host>`: 要连接的服务器主机地址 (覆盖配置文件)。
*   `--server-port <port>`: 要连接的服务器端口 (覆盖配置文件)。
*   `--debug`: 快速启用调试日志级别。
*   `--log-file <file>`: 将日志输出到文件。

### 3. 验证安装

1.  确保服务器和客户端都已无错误地启动。
2.  客户端系统托盘图标应显示正常状态 (例如，空闲或已连接)。
3.  按下配置的热键 (默认为 `Ctrl+Shift+Space`) 激活语音识别。
4.  对着麦克风说话。
5.  释放热键或等待语音识别自动完成 (取决于具体实现和模式)。
6.  验证识别的文本是否正确输入到当前活动的窗口中，或者在 `SimpleWindow` (如果注入失败) 中显示。

## 常见安装问题

### 无法安装PyAudio

如果在安装PyAudio时遇到问题，可能是因为缺少portaudio开发库：

```bash
sudo apt-get install portaudio19-dev
pip install pyaudio
```

### 无法安装FunASR

FunASR可能需要特定的依赖项，特别是在某些Linux发行版上：

```bash
# 确保已安装基本的编译工具
sudo apt-get install build-essential
sudo apt-get install python3-dev

# 安装FunASR
pip install funasr
```

如果仍然遇到问题，可以考虑从源代码安装：

```bash
git clone https://github.com/alibaba-damo-academy/FunASR.git
cd FunASR
pip install -e .
```

### 文本注入不工作

如果识别正常但文本没有注入到应用程序，请检查：

1. 是否已安装xdotool：`sudo apt-get install xdotool`
2. 是否启用了焦点窗口：确保配置文件中`enable_focus_window=true`
3. 是否安装了tkinter（用于焦点窗口）：`sudo apt-get install python3-tk`

### 服务器无法启动或模型下载失败

1. 检查网络连接是否正常
2. 尝试手动下载模型：`python scripts/download_models.py --download small.en --force`
3. 尝试使用更小的模型，如`tiny.en`或`SenseVoiceSmall`
4. 检查磁盘空间是否足够

## 进阶配置

### 多语言支持

NexTalk支持多种语言的语音识别。要优化特定语言的识别效果：

```ini
[Server]
# 英语优化
default_model=small.en
language=en

# 中文优化
default_model=paraformer-zh
language=zh

# 多语言支持
default_model=large-v3
language=auto
```

### 远程服务器配置

如果您希望在远程服务器上运行NexTalk服务器，需要修改以下配置：

服务器端配置（远程机器）：
```ini
[Server]
# 绑定到所有网络接口
host=0.0.0.0
port=8000
```

客户端配置（本地机器）：
```ini
[Client]
# 指向远程服务器地址
server_host=192.168.1.100  # 替换为实际服务器IP
server_port=8000
```

启动远程服务器：
```bash
python scripts/nextalk.py server --host 0.0.0.0
```

启动本地客户端连接远程服务器：
```bash
python scripts/nextalk.py client --server-host 192.168.1.100
```

## 其他资源

更多信息，请参阅：
- [用户指南](user_guide.md)：了解如何使用NexTalk的各项功能
- [架构文档](architecture.md)：了解NexTalk的技术架构
- [开发者指南](developer_guide.md)：了解如何参与NexTalk的开发

## 安装方法

### 依赖项

#### 必要依赖

- Python 3.10 或更高版本
- 用于音频处理的 PyAudio
- 用于WebSocket通信的 FastAPI, Uvicorn 和 websockets
- 用于语音识别的 FunASR

#### 可选依赖

- CUDA工具包（用于GPU加速）
- FFmpeg（用于某些音频处理功能）
- xdotool（Linux上用于文本注入）
- 用于系统托盘的 pystray 和 Pillow

### 安装FunASR

NexTalk现在主要使用FunASR作为语音识别引擎，需要正确安装：

```bash
# 安装FunASR (CPU版本)
pip install -U funasr

# 安装FunASR (GPU版本，需要CUDA支持)
pip install -U "funasr[cuda]"
```

如果您需要特定版本的FunASR，可以指定版本号：

```bash
pip install funasr==0.9.10
```

注意：FunASR依赖于多个第三方库，如torch、numpy等，它们会自动安装。

### 验证FunASR安装

确认FunASR正确安装：

```python
# 检查FunASR是否正确安装
python -c "from funasr import AutoModel; print('FunASR 安装成功')"
```

如果您要使用GPU版本，可以验证CUDA支持：

```python
python -c "import torch; print('CUDA可用：', torch.cuda.is_available()); print('CUDA设备数：', torch.cuda.device_count())"
```

### 使用pip安装NexTalk

```bash
# 克隆仓库
git clone https://github.com/username/nextalk.git
cd nextalk

# 使用pip安装
pip install -e .  # 以开发模式安装
```

### 使用uv安装（推荐）

```bash
# 安装uv (如果尚未安装)
curl -sSL https://install.python-poetry.org | python3 -

# 使用uv安装依赖
uv pip install --no-deps -e .

# 或者用uv安装开发环境
uv pip sync requirements.txt
```

## 配置NexTalk

### 配置文件

NexTalk使用两个主要配置文件：

1. **客户端配置**: `~/.config/nextalk/client_config.ini`
2. **服务器配置**: `~/.config/nextalk/server_config.ini`

### FunASR模型配置

服务器配置文件中的FunASR相关设置：

```ini
[Server]
# FunASR模型配置
funasr_offline_model = paraformer-zh
funasr_online_model = paraformer-zh-streaming
funasr_vad_model = fsmn-vad
funasr_punc_model = ct-punc
funasr_model_revision = v2.0.5

# 模型设备配置
device = cuda
ngpu = 1
ncpu = 4

# 模型缓存目录
model_path = ~/.cache/funasr/models
```

模型选择指南：
- **offline_model**: 离线识别模型，精度高但延迟较大
- **online_model**: 流式识别模型，实时性好但精度略低
- **vad_model**: 语音活动检测模型
- **punc_model**: 标点恢复模型

设备选择指南：
- 有NVIDIA GPU: 使用`device = cuda:0`并设置`use_fp16 = true`（推荐，节省显存）
- 仅CPU环境: 使用`device = cpu`，`use_fp16 = false`并适当增加`ncpu`值
- **注意**: 不要使用`compute_type`参数，FunASR官方不支持此参数
