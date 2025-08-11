# NexTalk - Real-time Speech Recognition System

[中文版](README_zh.md)

NexTalk is a lightweight real-time local speech recognition and input solution with FunASR as its core engine. It consists of a server (`nextalk_server`) and client (`nextalk_client`) that communicate efficiently via WebSocket.

Refer to detailed documentation in the [docs/](docs/) directory:
- [User Guide (user_guide.md)](docs/user_guide.md)
- [Setup Guide (setup_guide.md)](docs/setup_guide.md) 
- [Architecture Overview (architecture.md)](docs/architecture.md)
- [Developer Guide (developer_guide.md)](docs/developer_guide.md)

## Key Features

- **Real-time Speech Recognition**: Powered by FunASR, supporting high-quality Chinese and multilingual speech-to-text.
- **Streaming & Offline Processing**: Server intelligently uses streaming (low latency) or offline (high accuracy) recognition based on model configuration and audio stream characteristics.
- **Voice Activity Detection (VAD)**: Integrated FunASR VAD effectively filters silence and noise.
- **Punctuation Restoration**: Automatically adds punctuation to recognized text.
- **Hotword Optimization**: Supports custom hotwords via config file to improve recognition of specific terms.
- **Client Integration**: Provides client implementation for audio capture, text injection (using `xdotool` on Linux), system tray interaction and hotkey control.
- **WebSocket Communication**: Efficient real-time audio and result transmission.
- **Multi-platform Support**: Both server and client are Python-based, with client UI and injection currently targeting Linux.
- **Flexible Configuration**: Rich server and client configuration options via separate INI files (`~/.config/nextalk/server.ini` and `~/.config/nextalk/client.ini`).
- **GPU/CPU Support**: FunASR models can run on GPU (CUDA) or CPU.

## Core Components

- **`nextalk_server` (Server)**:
  - **FastAPI App (`app.py`)**: Web service framework managing application lifecycle.
  - **WebSocket Endpoint (`websocket_routes.py`)**: Handles client connections and data exchange on `/ws/stream`.
  - **`FunASRModel` (`funasr_model.py`)**: FunASR core engine wrapper handling model loading, management, warmup and inference (ASR, VAD, Punc).
  - **Config Module (`config.py`)**: Loads and provides server configuration.
  
- **`nextalk_client` (Client)**:
  - **`NexTalkClient` (`client_logic.py`)**: Core client logic, state management, server interaction.
  - **Audio Capture (`audio/capture.py`)**: Uses PyAudio to capture microphone audio.
  - **Text Injection (`injection/`)**: Inputs text to active window.
  - **UI Components (`ui/`)**: System tray (`tray_icon.py`), notifications (`notifications.py`), alternate text display (`simple_window.py`).
  - **Hotkey Listener (`hotkey/listener.py`)**: Global hotkey support.

- **`nextalk_shared` (Shared Module)**:
  - **Data Models (`data_models.py`)**: Pydantic models for WebSocket communication.
  - **Constants (`constants.py`)**: Project-wide shared constants.

## Quick Start

### 1. Environment Setup & Installation

Refer to detailed [Setup Guide (docs/setup_guide.md)](docs/setup_guide.md). Brief steps:

- Clone repository
- Install Python 3.10+
- Install system dependencies (e.g. `xdotool`, `portaudio19-dev`, `python3-tk`)
- Create virtual environment (recommend using `uv` or `venv`)
- Install project dependencies in virtual environment:
  ```bash
  # Using uv (recommended, assumes pyproject.toml defines dev extra)
  uv pip install -e ".[dev]"
  # Or using pip
  # pip install -e ".[dev]"
  ```
  This will install core dependencies including `funasr`.

### 2. Configuration

- Copy `config/default_config.ini` to `~/.config/nextalk/client.ini` and `~/.config/nextalk/server.ini`
- Edit configuration files per your needs (details in User Guide and Setup Guide)

### 3. Running NexTalk

**Start Server:**
In project root, activate virtual environment and run:
```bash
python scripts/run_server.py
```
Server will load models and start listening (default: `0.0.0.0:8000`).

**Start Client:**
In another terminal at project root, activate virtual environment and run:
```bash
python scripts/run_client.py
```
Client will connect to server. You can then use hotkey (default: `Ctrl+Shift+Space`) for speech recognition.

## WebSocket API (`ws://<host>:<port>/ws/stream`)

Client communicates with server via this WebSocket endpoint.

- **Main Interaction Flow**:
  1. Client connects to server's `/ws/stream` endpoint
  2. After successful connection, client can trigger audio capture via hotkey etc.
  3. Client streams captured audio chunks (typically PCM 16kHz, 16-bit, mono) to server in real-time
  4. Server (`FunASRModel`) processes audio stream for VAD, ASR and punctuation restoration
  5. Server sends recognition results (intermediate and final) back to client as JSON messages

- **Example Recognition Result**:
  Client receives messages typically in JSON format that can be parsed for recognized text.
  ```javascript
  // Client JavaScript example
  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "transcription" && data.text) {
        console.log("Recognition result:", data.text);
        if (data.is_final) {
          console.log("This is final result.");
          // Use data.text for text injection or other processing
        }
      } else if (data.type === "status") {
        console.log("Server status:", data.status, data.message || "");
      } else if (data.type === "error") {
        console.error("Server error:", data.message);
      }
    } catch (e) {
      console.error("Failed to parse received message:", event.data, e);
    }
  };
  ```
  Actual data models are defined in `nextalk_shared/data_models.py` (e.g. `TranscriptionResponse`, `StatusUpdate`, `ErrorMessage`).

- **Control Commands & Parameter Configuration**:
  Current version primarily uses server startup config file (`~/.config/nextalk/server.ini`) and command line arguments for FunASR model and parameter configuration. Any dynamic control commands via WebSocket (e.g. runtime model switching, dynamic hotword modification) are encapsulated in internal protocol and not highlighted as main public API features in this documentation. Main interaction is audio streaming and transcription results.

## `scripts/run_server.py` Main Command Line Arguments

Common arguments for server startup script `scripts/run_server.py`:

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
                     # ... Other FunASR direct parameters may be passed via kwargs ...
```
- `--host`: Server host address (default: `0.0.0.0`)
- `--port`: Server port (default: `8000`)
- `--device`: Compute device (`cpu` or `cuda`, default: `cuda`)
- `--log-level`: Logging level
- `--model-path`: Model cache/search path
- `--asr-model`: Main FunASR ASR model name
- `--vad-model`: VAD model name
- `--punc-model`: Punctuation model name
- `--skip-preload`: Skip model preloading
- `--print-config`: Print config and exit

For more detailed parameter explanations and configuration methods, refer to [User Guide (docs/user_guide.md)](docs/user_guide.md) and [Setup Guide (docs/setup_guide.md)](docs/setup_guide.md).

## Contributing

Contributions welcome! Please read [Developer Guide (docs/developer_guide.md)](docs/developer_guide.md) for development environment setup, code style and contribution process.