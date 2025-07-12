# NexTalk System Architecture

This document details the NexTalk system architecture, including main components, data flow, technology stack choices, and system interaction methods.

## 1. System Overview

NexTalk is a lightweight real-time local speech recognition and input system that allows users to input text via voice to any application. The system consists of two main parts: client (`nextalk_client`) and server (`nextalk_server`), which communicate via WebSocket protocol.

### 1.1 Core Features

- Real-time audio capture and processing (client)
- High-quality speech recognition (server-side FunASR engine, supporting multiple models and languages)
- Low-latency text input to active applications (client, primarily using `xdotool`)
- Hotkey-controlled speech recognition activation/deactivation (client)
- System tray interface and status indicator (client)
- Configurable speech recognition models (server-side configuration, client may request or display via specific mechanisms)
- Alternative text display window (client `SimpleWindow`, used when injection fails)

### 1.2 System Architecture Diagram

```
+-----------------------+        WebSocket (/ws/stream)        +------------------------+
|                       |      Audio Data / Transcription     |                        |
|    NexTalk Client     | <---------------------------------> |    NexTalk Server      |
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

[Remaining sections to be translated...]

## 2. Main Components

The NexTalk system consists of the following main components:

### 2.1 Client Components (`nextalk_client`)

1.  **`NexTalkClient`** (`client_logic.py`):
    *   Core logic class of the client, coordinating interactions between all other client components.
    *   Manages overall client states (idle, connected, listening, processing, error, etc.).
    *   Handles various messages received from the server via WebSocket.
    *   Responds to user actions triggered by hotkeys and system tray icons.

2.  **`AudioCapturer`** (`audio/capture.py`):
    *   Responsible for capturing audio data from the system microphone.
    *   Implemented using PyAudio library.
    *   Supports device selection and audio parameter configuration via config file.

3.  **`WebSocketClient`** (`network/client.py`):
    *   Manages WebSocket connection with the server (typically connecting to `/ws/stream` endpoint).
    *   Responsible for sending audio chunks to the server and receiving transcription results, status updates, and error messages.

4.  **`Injector`** (`injection/`):
    *   Injects transcription text returned by the server into the currently active application window.
    *   Main implementation is `XdotoolInjector` (using `xdotool` command), specifically for Linux systems.
    *   Based on `BaseInjector` abstract base class, allowing future extensions for other platforms.

5.  **`SimpleWindow`** (`ui/simple_window.py`):
    *   Provides a simple always-on-top floating window.
    *   Serves as an alternative for text injection: when `xdotool` injection fails or is unavailable, transcription text will be displayed in this window.
    *   Ensures users can always see recognition results.

6.  **`HotkeyListener`** (`hotkey/listener.py`):
    *   Listens for global hotkey events (e.g., default `Ctrl+Shift+Space`).
    *   Implemented using `pynput` library.
    *   Used to activate or deactivate the speech recognition process (i.e., start/stop capturing and sending audio).

7.  **`SystemTrayIcon`** (`ui/tray_icon.py`):
    *   Displays NexTalk status icon and menu in the system tray area.
    *   Implemented using `pystray` library.
    *   Icon changes according to current client state (idle, listening, processing, error, etc.).
    *   Menu typically provides "Exit" option and may include other features (like opening settings or switching models, requires further confirmation).

8.  **`NotificationManager`** (`ui/notifications.py`):
    *   Responsible for displaying desktop notifications to users.
    *   Used to report important events such as connection errors, state changes, or critical recognition information.

9.  **Configuration Loader** (`config/loader.py`):
    *   Loads client configuration files (typically the `[Client]` section in `~/.config/nextalk/config.ini`).
    *   Provides configuration parameters for other client components.

### 2.2 Server Components (`nextalk_server`)

### 2.2 Server Components (`nextalk_server`)

1. **`NexTalkServer`** (`app.py`):
   * Core server class implemented using FastAPI framework.
   * Manages WebSocket connections and routes.
   * Handles client authentication and session management.
   * Coordinates interactions between different server components.

2. **`WebSocketHandler`** (`websocket_handler.py`):
   * Processes WebSocket connections from clients.
   * Receives audio chunks and sends back transcription results.
   * Implements connection state management and error handling.

3. **`AudioProcessor`** (`audio_processors.py`):
   * Processes incoming audio data from clients.
   * Performs audio format conversion and preprocessing.
   * Manages audio buffer and chunking for ASR processing.

4. **`FunASRModel`** (`funasr_model.py`):
   * Wrapper for FunASR speech recognition models.
   * Supports both streaming and offline recognition modes.
   * Handles model loading, inference, and resource management.

5. **`VADProcessor`** (`vad.py`):
   * Voice Activity Detection component.
   * Determines speech segments in audio stream.
   * Uses FSMN-VAD model from FunASR.

6. **`PunctuationModel`** (`punc.py`):
   * Post-processing component for adding punctuation.
   * Uses CT-PUNC model from FunASR.
   * Improves readability of transcription results.

7. **`ConfigManager`** (`config.py`):
   * Manages server configuration files.
   * Handles model paths, ASR parameters, and server settings.
   * Provides configuration to other server components.

8. **`ModelManager`** (`model_manager.py`):
   * Manages loading and switching of ASR models.
   * Supports multiple model types (Paraformer, SenseVoice, etc.).
   * Handles model versioning and updates.

9. **`MonitoringService`** (`monitoring.py`):
   * Collects and reports server performance metrics.
   * Tracks connection statistics and resource usage.
   * Provides health check endpoints.

10. **`LoggingService`** (`logging.py`):
    * Centralized logging system for the server.
    * Supports different log levels and output formats.
    * Integrates with monitoring system.