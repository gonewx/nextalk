# Product Requirements Document (PRD): Nextalk

[简体中文](prd_zh.md) | English

## 1. Goals and Background Context

### Goals
* **Build a benchmark voice input experience for Linux**: Fill the gap of lacking high-quality, modern voice input tools on Linux desktop.
* **Achieve "ultimate transparency" visual effect**: Utilize Flutter rendering capabilities to provide borderless, background-artifact-free, breathing-animation modern floating window UI.
* **Ensure privacy and high performance**: Integrate Sherpa-onnx offline models, ensuring voice data never leaves the local machine; text commit path latency < 20ms, streaming recognition real-time factor (RTF) < 1.
* **Enable "speak-to-type" fluid interaction**: Implement VAD (endpoint detection) for automatic sentence breaks and text submission.
* **Seamless Fcitx5 integration**: Stable communication with input method framework via lightweight C++ plugin and Unix Domain Socket; degrade to clipboard fallback when Fcitx5 is unavailable.

### Background Context
Linux users lack beautiful and practical voice input tools. This project **Nextalk** leverages Sherpa-onnx's offline capabilities and Flutter's excellent rendering capabilities to build a productivity tool. The project uses Monorepo structure, containing Fcitx5 C++ plugin (backend) and Flutter client (frontend).

### Change Log
| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-12-21 | 1.0 | Official release: Lock Flutter+Sherpa solution, confirm C++ plugin ready | PM (John) |
| 2025-12-28 | 1.1 | SCP-002: Hotkey scheme changed to system native shortcuts, added clipboard fallback | PM (John) |
| 2026-07-09 | 1.2 | Aligned with v0.2.8 codebase: dual-engine ASR (SenseVoice default), silero VAD, libpulse-simple audio stack, new model management / error handling / i18n / device selection / packaging requirements (FR8–FR12), NFR1/NFR2 corrections, Epic list synced to epics.md | PM (John) |

## 2. Requirements

### 2.1 Functional Requirements

* **FR1 [UI/Interaction]: Floating Capsule Window**
    * App hidden by default after launch, tray icon displayed.
    * When activated, shows borderless, true-transparent capsule window.
    * **Real-time Feedback**: Recognized text appears in preview area in real time (character by character with the streaming engine; per VAD segment with the offline engine).
* **FR2 [Core]: Speech Recognition (ASR) — Dual-Engine Architecture** *(v1.2 update, Story 2-7)*
    * **SenseVoice offline engine (default)**: Recognizes whole segments after VAD segmentation; high accuracy, multilingual, supports ITN (inverse text normalization).
    * **Zipformer streaming engine (optional)**: `sherpa-onnx-streaming-zipformer-bilingual-zh-en`, recognize-while-listening, low latency; available in `int8` (fast) / `standard` (accurate) variants.
    * Engine and model variant are **hot-switchable** via tray menu, no app restart required.
    * **Audio Capture**: 16k mono; primary path `libpulse-simple` (device names match system settings, automatic resampling, PipeWire/PulseAudio integration), fallback path PortAudio (non-PulseAudio systems).
* **FR3 [Core]: Intelligent Endpoint Detection** *(v1.2 update)*
    * **SenseVoice path (default)**: Uses a standalone **silero VAD model** (`silero_vad.onnx`, loaded via sherpa-onnx VAD API) for speech segmentation; segmented recognition depends on VAD speech segments.
    * **Zipformer path**: Uses sherpa-onnx built-in endpoint rules (rule1/2/3); silero VAD is not loaded.
    * Both paths behave consistently: preview text is auto-submitted when a silence pause is detected.
* **FR4 [Integration]: Text Submission**
    * Client connects to `$XDG_RUNTIME_DIR/nextalk-fcitx5.sock` via Unix Domain Socket.
    * Protocol: `[4-byte length (LE)] + [UTF-8 text]`.
    * Text is committed to Fcitx5's most recent input context (`mostRecentInputContext`); the former "focus lock" mechanism was removed with SCP-002.
    * **Text Preservation**: On submission failure, recognized text is preserved with copy/retry support (Story 3-7).
    * Direct Fcitx5 interface submission, no ydotool fallback needed.
* **FR5 [System]: Tray Management** *(v1.2 expanded)*
    * Window show/hide/exit.
    * Engine and model variant switching, audio input device selection, UI language switching, open config directory.
* **FR6 [System]: Global Hotkey**
    * **Logic**: Press to wake/start recording; press again to stop/submit/hide.
    * **Implementation**: System native shortcuts (e.g., GNOME Settings → Keyboard → Custom Shortcuts) bound to `nextalk --toggle`; the app also provides `--show`/`--hide` commands.
    * Single-instance mechanism: a new process forwards the command to the running instance via an internal Unix Socket.
    * > **SCP-002 Change**: Original Fcitx5 plugin-side hotkey listening removed; the app itself performs no global key listening (hotkey hint text in the UI comes from built-in app defaults).
* **FR7 [System]: Clipboard Fallback** *(SCP-002 New)*
    * When the Fcitx5 plugin is unavailable (socket missing or submission fails), recognized text is automatically copied to the system clipboard.
    * UI shows prompt: "Copied to clipboard, please paste"; window auto-hides after 2 seconds.
* **FR8 [Core]: Model Management** *(v1.2 New)*
    * Models use a **download-on-first-run** strategy, stored at `$XDG_DATA_HOME/nextalk/models` (default `~/.local/share/nextalk/models`).
    * Manages three model classes: Zipformer (int8/standard), SenseVoice, and silero VAD.
    * Default download source is GitHub Releases (k2-fsa/sherpa-onnx); custom download URL supported via config file.
    * Downloads must show progress and support cancellation; integrity is verified after download — corrupted files must not enter the loading flow.
* **FR9 [System]: Init Wizard and Error Handling** *(v1.2 New, Story 3-7)*
    * First run provides an initialization wizard (model download, Fcitx5 plugin detection, hotkey setup guidance).
    * The following failures must be handled visibly: microphone missing/occupied, model missing or corrupted, model download interruption, Fcitx5 plugin not loaded, socket disconnection.
    * Fatal errors raise an error dialog with recovery guidance; non-fatal errors are expressed via state indicators on the capsule UI.
* **FR10 [System]: Internationalization** *(v1.2 New, Story 3-8)*
    * UI supports Simplified Chinese and English, switchable via tray menu with immediate effect.
* **FR11 [System]: Audio Input Device Selection** *(v1.2 New, Story 3-9)*
    * Select audio input device via tray menu; device list matches system settings (libpulse enumeration).
    * Provides `nextalk audio` CLI subcommand (interactive selection, `--list` machine-readable listing, direct set by index).
* **FR12 [Distribution]: Packaging and Delivery** *(v1.2 New, Epic 4)*
    * Provides DEB/RPM packaging scripts, install/uninstall scripts, desktop integration (.desktop, icons, autostart).
    * Provides Docker cross-distro compatible build environment.

### 2.2 Non-Functional Requirements
* **NFR1 [Performance]** *(v1.2 corrected)*:
    * Text commit path (socket submission → Fcitx5 `commitString`) latency < 20ms.
    * Streaming recognition real-time factor RTF < 1 (processing a 100ms audio chunk must take < 100ms; target < 10ms on reference hardware).
    * UI animations remain smooth during recording (no perceptible frame drops).
* **NFR2 [Privacy]** *(v1.2 corrected)*: Recognition inference is fully offline; voice data never leaves the local machine. Network access is required only for one-time **initial model download**; custom URLs or manually placed model files enable fully offline deployment.
* **NFR3 [Compatibility]**: Compatible with Ubuntu 22.04+ (X11/Wayland native support; both shortcuts and text submission support Wayland).
* **NFR4 [Experience]**: Window launch without black frame flicker (based on C++ Runner modification).

## 3. UI Design Goals

> The single source of truth for UI specifications is [front-end-spec.md](front-end-spec.md); this section is a summary only.

* **Visual**: Minimalist capsule, dark semi-transparent background, white inner-glow border.
* **Size**: 400x120 (logical pixels), capsule height 60px.
* **Animations**: Ripple (EaseOutQuad curve expansion), Breathing (red dot rhythms with ripple), Cursor (1s period blink).

## 4. Technical Assumptions

* **Repository Structure**: Monorepo
    * `/addons`: Fcitx5 C++ plugin source.
    * `/voice_capsule`: Flutter client source.
    * `/libs`: Precompiled dynamic libraries (sherpa-onnx, onnxruntime).
* **Core Stack**:
    * Flutter (Dart) + Linux C++ Runner (Modified)
    * Sherpa-onnx C-API (streaming / offline / VAD interface groups) via Dart FFI
    * libpulse / libpulse-simple (primary) + PortAudio (fallback) via Dart FFI
    * Unix Domain Socket IPC

## 5. Epic List

> **Single source of truth**: [`_bmad-output/epics.md`](../_bmad-output/epics.md) (4 Epics; see that file for story details and acceptance criteria). This section is a summary only; status as of v0.2.8.
> Note: The formal entry for Story 3-7 (init wizard and error handling) is pending backfill into epics.md; it currently exists only in implementation-artifacts.

### Epic 1: IPC Bridge (The Bridge) — ✅ Complete
Core communication channel: Fcitx5 plugin integration, plugin install script, Dart Socket Client, Flutter project init.

### Epic 2: Speech Recognition Engine (The Brain) — ✅ Complete
Native library linking, PortAudio/Sherpa FFI bindings, model manager, audio-inference pipeline, VAD endpoint detection, multi-model ASR support (SenseVoice integration).

### Epic 3: Complete Product Experience (The Product) — 🟡 Wrapping up
Transparent capsule window, capsule UI components, state machine and animations, system tray, global hotkey, full business flow, init wizard and error handling, zh/en i18n, audio device selection (3-9 in review).

### Epic 4: Packaging and Distribution — ✅ Complete
DEB/RPM packaging scripts, install/uninstall scripts, desktop integration, Docker cross-distro build environment.
