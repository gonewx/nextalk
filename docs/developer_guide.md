# NexTalk 开发者指南

## 目录

- [项目架构概述](#项目架构概述)
- [开发环境设置](#开发环境设置)
- [代码组织结构](#代码组织结构)
- [测试指南](#测试指南)
- [代码风格指南](#代码风格指南)
- [贡献流程](#贡献流程)
- [FunASR集成指南](#funasr集成指南)
- [常见问题解决](#常见问题解决)
- [打包与分发](#打包与分发)

## 项目架构概述

NexTalk 是一个轻量级实时本地语音识别和输入系统，由客户端和服务器两部分组成。详细的架构信息请参阅 [架构文档](architecture.md)。

系统主要组件包括：
- **服务器端 (`nextalk_server`)**: 负责语音识别和处理，核心为 `FunASRModel`，集成了 FunASR 的语音识别 (ASR)、语音活动检测 (VAD) 和标点恢复功能。
- **客户端 (`nextalk_client`)**: 负责音频捕获、用户界面交互（热键、系统托盘）和文本注入。
- **共享模块 (`nextalk_shared`)**: 包含客户端和服务器共用的数据模型和常量。
- **WebSocket通信**: 用于客户端和服务器之间的实时双向通信。
- **文本注入器**: 客户端组件，用于将识别的文本输入到活动窗口 (主要使用 `xdotool`，备选方案为简单文本窗口)。

## 开发环境设置

### 系统要求

- Python 3.10 或更高版本
- Linux 系统（主要开发和测试平台）
- Git

### 开发依赖

除了基本的运行时依赖外，开发时还需要以下工具和库：

- `funasr>=1.0.0`: 核心语音识别引擎。
- `uvicorn`: ASGI 服务器，用于运行 FastAPI 应用。
- `websockets`: FastAPI/Uvicorn 使用的 WebSocket 库。
- `pyaudio`: 用于客户端音频捕获。
- `pynput`: 用于客户端全局热键监听。
- `pystray`: 用于客户端系统托盘图标。
- `pytest` 和 `pytest-asyncio`：用于测试。
- `pytest-cov`：用于测试覆盖率报告。
- `ruff`：代码格式化和静态分析。

### 设置开发环境

1. 克隆仓库：
   ```bash
   git clone https://github.com/your-org/nextalk.git # 请替换为实际仓库地址
   cd nextalk
   ```

2. 推荐使用 `uv` 创建虚拟环境并安装依赖：
   ```bash
   # 安装 uv (如果尚未安装，请参考 uv 官方文档: https://github.com/astral-sh/uv)
   # pip install uv (示例)
   uv venv .venv
   source .venv/bin/activate
   # 假设依赖在 pyproject.toml 中定义，并包含 "dev" extra
   uv pip install -e ".[dev]"
   # 或者，如果使用 requirements.txt:
   # uv pip install -r requirements.txt -r requirements-dev.txt
   ```
   或者使用传统的 `venv` 和 `pip`:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   # 假设依赖在 pyproject.toml 中定义，并包含 "dev" extra
   pip install -e ".[dev]"
   # 或者，如果使用 requirements.txt:
   # pip install -r requirements.txt -r requirements-dev.txt
   ```

3. 安装系统依赖（Linux）：
   ```bash
   sudo apt-get update
   sudo apt-get install xdotool libnotify-bin portaudio19-dev python3-tk
   ```
   (`python3-tk` 对于客户端的简单文本窗口和系统托盘功能是必需的。)

4. （可选）配置CUDA环境:
   如果希望使用GPU进行语音识别（推荐以获得更好性能），请确保已正确安装NVIDIA驱动程序和CUDA工具包，并与FunASR所依赖的PyTorch版本兼容。

## 代码组织结构

项目代码组织为三个主要Python包，位于 `src/` 目录下：

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

**脚本和配置**

项目根目录下还包含其他重要文件和目录：

```
nextalk/                       # 项目根目录 (示例)
├── scripts/                   # 辅助脚本
│   ├── run_server.py          # 便捷的服务器启动脚本 (推荐)
│   ├── run_client.py          # 便捷的客户端启动脚本 (推荐)
│   └── build_package.sh       # 使用PyInstaller打包应用的脚本
├── config/                    # 默认配置文件目录
│   └── default_config.ini     # 项目的默认配置文件
├── tests/                     # 测试代码 (结构请根据实际情况填充)
│   #├── client/
│   #├── server/
│   #└── shared/
├── docs/                      # 项目文档
├── pyproject.toml             # 项目元数据和依赖 (如果使用)
└── README.md                  # 项目顶层README
```

## 测试指南

### 测试结构

测试代码组织如下：

```
tests/
├── client/  # 客户端测试
│   ├── unit/  # 单元测试
│   └── integration/  # 集成测试
├── server/  # 服务器测试
│   ├── unit/  # 单元测试
│   └── integration/  # 集成测试
├── shared/  # 共享模块测试
├── fixtures/  # 测试数据
├── conftest.py  # 全局测试夹具
└── pytest.ini  # 测试配置
```

### 运行测试

运行所有测试：
```bash
cd nextalk
python -m pytest
```

运行特定测试组：
```bash
python -m pytest tests/client  # 运行所有客户端测试
python -m pytest tests/server/unit  # 仅运行服务器单元测试
```

生成覆盖率报告：
```bash
python -m pytest --cov=src --cov-report=term-missing
```

### 编写测试

- 使用 `pytest` 框架
- 对于异步代码，使用 `pytest-asyncio`
- 测试文件命名为 `test_*.py`
- 测试函数命名为 `test_*`
- 利用 `conftest.py` 中的夹具

示例：
```python
def test_vad_filter_silence(silence_frame):
    """测试VAD对静音帧的处理"""
    from nextalk_server.audio.vad import VADFilter
    
    vad = VADFilter(sensitivity=2)
    assert vad.is_speech(silence_frame) is False
```

## 代码风格指南

本项目使用 `ruff` 进行代码格式化和静态分析。

### 代码风格规则

- 行长度限制为 100 字符
- 使用 4 空格缩进
- 遵循 PEP 8 命名规范
- 导入顺序：标准库、第三方库、本地模块

### 运行代码检查

```bash
cd nextalk
ruff check .  # 检查代码
ruff format .  # 格式化代码
```

## 贡献流程

### 贡献步骤

1. Fork 仓库并克隆到本地
2. 创建新的特性分支 (`git checkout -b feature/my-feature`)
3. 编写代码和测试
4. 确保所有测试通过 (`pytest`)
5. 确保代码符合风格要求 (`ruff check .`)
6. 提交更改 (`git commit -am '添加新特性'`)
7. 推送到分支 (`git push origin feature/my-feature`)
8. 创建 Pull Request

### 提交规范

提交消息应当包含清晰的描述，建议使用以下前缀：

- `feat:`：新功能
- `fix:`：bug修复
- `docs:`：文档修改
- `style:`：代码格式修改
- `refactor:`：代码重构
- `test:`：添加测试
- `chore:`：更新构建任务、包管理器配置等

示例：`feat: 添加模型切换功能`

## FunASR集成指南

FunASR 是 NexTalk 支持的核心语音识别引擎，特别适合中文和多语言识别场景。NexTalk 服务器通过 `nextalk_server/funasr_model.py` 中的 `FunASRModel` 类深度集成了 FunASR。

### FunASR 支持的模型组件

NexTalk 利用 FunASR 的多个组件来实现高质量的语音识别：

1.  **ASR 模型 (Automatic Speech Recognition)**:
    *   **离线模型 (`_model_asr`)**: 用于对完整的语音片段进行高精度识别。默认模型通常在 `nextalk_shared.constants` (例如 `FUNASR_OFFLINE_MODEL`) 中定义，并在服务器配置中指定。
    *   **在线/流式模型 (`_model_asr_streaming`)**: 用于实时语音识别，逐块处理音频并快速返回结果。默认模型同样在常量和配置中定义 (例如 `FUNASR_ONLINE_MODEL`)。
2.  **VAD 模型 (Voice Activity Detection)**:
    *   `_model_vad`: 用于检测语音活动，过滤静默片段，提高识别效率和准确性。默认模型在常量中定义 (例如 `FUNASR_VAD_MODEL`)，并通过服务器配置加载。
3.  **标点模型 (`PuncModel`)**:
    *   `_model_punc`: 用于在识别结果中自动添加标点符号，使文本更具可读性。默认模型在常量中定义 (例如 `FUNASR_PUNC_MODEL`)，并通过服务器配置加载。

具体的模型名称（如 `paraformer-zh`, `SenseVoiceSmall` 等）通过服务器配置文件传递给 `FunASRModel` 进行加载。

### 开发依赖

在开发涉及 FunASR 的功能时，需要安装 FunASR 库：

```bash
# 假设 funasr 已作为项目核心依赖安装
# uv pip install funasr
# 或者 pip install funasr
```
FunASR 的依赖可能较多，建议在专用虚拟环境中进行开发和运行。

### 集成核心：`FunASRModel`

FunASR 的集成主要在 `nextalk_server/funasr_model.py` 中的 `FunASRModel` 类实现。该类负责：

-   **模型加载与管理**: 根据服务器配置动态加载和初始化上述提到的 ASR、VAD 和标点模型。
-   **配置驱动**: 支持通过配置文件指定模型名称、设备（CPU/CUDA）、模型版本 (`model_revision`) 等。
-   **异步处理**: 使用 `ThreadPoolExecutor` 将 FunASR 的计算密集型操作移至工作线程，避免阻塞服务器的异步事件循环。
-   **模型预热与预加载**: 
    -   **预热**: 在模型初始化后，会尝试使用简短的测试数据对各个模型组件进行预热，以减少首次实际请求时的延迟。
    -   **预加载**: `scripts/run_server.py` 脚本支持在 uvicorn 服务器启动前完全初始化 `FunASRModel` 实例，并通过 `set_preloaded_model` 使其可用于 FastAPI 应用。这显著减少了服务器启动后的模型加载等待时间。
-   **流式识别**: 提供 `process_audio_chunk` 方法处理实时音频流。
-   **离线识别**: 提供 `process_audio_offline` 方法处理完整的音频片段。
-   **资源管理**: 提供 `release` 方法用于在服务器关闭时释放模型占用的资源。

### 模型缓存与下载

FunASR 模型通常在首次使用时会自动从其默认的 ModelScope 源（或其他已配置的源，如 HuggingFace）下载到本地缓存目录。默认缓存路径一般是用户主目录下的 `~/.cache/modelscope/hub` 或类似路径。可以通过 FunASR 自身支持的环境变量（如 `MODELSCOPE_CACHE`）来影响缓存行为。 `scripts/run_server.py` 脚本也可能通过 `--model-path` 参数指定模型搜索路径，或通过设置 `MODEL_HUB` 环境变量（如 `modelscope` 或 `hf`）来指定模型来源。

### 测试 FunASR 功能

测试 FunASR 相关功能时，需要注意：
-   确保开发环境中已正确安装 FunASR 及其依赖。
-   服务器配置文件 (`config/default_config.ini` 或 `~/.config/nextalk/config.ini`) 中指向了正确的、可访问的模型名称。
-   如果使用 GPU (`device=cuda`)，确保 CUDA 环境已正确配置并与 FunASR 使用的 PyTorch 版本兼容。

## 常见问题解决

### 开发中的常见问题

1. **测试超时问题**
   - 对于WebSocket测试，可能需要增加超时时间
   - 使用 `@pytest.mark.asyncio(timeout=10)` 设置更长的超时

2. **GPU内存问题**
   - 开发时如遇GPU内存不足，可在配置中设置 `device=cpu`
   - 或使用较小的模型（如 `tiny.en` 或 `SenseVoiceSmall`）进行开发

3. **音频设备权限问题**
   - 确保用户在 `audio` 组中
   - 使用 `aplay -l` 和 `arecord -l` 验证设备访问权限

4. **FunASR相关问题**
   - 如果遇到ImportError，确保已安装funasr库：`pip install funasr`
   - 如果遇到模型下载问题，可以手动下载模型到`~/.cache/NexTalk/funasr_models`目录
   - FunASR模型可能会在第一次使用时自动下载，需要确保网络连接良好
   - 使用`ASRRecognizer`类时注意导入检查，避免强制依赖FunASR库

### 调试技巧

- 使用标准库的 `logging` 模块记录详细信息
- 服务器端设置环境变量 `LOG_LEVEL=DEBUG`
- 客户端使用 `--debug` 参数启动，输出更多日志信息
- WebSocket通信问题可使用浏览器开发工具的网络面板检查
- 对于FunASR问题，可设置环境变量 `FUNASR_LOG_LEVEL=DEBUG` 查看更详细的模型日志

## 打包与分发

NexTalk 提供了使用 PyInstaller 打包客户端和服务器为独立可执行文件的脚本。

### 前提条件

-   确保已安装 `PyInstaller`。如果未安装，请在您的虚拟环境中运行：
    ```bash
    pip install pyinstaller
    ```

### 打包脚本

项目根目录下的 `scripts/build_package.sh` 脚本用于执行打包操作。

### 打包客户端

要仅打包客户端：

```bash
cd /path/to/nextalk  # 进入项目根目录
bash scripts/build_package.sh
```

这将会：
1.  在 `dist/` 目录下创建一个名为 `nextalk_client` (或类似名称) 的可执行文件。
2.  客户端被打包为单文件、窗口化应用。
3.  `src/nextalk_client/ui/assets` 目录中的资源文件会被包含。
4.  默认配置文件 `config/default_config.ini` 会被复制到 `dist/config/`。
5.  在 `dist/` 目录下生成一个基础的 `README.txt`。

### 打包客户端和服务器

要同时打包客户端和服务器：

```bash
cd /path/to/nextalk  # 进入项目根目录
bash scripts/build_package.sh --with-server
```

这将在上述客户端打包的基础上，额外在 `dist/` 目录下创建一个名为 `nextalk_server` (或类似名称) 的服务器可执行文件。

### 输出

打包完成后，所有生成的文件都位于项目根目录下的 `dist/` 目录中。

**注意**: 打包过程依赖于当前激活的Python环境和已安装的库。确保在正确的虚拟环境中运行此脚本，且该环境包含了所有必要的运行时依赖。