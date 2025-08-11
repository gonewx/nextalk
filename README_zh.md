# NexTalk - 实时语音识别系统

[English Version](README.md)

NexTalk 是一套轻量级的实时本地语音识别和输入解决方案，核心引擎为 FunASR。它由服务器端 (`nextalk_server`) 和客户端 (`nextalk_client`) 组成，通过 WebSocket 进行高效通信。

查阅 [docs/](docs/) 目录下的详细文档：
-   [用户指南 (user_guide_zh.md)](docs/user_guide_zh.md)
-   [安装指南 (setup_guide_zh.md)](docs/setup_guide_zh.md)
-   [架构概览 (architecture_zh.md)](docs/architecture_zh.md)
-   [开发者指南 (developer_guide_zh.md)](docs/developer_guide_zh.md)

## 主要功能

-   **实时语音识别**: 基于 FunASR，支持高质量的中文及多语言语音转文本。
-   **流式与离线处理**: 服务器根据模型配置和音频流特性，智能采用流式（低延迟）或离线（高精度）识别。
-   **语音活动检测 (VAD)**: 集成 FunASR VAD，有效过滤静默和噪声。
-   **标点恢复**: 自动为识别文本添加标点。
-   **热词优化**: 支持通过配置文件自定义热词，提升特定词汇识别率。
-   **客户端集成**: 提供客户端实现音频捕获、文本注入（Linux下使用 `xdotool`）、系统托盘交互和热键控制。
-   **WebSocket 通信**: 高效实时的音频和结果传输。
-   **多平台支持**: 服务器和客户端均为 Python 实现，客户端UI和注入功能目前主要针对 Linux。
-   **灵活配置**: 通过单独的INI文件 (`~/.config/nextalk/server.ini` 和 `~/.config/nextalk/client.ini`) 提供丰富的服务器和客户端配置选项。
-   **GPU/CPU 支持**: FunASR 模型可在 GPU (CUDA) 或 CPU 上运行。

## 核心组件

-   **`nextalk_server` (服务器端)**:
    -   **FastAPI 应用 (`app.py`)**: Web 服务框架，管理应用生命周期。
    -   **WebSocket 端点 (`websocket_routes.py`)**: 处理 `/ws/stream` 上的客户端连接和数据交换。
    -   **`FunASRModel` (`funasr_model.py`)**: FunASR 核心引擎的封装，负责模型加载、管理、预热、推理（ASR, VAD, Punc）。
    -   **配置模块 (`config.py`)**: 加载和提供服务器配置。
-   **`nextalk_client` (客户端)**:
    -   **`NexTalkClient` (`client_logic.py`)**: 客户端核心逻辑，状态管理，与服务器交互。
    -   **音频捕获 (`audio/capture.py`)**: 使用 PyAudio 从麦克风获取音频。
    -   **文本注入 (`injection/`)**: 将文本输入到活动窗口。
    -   **UI组件 (`ui/`)**: 系统托盘 (`tray_icon.py`)、通知 (`notifications.py`)、备选文本显示 (`simple_window.py`)。
    -   **热键监听 (`hotkey/listener.py`)**: 全局热键支持。
-   **`nextalk_shared` (共享模块)**:
    -   **数据模型 (`data_models.py`)**: Pydantic 模型，用于 WebSocket 通信。
    -   **常量 (`constants.py`)**: 项目共享的常量。

## 快速开始

### 1. 环境准备与安装

请参考详细的 [安装指南 (docs/setup_guide_zh.md)](docs/setup_guide_zh.md)。简要步骤如下：

-   克隆仓库。
-   安装 Python 3.10+。
-   安装系统依赖 (如 `xdotool`, `portaudio19-dev`, `python3-tk` 等)。
-   创建虚拟环境 (推荐使用 `uv` 或 `venv`)。
-   在虚拟环境中安装项目依赖：
    ```bash
    # 使用 uv (推荐, 假设 pyproject.toml 定义了 dev extra)
    uv pip install -e ".[dev]"
    # 或使用 pip
    # pip install -e ".[dev]"
    ```
    这将同时安装 `funasr` 等核心依赖。

### 2. 配置

-   将 `config/default_config.ini` 复制到 `~/.config/nextalk/client.ini` 和 `~/.config/nextalk/server.ini`。
-   根据您的需求编辑配置文件 (详情参考用户指南和安装指南)。

### 3. 运行 NexTalk

**启动服务器:**
在项目根目录下打开一个终端，激活虚拟环境后运行：
```bash
python scripts/run_server.py
```
服务器将加载模型并开始监听 (默认为 `0.0.0.0:8000`)。

**启动客户端:**
在项目根目录下打开另一个终端，激活虚拟环境后运行：
```bash
python scripts/run_client.py
```
客户端将连接到服务器，之后您可以使用热键 (默认为 `Ctrl+Shift+Space`) 进行语音识别。

## WebSocket API (`ws://<host>:<port>/ws/stream`)

客户端通过此 WebSocket 端点与服务器进行通信。

-   **主要交互流程**:
    1.  客户端连接到服务器的 `/ws/stream` 端点。
    2.  连接成功后，客户端可以通过热键等方式触发音频捕获。
    3.  客户端将捕获到的音频数据块 (通常为 PCM 16kHz, 16-bit, 单声道) 实时流式发送给服务器。
    4.  服务器 (`FunASRModel`) 处理音频流，进行 VAD、ASR 和标点恢复。
    5.  服务器将识别结果 (可能是中间和最终结果) 以 JSON 消息的形式发送回客户端。

-   **接收识别结果示例**:
    客户端收到的消息通常为 JSON 格式，可以解析获取识别文本。
    ```javascript
    // 客户端 JavaScript 示例
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "transcription" && data.text) {
          console.log("识别结果:", data.text);
          if (data.is_final) {
            console.log("这是最终结果。");
            // 将 data.text 用于文本注入或其他处理
          }
        } else if (data.type === "status") {
          console.log("服务器状态:", data.status, data.message || "");
        } else if (data.type === "error") {
          console.error("服务器错误:", data.message);
        }
      } catch (e) {
        console.error("无法解析收到的消息:", event.data, e);
      }
    };
    ```
    实际的数据模型定义在 `nextalk_shared/data_models.py` 中 (例如 `TranscriptionResponse`, `StatusUpdate`, `ErrorMessage`)。

-   **控制命令与参数配置**:
    当前版本主要通过服务器启动时的配置文件 (`~/.config/nextalk/server.ini`) 和命令行参数进行 FunASR 模型及相关参数的配置。通过 WebSocket 进行的动态控制命令（如运行时切换模型、动态修改热词等）如果存在，则封装在内部通信协议中，并未作为主要的公开 API 特性在本文档中突出。主要交互是音频流和转录结果。

## `scripts/run_server.py` 主要命令行参数

以下是启动服务器脚本 `scripts/run_server.py` 的一些常用参数：

```
usage: run_server.py [-h] [--host HOST] [--port PORT]
                     [--log-level {debug,info,warning,error,critical}]
                     [--log-file LOG_FILE]
                     [--model-path MODEL_PATH] [--device {cpu,cuda}]
                     [--vad-sensitivity {1,2,3}]
                     [--enable-funasr-update] [--print-config] [--skip-preload]
                     [--asr-model ASR_MODEL] [--asr-model-revision ASR_MODEL_REVISION]
                     [--asr-model-streaming ASR_MODEL_STREAMING]
                     [--asr-model-streaming-revision ASR_MODEL_STREAMING_REVISION]
                     [--vad-model VAD_MODEL] [--vad-model-revision VAD_MODEL_REVISION]
                     [--punc-model PUNC_MODEL] [--punc-model-revision PUNC_MODEL_REVISION]
                     [--ngpu NGPU] [--ncpu NCPU]
                     [--model-hub {auto,modelscope,hf}]
                     # ... 可能还有其他 FunASR 直接参数通过 kwargs 传递 ...
```
-   `--host`: 服务器监听的主机地址 (默认: `0.0.0.0`)。
-   `--port`: 服务器监听的端口 (默认: `8000`)。
-   `--device`: 计算设备 (`cpu` 或 `cuda`, 默认: `cuda`)。
-   `--log-level`: 日志级别。
-   `--model-path`: 模型缓存/搜索路径。
-   `--asr-model`: 主要的 FunASR ASR 模型名称。
-   `--vad-model`: VAD 模型名称。
-   `--punc-model`: 标点模型名称。
-   `--skip-preload`: 跳过模型预加载。
-   `--print-config`: 打印配置并退出。

更详细的参数说明和配置方法，请参考 [用户指南 (docs/user_guide_zh.md)](docs/user_guide_zh.md) 和 [安装指南 (docs/setup_guide_zh.md)](docs/setup_guide_zh.md)。

## 贡献

欢迎参与贡献！请阅读 [开发者指南 (docs/developer_guide_zh.md)](docs/developer_guide_zh.md) 了解如何设置开发环境、代码风格和贡献流程。
