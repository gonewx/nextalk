# UI/UX Specification: Nextalk

[简体中文](front-end-spec_zh.md) | English

| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-12-21 | 1.0 | Initial UI/UX spec (based on Flutter validation version) | UX Expert (Sally) |

## 1. Introduction

**Nextalk's** design philosophy is **"Invisible but Powerful"**.
It's not a traditional window that users stare at for long periods, but a **desktop spirit that comes when called and leaves when dismissed**. The UI must be extremely lightweight, minimally intrusive to the system, and provide delightful micro-interaction animations when it appears.

### Core Experience Goals
* **Zero Disruption**: Hidden by default, no taskbar occupation, only tray presence.
* **Instant Feedback**: Voice -> text conversion must have real-time visual flow.
* **Clear State**: Users can perceive "listening", "processing", or "sleeping" with peripheral vision.
* **Native Integration**: Window must perfectly blend into Linux desktop environment, no ugly system borders.

## 2. Visual Guidelines

### 2.1 Color Palette

We adopt a **Dark Mode Only** strategy, ensuring good contrast and tech feel across various wallpapers.

| Color Name | Hex / RGBA | Usage |
| :--- | :--- | :--- |
| **Capsule Bg** | `rgba(25, 25, 25, 0.95)` | Main capsule background, dark gray with slight transparency |
| **Accent Red** | `#FF4757` | **Core status color** (recording/breathing light) |
| **Text White** | `#FFFFFF` | Main text color |
| **Text Hint** | `#A4B0BE` | Hint text / cursor color |
| **Border Glow** | `rgba(255, 255, 255, 0.2)` | Inner glow border, enhances glass texture |
| **Shadow** | `rgba(0, 0, 0, 0.3)` | Soft outer shadow, provides floating feel |

### 2.2 Typography

* **Font Family**: Prefer `Segoe UI` (if available), fallback to system default sans-serif.
* **Size**: `18px` (main text).
* **Weight**: `500` (Medium).
* **Line Height**: `1.0` (compact, ensures vertical centering).

### 2.3 Dimensions

* **Window Size**: `400x120` (logical pixels, safe canvas including shadow area).
* **Capsule Size**:
    * Height: `60px` (fixed).
    * Min Width: `280px`.
    * Max Width: `380px` (content-adaptive).
* **Radius**: `40px` (fully rounded).
* **Padding**: `25px` left and right.

## 3. Core Screens

### 3.1 Main Capsule

This is the interface users see 99% of the time.

**State A: Listening (Active)**
* **Left**: Red solid circle (`#FF4757`, 30x30).
    * *Animation*: **Breathing** (Scale 1.0 -> 1.1 -> 1.0) + **Ripple expansion** (Opacity 0.6 -> 0, Scale 1.0 -> 3.0, Curve: EaseOutQuad).
* **Middle**: Real-time recognized text stream.
    * *Style*: White, single line, ellipsis for overflow.
    * *Dynamic*: Text appears character by character with voice, smooth scrolling.
* **Right**: Blinking cursor (`#A4B0BE`, 2px wide).
    * *Animation*: 1-second period Fade In/Out.

**State B: Processing (Submitting)**
* **Left**: Red dot changes to **spinning loader** or **rapid pulse**.
* **Middle**: Text color dims (`0.8` opacity), indicating submission in progress.

**State C: Error (No Permission)**
* **Left**: Changes to **yellow** (warning) or **gray** (no device).
* **Middle**: Shows error message (e.g., "Microphone unavailable").

### 3.2 First Run / Download Page

Triggered when no Sherpa model detected locally.

* **Layout**: Maintains capsule form, but may be slightly wider.
* **Content**:
    * Text: "Initializing model (45%)..."
    * Progress bar: Thin red progress bar (`#FF4757`) at capsule bottom or below text.
* **Interaction**: Cannot be closed, auto-switches to "Listening" or hides after download complete.

### 3.3 System Tray

* **Icon**: A minimalist microphone icon (monochrome or red accent).
* **Menu Items**:
    * **Nextalk** (disabled, title only)
    * ---
    * **Show / Hide**
    * **Settings...** (Post MVP)
    * ---
    * **Quit**

## 4. Interaction Flows

### 4.1 Wake & Speak
1. User presses configured hotkey (e.g., `Ctrl+Alt+V`).
2. Capsule window **instantly appears** (no fade, emphasizes speed) at screen center (or last remembered position).
3. Accompanied by a very light "Pop" sound effect (optional, Post MVP).
4. Left red light starts breathing, ripples start expanding.
5. User speaks -> text stream appears in real-time.

### 4.2 Auto Commit
1. VAD detects silence (>1.5s).
2. Red light stops breathing.
3. Text sent to Fcitx5 via Socket.
4. Window **instantly disappears**.

### 4.3 Manual Commit
1. User presses hotkey again.
2. Immediately stops recording.
3. Force submit current text.
4. Window disappears.

### 4.4 Drag to Move
1. User holds any blank area of capsule window.
2. Window follows mouse movement.
3. On release, records current position, next wake appears at this position.

## 5. Animation Specs

For development accuracy, here are specific Flutter animation parameters:

* **Wave (Ripple)**:
    * `Duration`: `1500ms`
    * `Curve`: `Curves.easeOutQuad` (burst feel)
    * `Scale`: `1.0` -> `3.0`
    * `Opacity`: `0.5` -> `0.0`
    * `Repeat`: Loop
* **Cursor**:
    * `Duration`: `800ms`
    * `Curve`: `Curves.easeInOut`
    * `Opacity`: `1.0` <-> `0.0`
    * `Repeat`: Reverse
* **Core Pulse (Red dot heartbeat)**:
    * `Formula`: `1.0 + 0.1 * sin(t)` (sine wave rhythm)

## 6. Error Handling UX

| Scenario | Visual Feedback | Behavior |
| :--- | :--- | :--- |
| **PortAudio Init Failure** | Left light turns gray, text shows "Audio device error" | Recording disabled, auto-hide after 3s |
| **Model Load Failure** | Text shows "Model corrupted, please restart" | Stays visible until user exits |
| **Socket Connection Lost** | Text shows "Fcitx5 not connected" | Attempts reconnect, allows recording but no submission |
