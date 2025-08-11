# NexTalk User Guide

## Table of Contents

- [NexTalk User Guide](#nextalk-user-guide)
  - [Table of Contents](#table-of-contents)
  - [Basic Usage](#basic-usage)
    - [Launch Methods](#launch-methods)
      - [Using Dedicated Launch Scripts (Recommended)](#using-dedicated-launch-scripts-recommended)
      - [Launching as Python Module (Developer/Alternative)](#launching-as-python-module-developeralternative)
    - [Hotkey Operations](#hotkey-operations)
    - [Transcription Control](#transcription-control)
    - [System Tray Icon](#system-tray-icon)
    - [Notification System](#notification-system)
  - [Configuration Options](#configuration-options)
    - [\[Client\] Section (`~/.config/nextalk/client.ini`)](#client-section-confignextalk-clientini)
    - [\[Server\] Section (`~/.config/nextalk/server.ini`)](#server-section-confignextalk-serverini)
    - [Model Selection](#model-selection)
    - [Audio Settings](#audio-settings)
    - [UI Settings](#ui-settings)
  - [FunASR Advanced Features](#funasr-advanced-features)
    - [Recognition Modes (Implicit)](#recognition-modes-implicit)
    - [Hotword Optimization](#hotword-optimization)
    - [Punctuation Restoration](#punctuation-restoration)
    - [Voice Activity Detection (VAD)](#voice-activity-detection-vad)
  - [Advanced Features \& Customization](#advanced-features--customization)
    - [Multilingual Support](#multilingual-support)
    - [Performance Tuning (Server Side)](#performance-tuning-server-side)
    - [Client Behavior Customization](#client-behavior-customization)
    - [About "Simple Client"](#about-simple-client)
  - [Additional Resources](#additional-resources)

## Basic Usage

### Launch Methods

NexTalk provides flexible launch options. We recommend using the launch scripts in the project's `scripts` directory.

#### Using Dedicated Launch Scripts (Recommended)

**1. Launch Server:**

Open a terminal, navigate to NexTalk project root directory, then run (ensure your virtual environment is activated):

```bash
python scripts/run_server.py
```

The server will start running and listen on the address and port specified in the configuration file. On first run, if the configured FunASR models aren't downloaded yet, the server will attempt to download and cache them automatically.

*Common server launch parameters (`scripts/run_server.py`):*
- `--host <ip_address>`: Set server listening host address (default: `0.0.0.0`)
- `--port <port_number>`: Set server listening port (default: `8000`)
- `--device <cpu|cuda>`: Select compute device (default: `cuda` if available)
- `--model-path <path>`: Specify model cache/search path
- `--log-level <debug|info|warning|error>`: Set log level
- `--debug`: Quickly enable debug log level
- `--log-file <path/to/log>`: Output logs to file
- `--print-config`: Print current config and exit without starting server
- `--skip-preload`: Skip model preloading to speed up server startup (but first recognition request will be slower)

**2. Launch Client:**

Open another terminal, navigate to NexTalk project root directory, then run (ensure your virtual environment is activated):

```bash
python scripts/run_client.py
```

The client will attempt to connect to the server. Upon successful connection, you should see the system tray icon and can start using voice recognition via hotkeys.

*Common client launch parameters (`scripts/run_client.py`):*
- `--server-host <ip_address>`: Server host address to connect to (overrides `server_url` host in config)
- `--server-port <port_number>`: Server port to connect to (overrides `server_url` port in config)
- `--debug`: Quickly enable debug log level
- `--log-file <path/to/log>`: Output logs to file

#### Launching as Python Module (Developer/Alternative)

You can also run NexTalk directly as Python module:

**Launch Server:**
```bash
# (After activating virtual environment)
python -m nextalk_server.main
```
Or at lower level (typically for FastAPI app development):
```python
# (In Python script)
# from nextalk_server.app import app
# import uvicorn
# uvicorn.run(app, host="0.0.0.0", port=8000) # Adjust host and port as needed
```

**Launch Client:**
```bash
# (After activating virtual environment)
python -m nextalk_client.main
```

### Hotkey Operations

NexTalk uses global hotkeys to activate voice recognition. Default hotkeys are:

- `Ctrl+Shift+Space`: Start/stop voice recognition
- `Esc`: Cancel current transcription

You can customize these hotkeys in the configuration file.

### Transcription Control

NexTalk provides multiple transcription control modes:

- **Auto Mode**: Automatically detects speech start/end without manual control
- **Manual Mode**: Press hotkey to start recording, press again to stop and transcribe
- **Continuous Mode**: Continuously records and transcribes in real-time until manually stopped

### System Tray Icon

After NexTalk launches, it displays an icon in the system tray area. Right-clicking the tray icon allows you to:

- **View current status**: Icon indicates whether NexTalk is listening, processing or idle
- **Switch recognition models**: Quickly switch between configured models
- **Open settings** (if supported in future): Quick access to configuration options
- **Exit program**: Safely shutdown NexTalk client and server

### Notification System

NexTalk provides desktop notifications for important information, such as:

- **Error alerts**: E.g., failed server connection, model loading failures
- **Status changes**: E.g., started listening, stopped listening, successful model switch
- **Transcription results** (optional): Key transcription information or prompts

Notification display can be controlled via the `show_notifications` option in config file. Set to `false` to disable all desktop notifications.

## Configuration Options

NexTalk's main configuration is managed via `config.ini` file in user directory. You need to copy `config/default_config.ini` to `~/.config/nextalk/client.ini 和 ~/.config/nextalk/server.ini` first, then modify as needed.

Command line arguments can override some config file settings.

### [Client] Section (`~/.config/nextalk/client.ini 和 ~/.config/nextalk/server.ini`)

- `hotkey = ctrl+shift+space`
  * Defines global hotkey combination to activate/deactivate voice recognition. Supports formats like `alt+z`, `ctrl+alt+s`. Refer to `pynput` docs for available combinations.
- `server_url = ws://127.0.0.1:8000/ws/stream`
  * Specifies full WebSocket URL for NexTalk server. Modify if server is on another machine or using SSL (wss://).
- `show_notifications = true`
  * Whether to show desktop notifications. Set to `false` to disable all status change and error notifications.
- `use_ssl = false`
  * If `server_url` uses `wss://`, this is typically handled automatically but can be explicitly set to `true` to enforce SSL behavior.
- `enable_focus_window = true`
  * When `xdotool` text injection fails, whether to enable fallback `SimpleWindow` (a topmost simple text window) to display recognition results. Set to `false` to disable this fallback.
- `focus_window_duration = 5`
  * If `enable_focus_window` is `true`, this sets how long (seconds) the `SimpleWindow` displays text before automatically fading/hiding.

### [Server] Section (`~/.config/nextalk/client.ini 和 ~/.config/nextalk/server.ini`)

- `host = 0.0.0.0`
  * Server listening host address. `0.0.0.0` listens on all available network interfaces; `127.0.0.1` listens only on local loopback.
- `port = 8000`
  * Server listening TCP port.
- `device = cuda`
  * Primary compute device for FunASR models. Options: `cuda` (recommended, uses NVIDIA GPU) or `cpu`. If `cuda` is selected but no GPU available, FunASR typically falls back to `cpu` (with warning).
- `ngpu = 1`
  * (FunASR parameter) When `device = cuda`, specifies number of GPUs to use. Typically set to `1`.
- `ncpu = 4`
  * (FunASR parameter) Number of CPU cores FunASR can utilize for certain operations. Increasing may help CPU-intensive tasks but should be adjusted based on actual hardware.
- `model_path = ~/.cache/NexTalk/funasr_models` (example, actual default may be determined by FunASR)
  * (Optional) Specifies root directory for FunASR model download/cache. If unset or unrecognized by FunASR, it typically uses internal default cache path (e.g., `~/.cache/modelscope/hub`). `scripts/run_server.py` also supports setting this via `--model-path` command line argument.
- `asr_model = iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`
  * Specifies primary FunASR speech recognition (ASR) model. This is the core model for speech-to-text conversion. You can find available FunASR model names on ModelScope (modelscope.cn). For example, `FUNASR_OFFLINE_MODEL` or `FUNASR_ONLINE_MODEL` in `nextalk_shared/constants.py` may define recommended defaults.
- `asr_model_revision = None`
  * (Optional) Specifies specific version of ASR model (e.g., git commit hash or branch name). If `None` or unspecified, uses model's default/latest version.
- `asr_model_streaming = None`
  * (Optional) If you want to use a different, streaming-optimized model for streaming recognition, specify its name here. If `asr_model` itself supports efficient streaming, this may not be needed or should match `asr_model`.
- `asr_model_streaming_revision = None`
  * (Optional) Specific version for `asr_model_streaming`.
- `vad_model = iic/speech_fsmn_vad_zh-cn-16k-common-pytorch`
  * Specifies FunASR voice activity detection (VAD) model. Used to detect valid speech segments in audio streams, filtering background noise and silence. `nextalk_shared/constants.py`'s `FUNASR_VAD_MODEL` may have default value.
- `vad_model_revision = None`
  * (Optional) Specific version for VAD model.
- `punc_model = iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch`
  * Specifies FunASR punctuation restoration model. Automatically adds punctuation marks (commas, periods, question marks etc.) to raw text output from ASR engine, making it more natural and readable.
- `punc_model_revision = None`
  * (Optional) Specific version for punctuation model.
- `funasr_hotwords =`
  * (Optional) Hotword list to improve recognition accuracy for specific words/phrases. Typically one hotword per line or specific delimiter. Refer to FunASR docs or `FunASRModel` implementation for exact format. Example:
    ```ini
    funasr_hotwords = NexTalk
                      FunASR
                      CustomTerm
    ```

**Important Note**: Above list explains main configuration items. Some defaults may be hardcoded in code (e.g., `nextalk_server/config.py`, `nextalk_client/config/loader.py`, `nextalk_shared/constants.py`). Always refer to `config/default_config.ini` as authoritative config template, and consult code behavior to understand each option's exact effect.

### Model Selection

You can select different speech recognition models in config file:

```ini
[server]
# Whisper model options: tiny, base, small, medium, large, large-v3, distil-large-v3
# FunASR model options: paraformer-zh, paraformer-zh-streaming, SenseVoiceSmall
default_model = large-v3
# Options: cpu, cuda
device = cuda
```

Whisper model comparison:
- `tiny`: Smallest, fastest, lowest accuracy
- `base`/`small`: Balanced speed and accuracy
- `medium`/`large`: High accuracy but more resource-intensive
- `large-v3`/`distil-large-v3`: Latest models supporting more languages

FunASR model comparison:
- `paraformer-zh`: Standard Chinese model, higher accuracy, moderate speed
- `paraformer-zh-streaming`: Streaming Chinese model, better real-time performance
- `SenseVoiceSmall`: Small general-purpose model, low resource usage, fast

Selection recommendations:
- For Chinese recognition, recommend FunASR's `paraformer-zh` or `paraformer-zh-streaming`
- For English/multilingual, recommend Whisper's `large-v3` or `medium`
- On resource-constrained devices, choose smaller models like Whisper's `small` or FunASR's `SenseVoiceSmall`

Besides config file, you can quickly switch between already-loaded or server-supported recognition models via the **system tray icon menu**.

### Audio Settings

Adjust audio settings for optimal recognition:

```ini
[audio]
# Audio backend (pulseaudio, alsa, portaudio)
audio_backend = pulseaudio
# Sample rate (16000 recommended)
sample_rate = 16000
# Channels (1=mono)
channels = 1
```

### UI Settings

Client UI and behavior settings:

```ini
[client]
# Server connection
server_host = 127.0.0.1
server_port = 8765
# Transcription result display time (seconds)
notification_timeout = 5
# Auto-type text to active window
auto_type = true
# Enable focus window as fallback when text injection fails (true/false)
enable_focus_window = true
# Focus window display duration (seconds)
focus_window_duration = 5
```

**Focus Window**:

When `auto_type` is `true` but `xdotool` text injection fails, if `enable_focus_window` is also `true`, NexTalk will attempt to display transcribed text in a topmost semi-transparent "focus window". This window typically appears at screen bottom and automatically fades after `focus_window_duration` seconds. Ensures you can still see recognition results even when direct input to target app fails.

## FunASR Advanced Features

NexTalk encapsulates various FunASR advanced features via server-side `FunASRModel`. These are primarily controlled through server config file (`~/.config/nextalk/client.ini 和 ~/.config/nextalk/server.ini` [Server] section).

### Recognition Modes (Implicit)

FunASR supports multiple internal modes like offline (full-sentence recognition) and online (streaming). NexTalk's `FunASRModel` implicitly utilizes these based on loaded models (e.g., specified via `asr_model` and `asr_model_streaming` configs) and audio data reception method (single complete chunk vs. continuous small chunks).

- **Streaming**: When client sends continuous small audio chunks, server-side `FunASRModel` (if streaming model loaded) performs streaming processing, potentially returning intermediate/final results in real/near-real time.
- **Offline**: If receiving larger/complete audio segments, or if configured with offline-only model, performs more sentence-oriented recognition, typically more accurate but with higher latency.

Users generally don't need to directly switch these underlying modes, but rather select appropriate FunASR models (in server config) and usage patterns to get desired recognition behavior.

### Hotword Optimization

By setting `funasr_hotwords` in server config [Server] section, you can provide a hotword list to improve recognition accuracy for specific words, phrases or technical terms. FunASR gives these hotwords higher weight during recognition.

**Config Example (`config.ini`):**
```ini
[Server]
# ... other server configs ...
funasr_hotwords =
    NexTalk
    FunASR Pipeline
    CustomProductName
    DomainSpecificTerm
```
One hotword/phrase per line. Refer to FunASR official docs for more on hotword formats and best practices.

### Punctuation Restoration

By specifying `punc_model` in server config (e.g., `iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch`), you enable automatic punctuation restoration. FunASR automatically adds commas, periods, question marks etc. to raw ASR output text, making it more natural and readable.

If punctuation restoration isn't needed, leave `punc_model` config empty or commented out.

### Voice Activity Detection (VAD)

Server config's `vad_model` (e.g., `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch`) specifies model for voice activity detection. VAD helps system distinguish speech from non-speech segments (like silence, background noise), only passing speech-containing audio to ASR engine. This reduces unnecessary computation, improves recognition efficiency, and in some cases enhances accuracy.

## Advanced Features & Customization

### Multilingual Support

FunASR natively supports multiple languages. NexTalk's multilingual support mainly depends on which FunASR model you select for `asr_model` (and related VAD/punctuation models if language-specific versions needed) in server config.

For example, to recognize English, you need an English FunASR ASR model. For Chinese, select Chinese model. Check ModelScope's FunASR model list for models suited to your target language, and configure in `config.ini`.

### Performance Tuning (Server Side)

- **Device selection (`device`)**: For production or low-latency scenarios, strongly recommend `cuda` (NVIDIA GPU). CPU inference is much slower.
- **Model selection**: Different FunASR models trade off between speed, accuracy and resource usage. Larger models typically more accurate but slower/resource-heavy. Streaming models usually lower latency.
- **Preloading & warmup**: `scripts/run_server.py` preloads/warms up models by default, increasing server startup time but significantly reducing first-request latency. For development or non-immediate-response needs, consider `--skip-preload` server launch.
- **CPU cores (`ncpu`)**: When running on CPU or with limited GPU, adjusting `ncpu` may help improve FunASR processing speed, but requires testing on specific hardware.

### Client Behavior Customization

- **Hotkeys (`hotkey`)**: Customize hotkeys to fit your workflow.
- **Injection fallback (`enable_focus_window`, `focus_window_duration`)**: Configure simple text window behavior when `xdotool` injection fails.

### About "Simple Client"

Older docs may mention `use_simple_client` config. Check current `client_logic.py` and related UI code to confirm if this option remains valid, or if its functionality has been replaced/removed. If no longer used, ignore this config.

## Additional Resources

- Installation Guide: See [setup_guide.md](setup_guide.md) for complete installation instructions
- Project Architecture: See [architecture.md](architecture.md) for NexTalk's technical architecture
- Contribution Guide: See [developer_guide.md](developer_guide.md) for how to contribute to project development