# NexTalk 用户指南

## 目录

- [NexTalk 用户指南](#nextalk-用户指南)
  - [目录](#目录)
  - [基本使用](#基本使用)
    - [启动方式](#启动方式)
      - [使用专用启动脚本 (推荐)](#使用专用启动脚本推荐)
      - [作为Python模块启动](#作为python模块启动)
    - [热键操作](#热键操作)
    - [转录控制](#转录控制)
    - [系统托盘图标](#系统托盘图标)
    - [通知系统](#通知系统)
  - [配置选项](#配置选项)
    - [\[Client\] 部分 (`~/.config/nextalk/config.ini`)](#client-部分-confignextalkconfigini)
    - [\[Server\] 部分 (`~/.config/nextalk/config.ini`)](#server-部分-confignextalkconfigini)
    - [模型选择](#模型选择)
    - [音频设置](#音频设置)
    - [界面设置](#界面设置)
  - [FunASR 高级功能](#funasr-高级功能)
    - [识别模式 (隐式)](#识别模式-隐式)
    - [热词优化](#热词优化)
    - [标点恢复](#标点恢复)
    - [语音活动检测 (VAD)](#语音活动检测-vad)
  - [高级功能与定制](#高级功能与定制)
    - [多语言支持](#多语言支持)
    - [性能调优 (服务器端)](#性能调优-服务器端)
    - [客户端行为定制](#客户端行为定制)
    - [关于"简化版客户端"](#关于简化版客户端)
  - [其他资源](#其他资源)

## 基本使用

### 启动方式

NexTalk 提供了灵活的启动方式。推荐使用项目 `scripts` 目录下的启动脚本。

#### 使用专用启动脚本 (推荐)

**1. 启动服务器:**

打开一个终端，进入 NexTalk 项目根目录，然后运行 (确保您的虚拟环境已激活)：

```bash
python scripts/run_server.py
```

服务器将开始运行，并监听配置文件中指定的地址和端口。首次运行时，如果配置的 FunASR 模型尚未下载，服务器会尝试自动下载和缓存它们。

*常用服务器启动参数 (`scripts/run_server.py`):*
*   `--host <ip_address>`: 设置服务器监听的主机地址 (默认: `0.0.0.0`)。
*   `--port <port_number>`: 设置服务器监听的端口 (默认: `8000`)。
*   `--device <cpu|cuda>`: 选择计算设备 (默认: `cuda`, 如果可用)。
*   `--model-path <path>`: 指定模型缓存/搜索路径。
*   `--log-level <debug|info|warning|error>`: 设置日志级别。
*   `--debug`: 快速启用调试日志级别。
*   `--log-file <path/to/log>`: 将日志输出到文件。
*   `--print-config`: 打印当前配置并退出，不启动服务器。
*   `--skip-preload`: 跳过模型预加载以加快服务器启动速度 (但首次识别请求会较慢)。

**2. 启动客户端:**

打开另一个终端，进入 NexTalk 项目根目录，然后运行 (确保您的虚拟环境已激活)：

```bash
python scripts/run_client.py
```

客户端将尝试连接到服务器。连接成功后，您应该会看到系统托盘图标，并可以通过热键开始使用语音识别。

*常用客户端启动参数 (`scripts/run_client.py`):*
*   `--server-host <ip_address>`: 要连接的服务器主机地址 (覆盖配置文件中的 `server_url` 主机部分)。
*   `--server-port <port_number>`: 要连接的服务器端口 (覆盖配置文件中的 `server_url` 端口部分)。
*   `--debug`: 快速启用调试日志级别。
*   `--log-file <path/to/log>`: 将日志输出到文件。

#### 作为 Python 模块启动 (开发者/备选)

您也可以直接将 NexTalk 作为 Python 模块运行：

**启动服务器:**
```bash
# (激活虚拟环境后)
python -m nextalk_server.main
```
或者更底层地 (通常用于开发 FastAPI 应用):
```python
# (在Python脚本中)
# from nextalk_server.app import app
# import uvicorn
# uvicorn.run(app, host="0.0.0.0", port=8000) # 根据需要调整 host 和 port
```

**启动客户端:**
```bash
# (激活虚拟环境后)
python -m nextalk_client.main
```

### 热键操作

NexTalk使用全局热键激活语音识别。默认热键为：

- `Ctrl+Shift+Space`: 开始/停止语音识别
- `Esc`: 取消当前转录

您可以在配置文件中自定义这些热键。

### 转录控制

NexTalk提供了多种控制转录过程的方式：

- **自动模式**: 自动检测语音开始和结束，无需手动控制
- **手动模式**: 按下热键开始录音，再次按下停止并转录
- **持续模式**: 连续录音并实时转录，直到手动停止

### 系统托盘图标

NexTalk 启动后，会在系统托盘区域显示一个图标。通过右键点击托盘图标，您可以：

- **查看当前状态**：图标会指示 NexTalk 是否正在监听、处理或空闲。
- **切换识别模型**：快速在已配置的模型间进行切换。
- **打开设置**（如果未来支持）：快速访问配置选项。
- **退出程序**：安全关闭 NexTalk 客户端和服务器。

### 通知系统

NexTalk 会通过桌面通知向您反馈重要信息，例如：

- **错误提示**：如连接服务器失败、模型加载失败等。
- **状态变更**：如开始监听、停止监听、模型切换成功等。
- **转录结果**（可选）：部分关键转录信息或提示。

通知的显示可以通过配置文件中的 `show_notifications` 选项来控制。如果您不希望看到任何桌面通知，可以将此选项设置为 `false`。

## 配置选项

NexTalk 的主要配置通过位于用户目录下的 `config.ini` 文件进行管理。您需要先将项目中的 `config/default_config.ini` 复制到 `~/.config/nextalk/config.ini`，然后根据需要进行修改。

命令行参数可以覆盖部分配置文件中的设置。

### [Client] 部分 (`~/.config/nextalk/config.ini`)

-   `hotkey = ctrl+shift+space`
    *   定义激活/停用语音识别的全局热键组合。支持如 `alt+z`, `ctrl+alt+s` 等格式。请参考 `pynput` 文档了解可用组合。
-   `server_url = ws://127.0.0.1:8000/ws/stream`
    *   指定 NexTalk 服务器的完整 WebSocket URL。如果服务器在另一台机器或使用 SSL (wss://)，请相应修改。
-   `show_notifications = true`
    *   是否显示桌面通知。设置为 `false` 将禁用所有状态变更和错误通知。
-   `use_ssl = false`
    *   如果 `server_url` 使用 `wss://`，此项通常会自动处理，但可以明确设置为 `true` 以强制 SSL 相关行为。
-   `enable_focus_window = true`
    *   当使用 `xdotool` 的文本注入失败时，是否启用备选的 `SimpleWindow` (一个置顶的简单文本窗口) 来显示识别结果。设置为 `false` 将禁用此备选方案。
-   `focus_window_duration = 5`
    *   如果 `enable_focus_window` 为 `true`，此选项设置 `SimpleWindow` 显示文本的持续时间（秒），之后窗口会自动淡出或隐藏。

### [Server] 部分 (`~/.config/nextalk/config.ini`)

-   `host = 0.0.0.0`
    *   服务器监听的主机地址。`0.0.0.0` 表示监听所有可用的网络接口；`127.0.0.1` 表示仅监听本地回环地址。
-   `port = 8000`
    *   服务器监听的 TCP 端口。
-   `device = cuda`
    *   FunASR 模型使用的主要计算设备。可选值为 `cuda` (推荐，使用 NVIDIA GPU) 或 `cpu`。如果选择 `cuda` 但无可用 GPU，FunASR 通常会自动回退到 `cpu` (可能伴有警告)。
-   `ngpu = 1`
    *   (FunASR 参数) 当 `device = cuda` 时，指定使用的 GPU 数量。通常设置为 `1`。
-   `ncpu = 4`
    *   (FunASR 参数) FunASR 在执行某些操作时可利用的 CPU 核心数。增加此值可能有助于 CPU 密集型任务的处理，但需根据实际硬件调整。
-   `model_path = ~/.cache/NexTalk/funasr_models` (示例, 实际默认可能由FunASR内部决定)
    *   (可选) 指定 FunASR 模型下载和缓存的根目录。如果未设置或 FunASR 无法识别，FunASR 通常会使用其内部默认的缓存路径 (如 `~/.cache/modelscope/hub`)。`scripts/run_server.py` 也支持通过 `--model-path` 命令行参数设置此路径。
-   `asr_model = iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`
    *   指定主要的 FunASR 语音识别 (ASR) 模型。这是进行语音转文本的核心模型。您可以从 ModelScope (modelscope.cn) 查找可用的 FunASR 模型名称。例如，`FUNASR_OFFLINE_MODEL` 或 `FUNASR_ONLINE_MODEL` 在 `nextalk_shared/constants.py` 中可能定义了推荐的默认值。
-   `asr_model_revision = None`
    *   (可选) 指定 ASR 模型的特定版本 (例如 git commit hash 或分支名)。如果为 `None` 或未指定，则使用模型的默认/最新版本。
-   `asr_model_streaming = None`
    *   (可选) 如果您希望为流式识别使用一个与 `asr_model` 不同的、专门优化的流式模型，请在此处指定其名称。如果 `asr_model` 本身已支持高效流式处理，则此项可能不需要或应与 `asr_model` 相同。
-   `asr_model_streaming_revision = None`
    *   (可选) `asr_model_streaming` 的特定版本。
-   `vad_model = iic/speech_fsmn_vad_zh-cn-16k-common-pytorch`
    *   指定 FunASR 语音活动检测 (VAD) 模型。用于在音频流中检测有效的语音片段，过滤背景噪音和静默。`nextalk_shared/constants.py` 中的 `FUNASR_VAD_MODEL` 可能有默认值。
-   `vad_model_revision = None`
    *   (可选) VAD 模型的特定版本。
-   `punc_model = iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch`
    *   指定 FunASR 标点恢复模型。用于在 ASR 输出的原始文本中自动添加标点符号。`nextalk_shared/constants.py` 中的 `FUNASR_PUNC_MODEL` 可能有默认值。
-   `punc_model_revision = None`
    *   (可选) 标点模型的特定版本。
-   `funasr_hotwords =`
    *   (可选) 热词列表，用于提高特定词汇或短语的识别准确率。格式通常是每个热词占一行，或者以特定方式分隔。具体格式请参考 FunASR 文档或 `FunASRModel` 中的实现。示例：
        ```ini
        funasr_hotwords = NexTalk
                          FunASR
                          自定义术语
        ```

**重要提示**: 上述列表是对主要配置项的说明。部分配置项的默认值可能在代码中 (如 `nextalk_server/config.py`, `nextalk_client/config/loader.py`, `nextalk_shared/constants.py`) 硬编码或有更复杂的确定逻辑。请务必参考 `config/default_config.ini` 文件作为最权威的配置模板，并结合代码行为来理解每个选项的精确作用。

### 模型选择

您可以在配置文件中选择不同的语音识别模型：

```ini
[server]
# Whisper模型可选值: tiny, base, small, medium, large, large-v3, distil-large-v3
# FunASR模型可选值: paraformer-zh, paraformer-zh-streaming, SenseVoiceSmall
default_model = large-v3
# 可选值: cpu, cuda
device = cuda
```

Whisper模型的对比：
- `tiny`: 最小，速度最快，精度最低
- `base`/`small`: 平衡速度和精度
- `medium`/`large`: 高精度，但需要更多计算资源
- `large-v3`/`distil-large-v3`: 最新模型，支持更多语言

FunASR模型的对比：
- `paraformer-zh`: 标准中文模型，精度较高，速度适中
- `paraformer-zh-streaming`: 流式中文模型，实时性好，适合持续转录
- `SenseVoiceSmall`: 小型通用模型，资源占用少，速度快

选择模型时的建议：
- 对于中文识别，推荐使用FunASR的`paraformer-zh`或`paraformer-zh-streaming`模型
- 对于英文或多语言识别，推荐使用Whisper的`large-v3`或`medium`模型
- 在资源受限的设备上，可以选择较小的模型，如Whisper的`small`或FunASR的`SenseVoiceSmall`

除了通过配置文件修改，您还可以通过**系统托盘图标的菜单**快速切换已在服务器端加载或支持的识别模型。

### 音频设置

调整音频设置以获得最佳识别效果：

```ini
[audio]
# 音频后端选择 (pulseaudio, alsa, portaudio)
audio_backend = pulseaudio
# 采样率 (16000推荐)
sample_rate = 16000
# 声道数 (1=单声道)
channels = 1
```

### 界面设置

客户端界面和行为设置：

```ini
[client]
# 服务器连接设置
server_host = 127.0.0.1
server_port = 8765
# 转录结果显示时间(秒)
notification_timeout = 5
# 自动输入文本到当前活动窗口
auto_type = true
# 是否启用焦点窗口作为文本注入失败时的备选方案 (true/false)
enable_focus_window = true
# 焦点窗口显示时长（秒）
focus_window_duration = 5
```

**焦点窗口 (Focus Window)**:

当 `auto_type` 设置为 `true` 但 `xdotool` 文本注入失败时，如果 `enable_focus_window` 也为 `true`，NexTalk 会尝试在一个置顶的半透明"焦点窗口"中显示转录的文本。这个窗口通常出现在屏幕底部，并在 `focus_window_duration` 指定的时间后自动淡出。这确保了即使在无法直接输入到目标应用的情况下，您仍然可以看到识别结果。

## FunASR 高级功能

NexTalk 通过服务器端的 `FunASRModel` 封装了 FunASR 的多种高级功能。这些功能主要通过服务器配置文件 (`~/.config/nextalk/config.ini` 的 `[Server]` 部分) 进行控制。

### 识别模式 (隐式)

FunASR 支持多种内部工作模式，例如离线 (整句识别) 和在线 (流式识别)。NexTalk 的 `FunASRModel` 会根据加载的模型 (例如，通过 `asr_model` 和 `asr_model_streaming` 配置项指定的模型) 和接收音频数据的方式 (单个完整块 vs. 连续小块) 来隐式地利用这些模式。

-   **流式处理**: 当客户端持续发送小的音频块时，服务器端的 `FunASRModel` (如果加载了流式模型) 会进行流式处理，并可能实时或准实时地返回中间和最终识别结果。
-   **离线处理**: 如果接收到较大或完整的音频片段，或者配置了仅支持离线的模型，则会进行更偏向整句的识别处理，这通常能带来更高的准确性但延迟也相应增加。

用户通常不需要直接切换这些底层模式，而是通过选择合适的 FunASR 模型 (在服务器配置中) 和使用方式来获得期望的识别行为。

### 热词优化

通过在服务器配置文件的 `[Server]` 部分设置 `funasr_hotwords`，可以提供一个热词列表，以提高特定词汇、短语或专业术语的识别准确率。FunASR 会在识别过程中对这些热词给予更高的权重。

**配置示例 (`config.ini`):**
```ini
[Server]
# ... 其他服务器配置 ...
funasr_hotwords =
    NexTalk
    FunASR Pipeline
    自定义产品名称
    领域特定术语
```
每行一个热词或短语。请参考 FunASR 的官方文档以获取关于热词格式和最佳实践的更多信息。

### 标点恢复

通过在服务器配置中指定 `punc_model` (例如, `iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch`)，可以启用自动标点恢复功能。FunASR 会在 ASR 引擎输出的原始文本基础上自动添加逗号、句号、问号等标点符号，使输出的文本更自然、更易读。

如果不需要标点恢复，可以将 `punc_model` 配置项留空或注释掉。

### 语音活动检测 (VAD)

服务器配置中的 `vad_model` (例如, `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch`) 指定了用于语音活动检测的模型。VAD 帮助系统区分语音和非语音片段（如静默、背景噪音），只将包含语音的音频数据传递给 ASR 引擎。这可以减少不必要的计算，提高识别效率，并在某些情况下改善识别准确性。

## 高级功能与定制

### 多语言支持

FunASR 本身支持多种语言的识别。NexTalk 对多语言的支持主要取决于您在服务器配置中为 `asr_model` (以及相关的 VAD 和标点模型，如果需要特定语言版本)选择了哪个 FunASR 模型。

例如，要识别英文，您需要选择一个英文的 FunASR ASR 模型。要识别中文，则选择中文模型。请查阅 ModelScope 上的 FunASR 模型列表，找到适合您目标语言的模型，并在 `config.ini` 中进行配置。

### 性能调优 (服务器端)

-   **设备选择 (`device`)**: 对于生产环境或追求低延迟的场景，强烈建议使用 `cuda` (NVIDIA GPU)。CPU 推理会慢很多。
-   **模型选择**: 不同的 FunASR 模型在速度、准确率和资源消耗之间有不同的权衡。大型模型通常更准确但更慢且占用更多资源。流式模型通常延迟更低。
-   **预加载与预热**: `scripts/run_server.py` 默认会预加载和预热模型，这会增加服务器启动时间，但能显著减少首次识别请求的延迟。对于开发或不需要立即响应的场景，可以考虑使用 `--skip-preload` 参数启动服务器。
-   **CPU核心数 (`ncpu`)**: 如果在 CPU 上运行或 GPU 性能有限，适当调整 `ncpu` 可能有助于提升 FunASR 的处理速度，但这需要根据具体硬件进行测试。

### 客户端行为定制

-   **热键 (`hotkey`)**: 自定义热键以适应您的工作流程。
-   **注入失败备选 (`enable_focus_window`, `focus_window_duration`)**: 配置当 `xdotool` 注入失败时，简单文本窗口的显示行为。

### 关于"简化版客户端"

旧版文档中可能提及 `use_simple_client` 配置。请检查当前 `client_logic.py` 和相关UI代码，确认此选项是否仍然有效，或者其功能已被其他机制替代或移除。如果不再使用，应忽略此配置。

## 其他资源

- 安装指南：查看 [setup_guide.md](setup_guide.md) 获取完整的安装说明
- 项目架构：查看 [architecture.md](architecture.md) 了解NexTalk的技术架构
- 贡献指南：查看 [developer_guide.md](developer_guide.md) 了解如何参与项目开发 