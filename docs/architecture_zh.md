# NexTalk 系统架构

本文档详细描述了NexTalk的系统架构，包括主要组件、数据流、技术栈选择以及系统间交互方式。

## 1. 系统概述

NexTalk是一个轻量级实时本地语音识别和输入系统，允许用户通过语音输入文本到任何应用程序。系统由两个主要部分组成：客户端 (`nextalk_client`) 和服务器 (`nextalk_server`)，它们通过WebSocket协议进行实时通信。

### 1.1 核心功能

- 实时语音捕获和处理 (客户端)
- 高质量语音识别（基于服务器端的 FunASR 引擎，支持多种模型和语言）
- 低延迟文本输入到活动应用程序 (客户端，主要使用 `xdotool`)
- 热键控制的语音识别激活/停用 (客户端)
- 系统托盘界面和状态指示 (客户端)
- 可配置的语音识别模型 (服务器端配置，客户端可能通过特定机制请求或展示)
- 备选文本显示窗口 (客户端 `SimpleWindow`，用于注入失败时)

### 1.2 系统架构示意图

```
+-----------------------+        WebSocket (/ws/stream)        +------------------------+
|                       |      音频数据 / 转录结果 / 控制     |                        |
|    NexTalk 客户端     | <---------------------------------> |    NexTalk 服务器      |
| (nextalk_client)      |                                     | (nextalk_server)       |
+-----------------------+                                     +------------------------+
    |      ^      |                                           |          ^      |
    |      |      | Audio                                     | VAD      | ASR  | Punc
    v      |      | Chunks                                    v          |      |
+--------+ | +--------+                          +----------+----------+------+
|  Audio | | | Text   |                          | FunASR Voice Activity Detection |
| Capturer| | | Injector|                          | (fsmn-vad or similar)           |
+--------+ | +--------+                          +---------------------------------+
    ^      |      |                                           |          
    |      |      |                                           v          
    | Hotkey |    | SimpleWindow (Fallback)         +---------------------------------+
    | Listener |  +--------+                          | FunASR ASR Engine (Streaming/Offline) |
    |      |                                           | (e.g., Paraformer, SenseVoice)  |
+--------+ |                                           +---------------------------------+
    |      |                                                       |          
    v      |                                                       v          
+--------+ |                                           +---------------------------------+
| System | |                                           | FunASR Punctuation Model        |
| Tray UI| |                                           | (ct-punc or similar)            |
+--------+                                            +---------------------------------+
```

## 2. 主要组件

NexTalk系统由以下主要组件组成：

### 2.1 客户端组件 (`nextalk_client`)

1.  **`NexTalkClient`** (`client_logic.py`):
    *   客户端的核心逻辑类，协调所有其他客户端组件的交互。
    *   管理客户端的整体状态 (空闲、连接、监听、处理、错误等)。
    *   处理来自服务器通过 WebSocket 发送的各类消息。
    *   响应用户通过热键和托盘图标发起的动作。

2.  **`AudioCapturer`** (`audio/capture.py`):
    *   负责从系统麦克风捕获音频数据。
    *   使用 PyAudio 库实现。
    *   支持通过配置文件进行设备选择和音频参数配置。

3.  **`WebSocketClient`** (`network/client.py`):
    *   管理与服务器的 WebSocket 连接 (通常连接到 `/ws/stream` 端点)。
    *   负责发送音频数据块到服务器，并接收转录结果、状态更新及错误信息。

4.  **`Injector`** (`injection/`):
    *   将服务器返回的转录文本注入到当前活动的应用程序窗口。
    *   主要实现是 `XdotoolInjector` (使用 `xdotool` 命令)，针对 Linux 系统。
    *   基于 `BaseInjector` 抽象基类，允许未来扩展支持其他平台。

5.  **`SimpleWindow`** (`ui/simple_window.py`):
    *   提供一个简单的置顶浮动窗口。
    *   用作文本注入的备选方案：当 `xdotool` 注入失败或不可用时，转录文本会显示在此窗口中。
    *   确保用户总能看到识别结果。

6.  **`HotkeyListener`** (`hotkey/listener.py`):
    *   监听全局热键事件 (例如，默认 `Ctrl+Shift+Space`)。
    *   使用 `pynput` 库实现。
    *   用于激活或停用语音识别过程（即开始/停止捕获和发送音频）。

7.  **`SystemTrayIcon`** (`ui/tray_icon.py`):
    *   在系统托盘区域显示 NexTalk 的状态图标和菜单。
    *   使用 `pystray` 库实现。
    *   图标根据客户端当前状态（如空闲、监听中、处理中、错误）变化。
    *   菜单通常提供"退出"选项，并可能包含其他功能（如打开设置或切换模型，需进一步确认）。

8.  **`NotificationManager`** (`ui/notifications.py`):
    *   负责向用户显示桌面通知。
    *   用于报告重要事件，如连接错误、状态变更或关键识别信息。

9.  **Configuration Loader** (`config/loader.py`):
    *   负责加载客户端的配置文件 (通常是 `~/.config/nextalk/client.ini 和 ~/.config/nextalk/server.ini` 中的 `[Client]`部分)。
    *   为其他客户端组件提供配置参数。

### 2.2 服务器组件 (`nextalk_server`)

1.  **FastAPI Application** (`app.py`):
    *   基于 FastAPI 构建的 Web 应用，使用 Uvicorn 作为 ASGI 服务器运行。
    *   负责应用的生命周期管理（启动时加载模型、关闭时释放资源）。
    *   管理 `FunASRModel` 实例的状态，并将其提供给请求处理程序。

2.  **WebSocket Endpoint** (`websocket_routes.py`):
    *   通过 FastAPI 的 `APIRouter` 定义 WebSocket 端点 (通常是 `/ws/stream`)。
    *   处理来自客户端的 WebSocket 连接请求和生命周期。
    *   异步接收客户端发送的音频数据流。
    *   将音频数据块传递给 `FunASRModel` 实例进行处理。
    *   将 `FunASRModel` 返回的转录结果、状态更新或错误信息通过 WebSocket 发送回对应的客户端。

3.  **`FunASRModel`** (`funasr_model.py`):
    *   核心语音识别引擎的封装类，负责与 FunASR 库交互。
    *   **多组件集成**: 内部管理和调用 FunASR 的多个模型组件，包括：
        *   离线 ASR 模型 (用于高精度整句识别)
        *   在线/流式 ASR 模型 (用于低延迟实时识别)
        *   VAD (语音活动检测) 模型 (用于过滤静默片段)
        *   标点恢复模型 (用于自动添加标点)
    *   **配置驱动**: 从服务器配置文件加载模型名称、设备 (CPU/CUDA)、模型版本等参数。
    *   **模型管理**: 负责各模型组件的初始化（包括预热）、运行推理和资源释放。支持通过 `scripts/run_server.py` 进行模型预加载，以加速服务器启动。
    *   **识别流程**: 提供处理流式音频 (`process_audio_chunk`) 和离线音频 (`process_audio_offline`) 的方法。
    *   **异步执行**: 将耗时的模型推理操作放在 `ThreadPoolExecutor` 中执行，避免阻塞服务器主事件循环。

4.  **Configuration** (`config.py`):
    *   负责加载和管理服务器的配置信息 (通常来自 `~/.config/nextalk/client.ini 和 ~/.config/nextalk/server.ini` 中的 `[Server]` 部分，或 `config/default_config.ini`)。
    *   为其他服务器组件（主要是 `FunASRModel` 和 `app.py`）提供配置访问接口。

### 2.3 共享组件

1.  **Data Models** (`data_models.py`):
    *   定义了客户端和服务器之间通过 WebSocket 通信时使用的 Pydantic 数据模型。
    *   例如：`TranscriptionResponse`, `ErrorMessage`, `StatusUpdate`, `CommandMessage`。
    *   确保了通信数据的结构化和类型安全。

2.  **Constants** (`constants.py`):
    *   定义了项目中多处使用的常量。
    *   例如：状态字符串 (IDLE, LISTENING, PROCESSING等)，默认模型名称，音频参数等。
    *   有助于保持一致性并避免硬编码值。

## 3. 数据流

### 3.1 音频捕获和处理流程

1.  客户端 (`NexTalkClient`) 通过全局热键 (由 `HotkeyListener` 捕获) 激活语音识别。
2.  `AudioCapturer` 从麦克风捕获音频数据块。
3.  客户端 (`WebSocketClient`) 通过已建立的 WebSocket 连接，将音频数据块实时发送到服务器的 `/ws/stream` 端点。
4.  服务器端的 `WebSocket Endpoint` 接收音频数据，并将其传递给 `FunASRModel` 实例。
5.  `FunASRModel` 首先使用其 VAD (语音活动检测) 组件处理音频数据，以识别有效的语音片段。
6.  有效的语音数据被送入选择的 ASR (自动语音识别) 模型（在线/流式或离线模式，取决于配置和数据块的性质）。
7.  ASR 模型将语音转换为文本。
8.  可选地，生成的文本通过标点恢复模型 (`PuncModel`) 添加标点。
9.  `FunASRModel` 返回最终的转录结果 (可能包括中间结果，如果是在线模式)。
10. 服务器的 `WebSocket Endpoint` 将转录结果 (封装在如 `TranscriptionResponse` 的数据模型中) 通过 WebSocket 发送回对应的客户端。
11. 客户端 (`NexTalkClient`) 接收转录文本。
12. `Injector` 组件尝试将文本注入到当前活动的应用程序窗口。如果失败，文本可能会显示在 `SimpleWindow` 中。
13. 客户端状态（通过 `SystemTrayIcon` 和通知显示）会相应更新。

### 3.2 模型切换流程

*目前版本的 NexTalk 主要通过服务器配置文件在启动时设定 FunASR 模型。客户端通过系统托盘动态切换模型的功能在本文档编写时尚未完全确认。如果实现，流程可能如下：*

1.  用户通过客户端的系统托盘菜单选择一个新的语音识别模型。
2.  客户端构建一个包含模型切换请求的 `CommandMessage` (或类似机制)，并通过 WebSocket 发送到服务器。
3.  服务器的 `WebSocket Endpoint` 接收到该命令。
4.  服务器端的逻辑 (可能在 `FunASRModel` 或 `app.py` 中) 尝试加载并切换到请求的新模型。这可能涉及释放当前模型并初始化新模型。
5.  服务器通过 WebSocket 向客户端返回操作结果（成功或失败，可能包含错误信息）。
6.  客户端更新其UI（如托盘图标提示或通知）以反映模型切换的状态。

### 3.3 状态更新流程

1.  当客户端或服务器内部状态发生变化时（例如：客户端开始/停止监听，服务器开始/停止处理音频，发生错误，连接断开/成功等）。
2.  相关的组件（客户端的 `NexTalkClient` 或服务器的 `WebSocket Endpoint`/`FunASRModel`）会生成一个 `StatusUpdate` 消息 (或 `ErrorMessage`)。
3.  此消息通过 WebSocket 在服务器和客户端之间传递。
4.  接收方根据消息内容更新其内部状态和用户界面（例如，客户端的系统托盘图标、通知；服务器端的日志记录）。

## 4. 技术栈选择

### 4.1 核心技术

| 组件领域     | 技术选择                                 | 主要原因                                                                 |
|--------------|------------------------------------------|--------------------------------------------------------------------------|
| 核心语言     | Python 3.10+                             | 跨平台、丰富的库生态、快速开发、FunASR等AI库的良好支持                     |
| 语音识别     | FunASR (阿里云DAMO)                      | 高质量的中文和多语言ASR、VAD、标点恢复模型；支持流式和离线模式             |
| 服务器框架   | FastAPI + Uvicorn                        | 高性能异步API框架、内置WebSocket支持、Pydantic数据校验、易于开发和扩展     |
| WebSocket通信| `websockets` 库 (FastAPI集成)            | Python中成熟的WebSocket实现，支持异步，性能良好                            |
| 客户端音频捕获 | PyAudio                                  | 跨平台音频I/O库，广泛使用                                                |
| 客户端热键监听 | `pynput`                                 | 跨平台全局键盘事件监听                                                   |
| 客户端系统托盘 | `pystray`                                | 轻量级、跨平台的系统托盘图标库                                           |
| 客户端文本注入 | `xdotool` (Linux)                        | 成熟的Linux命令行工具，用于模拟键盘输入和窗口管理                        |
| 客户端UI备选 | Tkinter (用于 `SimpleWindow`)            | Python内置GUI库，用于简单的窗口显示                                        |
| 配置文件格式 | INI (使用 `configparser` 标准库)         | 简单易读的配置文件格式，Python标准库支持                                   |
| 依赖管理(推荐)| `uv`                                     | 快速的Python包安装器和解析器                                               |

### 4.2 依赖管理

推荐使用 `uv` 进行依赖管理，配合 `pyproject.toml` (如果项目使用) 或 `requirements.txt` 文件来定义项目依赖和虚拟环境。这种方式有助于确保开发和部署环境的一致性。

## 5. 模块结构

项目代码主要组织在 `src/` 目录下，分为三个核心包：`nextalk_shared`, `nextalk_server`, 和 `nextalk_client`。

```
src/
├── nextalk_shared/        # 客户端和服务器共享的模块
│   ├── constants.py       # 定义共享常量 (如状态字符串, FunASR默认模型名等)
│   ├── data_models.py     # 定义共享数据模型 (如WebSocket通信用的Pydantic模型)
│   └── __init__.py
│
├── nextalk_server/        # 服务器端代码
│   ├── funasr_model.py    # FunASR模型的核心封装和管理
│   ├── websocket_routes.py # 定义WebSocket API端点和处理逻辑
│   ├── config.py          # 服务器配置加载和管理
│   ├── app.py             # FastAPI应用的创建和生命周期管理
│   ├── main.py            # 服务器主入口 (通常由uvicorn或run_server.py调用)
│   └── __init__.py
│
└── nextalk_client/        # 客户端代码
    ├── client_logic.py    # 客户端核心逻辑 (状态管理, 事件处理)
    ├── main.py            # 客户端主入口和命令行处理
    ├── audio/             # 音频捕获模块 (e.g., capture.py)
    ├── config/            # 客户端配置加载 (e.g., loader.py)
    ├── network/           # WebSocket客户端实现 (e.g., client.py)
    ├── hotkey/            # 全局热键监听 (e.g., listener.py)
    ├── injection/         # 文本注入模块 (e.g., injector_base.py, xdotool_injector.py)
    ├── ui/                # 用户界面组件
    │   ├── tray_icon.py   # 系统托盘图标和菜单
    │   ├── notifications.py # 桌面通知
    │   ├── simple_window.py # 用于显示文本的简单窗口 (备选注入方式)
    │   └── __init__.py
    └── __init__.py
```

项目根目录下还包含 `scripts/` (用于启动和打包)、`config/` (默认配置文件)、`docs/` 和可选的 `tests/` 等目录。

## 6. 关键技术决策

### 6.1 客户端-服务器分离架构

NexTalk采用了客户端-服务器分离架构，而不是单一应用程序架构，主要基于以下考虑：

1. **资源隔离**：语音识别模型（尤其是大型模型）需要大量内存和GPU资源，通过服务器隔离这些资源消耗
2. **功能解耦**：允许客户端专注于UI和用户交互，服务器专注于计算密集型任务
3. **灵活部署**：支持单机部署和远程服务器部署两种模式
4. **多客户端支持**：未来可以扩展支持多个客户端连接到同一服务器

### 6.2 WebSocket通信

选择WebSocket作为通信协议的原因：

1. **实时性**：提供低延迟的全双工通信
2. **二进制支持**：有效传输音频数据
3. **状态管理**：维护持久连接，简化状态同步
4. **广泛支持**：良好的库支持和跨平台兼容性
5. **流式处理**：支持FunASR的流式识别模式
6. **轻量级**：比gRPC更易于调试和部署

### 6.3 插件式文本注入

设计了基于平台的文本注入器抽象类和工厂模式：

1. **跨平台扩展性**：虽然当前版本主要支持Linux，但架构设计允许轻松添加其他平台支持
2. **解耦依赖**：平台特定代码被隔离在特定模块中
3. **统一接口**：所有平台实现都遵循同一接口，简化客户端逻辑

## 7. 性能考虑

### 7.1 音频处理

- 使用VAD进行语音检测，减少处理非语音数据的资源消耗
- 音频帧缓冲设计优化了内存使用和处理延迟的平衡
- 使用numpy进行高效的音频数据操作

### 7.2 语音识别

- 集成FunASR模型，提供更好的中文和多语言识别能力
  - 支持离线转录模式，提供最高质量的识别结果
  - 支持流式（实时）处理模式，实现低延迟连续音频转录
  - 支持2pass混合模式，结合在线和离线的优势
  - 内置语音活动检测(VAD)、标点恢复和时间戳预测
  - 支持热词功能，提高特定领域术语识别准确率
- 支持CPU和CUDA设备选择，适应不同硬件环境
- 模型类型和参数通过配置文件灵活配置
- 支持基于WebRTC的VAD滤波，减少非语音段处理

### 7.3 并发处理

- 使用异步编程模型处理WebSocket通信和音频处理
- 分离音频捕获和处理线程，确保捕获不被处理延迟影响
- 实现线程安全的数据共享机制

## 8. 扩展性和未来发展

### 8.1 计划的扩展

- Windows和macOS文本注入支持
  - 为Windows平台实现基于Win32 API的文本注入
  - 为macOS平台实现基于AppleScript的文本注入
- 更多语音识别模型选项
  - 集成更多轻量级模型，适用于低资源设备
  - 支持自定义模型导入和使用
- FunASR模型的进一步优化
  - 增强热词功能，支持更复杂的权重和匹配规则
  - 添加更多语言支持，拓展多语言模型
  - 提供更精细的VAD和标点控制选项
  - 实现更高效的流式识别算法
- 高级语音命令和自定义操作
  - 允许用户定义语音命令触发特定动作
  - 支持基本的语音助手功能
- 用户界面改进和配置面板
  - 添加图形化配置界面，便于非技术用户调整设置
  - 提供实时音频波形显示和转录历史记录
- 多语言界面支持
  - 提供多语言UI，提升国际化用户体验
- 性能优化
  - 实现更高效的音频预处理算法
  - 优化模型加载和切换过程
  - 提高大型模型的性能，减少资源消耗

### 8.2 API扩展

- 提供RESTful API接口，允许第三方应用集成
- 开发WebSocket客户端库，便于其他语言开发的应用接入
- 支持批量音频文件处理功能

### 8.3 生态系统集成

- 与流行的生产力工具集成
- 开发浏览器扩展，支持网页应用中的语音输入
- 为开发者提供插件系统，允许自定义功能扩展 