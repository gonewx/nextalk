# Product Requirements Document (PRD): Nextalk

[简体中文](prd_zh.md) | English

## 1. Goals and Background Context

### Goals
* **Build a benchmark voice input experience for Linux**: Fill the gap of lacking high-quality, modern voice input tools on Linux desktop.
* **Achieve "ultimate transparency" visual effect**: Utilize Flutter rendering capabilities to provide borderless, background-artifact-free, breathing-animation modern floating window UI.
* **Ensure privacy and high performance**: Integrate Sherpa-onnx offline model, ensuring data never leaves local machine, achieving <20ms input latency.
* **Enable "speak-to-type" fluid interaction**: Implement intelligent VAD (endpoint detection) for automatic sentence breaks and text submission.
* **Seamless Fcitx5 integration**: Stable communication with input method framework via existing lightweight C++ plugin and Unix Domain Socket.

### Background Context
Linux users lack beautiful and practical voice input tools. This project **Nextalk** leverages Sherpa-onnx's offline capabilities and Flutter's excellent rendering capabilities to build a productivity tool. The project uses Monorepo structure, containing existing Fcitx5 C++ plugin (backend) and new Flutter client (frontend).

### Change Log
| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-12-21 | 1.0 | Official release: Lock Flutter+Sherpa solution, confirm C++ plugin ready | PM (John) |
| 2025-12-28 | 1.1 | SCP-002: Hotkey scheme changed to system native shortcuts, added clipboard fallback | PM (John) |

## 2. Requirements

### 2.1 Functional Requirements

* **FR1 [UI/Interaction]: Floating Capsule Window**
    * App hidden by default after launch, tray icon displayed.
    * When activated, shows borderless, true-transparent capsule window.
    * **Real-time Feedback**: Text appears character by character in preview area as user speaks.
* **FR2 [Core]: Real-time Speech Recognition (ASR)**
    * **Model**: `sherpa-onnx-streaming-zipformer-bilingual-zh-en` (streaming bilingual).
    * **Capture**: 16k mono audio via Dart FFI + PortAudio.
* **FR3 [Core]: Intelligent Endpoint Detection (VAD)**
    * Uses Sherpa built-in VAD (default ~1.5s pause triggers).
    * Auto-submit preview text when silence detected.
* **FR4 [Integration]: Text Submission**
    * Client connects to `$XDG_RUNTIME_DIR/nextalk-fcitx5.sock` via Unix Domain Socket.
    * Protocol: `[4-byte length (LE)] + [UTF-8 text]`.
    * **Note**: Direct Fcitx5 interface submission, **no need** for ydotool fallback.
* **FR5 [System]: Tray Management**
    * Support show/hide/exit.
* **FR6 [System]: Global Hotkey**
    * **Logic**: Press to wake/start recording; press again to stop/submit/hide.
    * **Implementation**: System native shortcuts (e.g., GNOME Settings → Keyboard → Custom Shortcuts) + `nextalk --toggle` command.
    * > **SCP-002 Change**: Original Fcitx5 plugin-side hotkey listening removed, replaced with simpler system native shortcut scheme.
* **FR7 [System]: Clipboard Fallback** *(SCP-002 New)*
    * Auto-copy recognized text to system clipboard when Fcitx5 plugin unavailable.
    * UI shows prompt: "Copied to clipboard, please paste".
    * Auto-hide window after 2 seconds.

### 2.2 Non-Functional Requirements
* **NFR1**: End-to-end latency < 20ms.
* **NFR2**: Pure offline inference, no network requests.
* **NFR3**: Compatible with Ubuntu 22.04+ (X11/Wayland native support, shortcuts and text submission both support Wayland).
* **NFR4**: Window launch without black frame flicker (based on C++ Runner modification).

## 3. UI Design Goals

* **Visual**: Minimalist capsule, dark semi-transparent background, white inner-glow border.
* **Size**: 400x120 (logical pixels), capsule height 60px.
* **Animations**:
    * **Ripple**: EaseOutQuad curve expansion.
    * **Breathing**: Red dot rhythms with ripple.
    * **Cursor**: 1s period blink.

## 4. Technical Assumptions

* **Repository Structure**: Monorepo
    * `/addons`: Existing C++ Fcitx5 plugin source.
    * `/voice_capsule`: Flutter client source.
* **Core Stack**:
    * Flutter (Dart) + Linux C++ Runner (Modified)
    * Sherpa-onnx (C-API) via Dart FFI
    * PortAudio via Dart FFI
    * Unix Domain Socket IPC

## 5. Epic List and Details

### Epic 1: Plugin Integration and IPC (The Bridge)
**Status**: *Mostly complete, needs cleanup and integration*
* **Story 1.1 [Integration]**: Migrate existing `addons/fcitx5` code into project structure, configure CMake build flow.
* **Story 1.2 [Refactor]**: Clean up C++ code, remove `ydotool` fallback logic (per latest requirements).
* **Story 1.3 [Dev]**: Implement Dart-side Socket Client, verify communication with C++ plugin (send Hello World and display).
* **Story 1.4 [DevOps]**: Write `scripts/install_addon.sh` for one-click plugin compilation and installation.

### Epic 2: Hearing and Brain (The Brain)
**Status**: *To be developed*
* **Story 2.1 [Infra]**: Configure Flutter Linux build environment, link `libsherpa-onnx-c-api.so` and `libportaudio.so`.
* **Story 2.2 [FFI]**: Write Dart FFI Bindings, map Sherpa and PortAudio C functions.
* **Story 2.3 [Dev]**: Implement audio capture stream -> Sherpa inference stream data pipeline.
* **Story 2.4 [Dev]**: Implement VAD event listening and handling.

### Epic 3: Fusion and Delivery (The Product)
**Status**: *To be developed*
* **Story 3.1 [UI]**: Migrate verified Flutter UI code to main project.
* **Story 3.2 [Logic]**: Chain complete business flow: `Right Alt` -> recording -> recognition -> Socket submission.
* **Story 3.3 [Sys]**: Implement global hotkey listening (Rust FFI or C++ Runner extension).
* **Story 3.4 [Sys]**: Complete tray and window show/hide logic.
