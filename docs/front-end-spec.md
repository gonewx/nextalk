# UI/UX Specification: Nextalk

[简体中文](front-end-spec_zh.md) | English

| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-12-29 | 2.0 | Complete UI/UX spec based on actual implementation | Tech Writer (Paige) |
| 2025-12-21 | 1.0 | Initial UI/UX spec (based on Flutter validation version) | UX Expert (Sally) |

## 1. Introduction

**Nextalk's** design philosophy is **"Invisible but Powerful"**.
It's not a traditional window that users stare at for long periods, but a **desktop spirit that comes when called and leaves when dismissed**. The UI must be extremely lightweight, minimally intrusive to the system, and provide delightful micro-interaction animations when it appears.

### Core Experience Goals

- **Zero Disruption**: Hidden by default, no taskbar occupation, only tray presence.
- **Instant Feedback**: Voice -> text conversion must have real-time visual flow.
- **Clear State**: Users can perceive "listening", "processing", or "sleeping" with peripheral vision.
- **Native Integration**: Window must perfectly blend into Linux desktop environment, no ugly system borders.

## 2. Visual Guidelines

### 2.1 Color Palette

We adopt a **Dark Mode Only** strategy, ensuring good contrast and tech feel across various wallpapers.

| Color Name | Hex / RGBA | Usage |
| :--- | :--- | :--- |
| **Capsule Bg** | `rgba(25, 25, 25, 0.95)` | Main capsule background, dark gray with slight transparency |
| **Background Dark** | `#1A1A1A` | Dialog background (fatal error dialog) |
| **Accent Red** | `#FF4757` | **Core status color** (recording/breathing light) |
| **Text White** | `#FFFFFF` | Main text color |
| **Text Hint** | `#A4B0BE` | Hint text / cursor color |
| **Text Processing** | `rgba(255, 255, 255, 0.8)` | Processing state text (dimmed) |
| **Border Glow** | `rgba(255, 255, 255, 0.2)` | Inner glow border, enhances glass texture |
| **Shadow** | `rgba(0, 0, 0, 0.3)` | Soft outer shadow, provides floating feel |
| **Warning** | `#FFA502` | Warning state indicator (yellow) |
| **Disabled** | `#636E72` | No device state indicator (gray) |
| **Success** | `#2ECC71` | Clipboard copy success indicator (green) |

### 2.2 Typography

- **Font Family**: System default sans-serif.
- **Primary Text Size**: `18px`.
- **Weight**: `500` (Medium).
- **Line Height**: `1.0` (compact, ensures vertical centering).

### 2.3 Dimensions

#### Main Capsule Window

| Property | Value | Description |
| :--- | :--- | :--- |
| Window Size | `400 × 120` px | Logical pixels, safe canvas including shadow area |
| Window Size (Expanded) | `400 × 180` px | Error state with action buttons |
| Capsule Height | `60` px | Fixed |
| Capsule Min Width | `280` px | Minimum content width |
| Capsule Max Width | `380` px | Maximum content width (adaptive) |
| Capsule Radius | `40` px | Fully rounded |
| Horizontal Padding | `25` px | Left and right padding |
| Indicator Size | `30 × 30` px | State indicator diameter |
| Cursor Width | `2` px | Blinking cursor width |
| Cursor Height | `20` px | Blinking cursor height |

#### Init Wizard Window

| Property | Value | Description |
| :--- | :--- | :--- |
| Window Size | `540 × 540` px | Sufficient for manual install guide |
| Container Radius | `16` px | Card border radius |
| Container Padding | `24` px | Inner padding |

## 3. Core Screens

### 3.1 Main Capsule Window

This is the interface users see 99% of the time.

#### State A: Listening (Active)

- **Left**: Red solid circle (`#FF4757`, 30×30).
  - *Animation*: **Breathing** (Scale 1.0 ↔ 1.1, sine wave) + **Ripple expansion** (2 layers, Opacity 0.5 → 0, Scale 1.0 → 3.0).
- **Middle**: Real-time recognized text stream.
  - *Style*: White, single line, gradient text flow effect.
  - *Dynamic*: Latest text appears on the right with larger font (18px), older text fades left with smaller font (11px) and lower opacity (0.35).
  - *Visible Characters*: 25 characters max, left fade mask width 20px.
- **Right**: Blinking cursor (`#A4B0BE`, 2×20px).
  - *Animation*: 800ms period Fade In/Out with EaseInOut curve.

#### State B: Processing (Submitting)

- **Left**: Red dot changes to **rapid pulse** (Scale 1.0 → 1.2 → 1.0, 400ms cycle).
- **Middle**: Text color dims to `0.8` opacity, indicating submission in progress.
- **Right**: Cursor hidden.

#### State C: Error

- **Left**: Changes to **yellow** (`#FFA502`, warning) or **gray** (`#636E72`, no device).
- **Middle**: Shows error message (e.g., "Microphone unavailable").
- **Right**: No cursor.
- **Below Capsule**: Error action buttons (Refresh/Retry/Close).

Error types and their indicators:

| Error Type | Indicator Color | Example Message |
| :--- | :--- | :--- |
| Audio No Device | Gray `#636E72` | "No microphone detected" |
| Audio Device Busy | Yellow `#FFA502` | "Microphone is in use" |
| Audio Permission Denied | Yellow `#FFA502` | "Microphone permission denied" |
| Audio Device Lost | Yellow `#FFA502` | "Microphone disconnected" |
| Model Not Found | Yellow `#FFA502` | "Model not found" |
| Model Corrupted | Yellow `#FFA502` | "Model corrupted" |
| Socket Error | Yellow `#FFA502` | "Fcitx5 not connected" |

#### State D: Copied to Clipboard

- **Left**: Green circle with checkmark (`#2ECC71`).
- **Middle**: Recognized text.
- **Below Capsule**: Green-bordered hint box with message "已复制到剪贴板，请粘贴".

### 3.2 Init Wizard

Triggered when no ASR model detected locally on first run, or when switching to an engine without available model.

#### Phase 1: Mode Selection

- **Layout**: Centered card container.
- **Title**: "🎤 Nextalk 首次启动" (First Launch).
- **Description**: "需要下载语音识别模型" (Model download required).
- **Buttons**:
  - **Auto Download** (Primary, Red): "📥 自动下载 (推荐)".
  - **Manual Install** (Outlined): "📁 手动安装".

#### Phase 2: Download Progress

- **Title**: "⬇️ 正在下载模型..." (Downloading model...).
- **Progress**: Large percentage display (e.g., "45.2%").
- **Progress Bar**: Red linear indicator, 8px height, rounded corners.
- **Size Info**: "68MB / 150MB" format.
- **Buttons**:
  - **Switch to Manual**: Left-aligned text button.
  - **Cancel**: Right-aligned text button.

#### Phase 3: Extracting

- **Title**: "📦 解压模型..." (Extracting model...).
- **Progress**: Same as download phase.

#### Phase 4: Manual Install Guide

- **Title**: "📁 手动安装模型 (Engine Name)".
- **Steps**:
  1. Download model file (with copy link button).
  2. Extract and place to target path (with open directory button).
  3. Expected directory structure (code block display).
  - For SenseVoice: Additional steps 1b and 3b for VAD model.
- **Buttons**:
  - **Verify Model** (Primary): Check if model is correctly placed.
  - **Back to Auto Download**: Text button.

#### Phase 5: Completed

- **Icon**: Green checkmark (64px).
- **Title**: "🎉 初始化完成！".
- **Hint**: "按下 Right Alt 键开始语音输入".
- **Button**: "开始使用" (Start Using).

### 3.3 System Tray

- **Icon**: Minimalist microphone icon with three states:
  - Normal: Default icon.
  - Warning: Yellow-tinted icon (connection issues).
  - Error: Red-tinted icon (severe errors).
- **Menu Items**:
  - **Nextalk** (disabled, title only)
  - ---
  - **显示 / 隐藏** (Show / Hide)
  - **重新连接 Fcitx5** (Reconnect Fcitx5)
  - ---
  - **模型设置** (Model Settings) → Submenu:
    - **Zipformer** → Submenu:
      - ● int8 模型 (更快)
      - 标准模型 (更准)
    - **SenseVoice**
  - ---
  - **语言** (Language) → Submenu:
    - ● 简体中文
    - English
  - **设置** (Settings) - Opens config directory
  - ---
  - **退出** (Quit)

Note: Current selection indicated by "● " prefix (workaround for system_tray Linux checkbox bug).

### 3.4 Fatal Error Dialog

For unrecoverable application errors.

- **Size**: 400px width, auto height.
- **Background**: Dark (`#1A1A1A`).
- **Border Radius**: 16px.
- **Content**:
  - Header with error icon and "应用程序错误" title.
  - Error message in monospace font with dark background.
  - Expandable "详细信息" section for stack trace.
  - Action buttons: "复制诊断" (Copy Diagnostics), "退出" (Exit), "重启" (Restart, if available).

## 4. Interaction Flows

### 4.1 Wake & Speak

1. User presses configured hotkey (default: `Right Alt`).
2. Capsule window **instantly appears** (no fade, emphasizes speed) at last remembered position.
3. Left red light starts breathing, ripples start expanding.
4. User speaks → text stream appears in real-time with gradient flow effect.

### 4.2 Auto Commit (Fcitx5 Mode)

1. VAD detects silence (configurable threshold).
2. Red light stops breathing.
3. Text sent to Fcitx5 via Unix Domain Socket.
4. Window **instantly disappears**.

### 4.3 Auto Commit (Clipboard Mode)

When Fcitx5 is not available:

1. VAD detects silence.
2. Text copied to system clipboard.
3. State changes to **copiedToClipboard** (green checkmark + hint).
4. After 1.5 seconds, window **instantly disappears**.

### 4.4 Manual Commit

1. User presses hotkey again.
2. Immediately stops recording.
3. Force submit current text.
4. Window disappears.

### 4.5 Drag to Move

1. User holds any blank area of capsule window.
2. Window follows mouse movement (using `DragToMoveArea` widget).
3. On release, position saved to `SharedPreferences`, next wake appears at this position.

### 4.6 Engine Switch

1. User selects different engine from tray menu.
2. If model not available, Init Wizard shows with target engine.
3. After model ready, engine switches and tray menu updates.
4. System notification confirms switch success/failure.

## 5. Animation Specifications

For development accuracy, here are specific Flutter animation parameters:

### 5.1 Breathing Dot

| Property | Value |
| :--- | :--- |
| Formula | `1.0 + 0.1 × sin(t)` |
| Period | `2000ms` |
| Scale Range | `1.0` ↔ `1.1` |
| Glow Effect | Box shadow with radius `8 × scale`, opacity `0.6` |

Uses global `AnimationTickerService` for prewarming.

### 5.2 Ripple Effect

| Property | Value |
| :--- | :--- |
| Duration | `1500ms` |
| Curve | `Curves.easeOutQuad` (burst feel) |
| Scale | `1.0` → `3.0` |
| Opacity | `0.5` → `0.0` |
| Layer Count | `2` (staggered) |
| Repeat | Loop |

### 5.3 Cursor Blink

| Property | Value |
| :--- | :--- |
| Duration | `800ms` |
| Curve | `Curves.easeInOut` |
| Opacity | `1.0` ↔ `0.0` |
| Repeat | Reverse |

### 5.4 Pulse Indicator (Processing)

| Property | Value |
| :--- | :--- |
| Duration | `400ms` |
| Scale Sequence | `1.0` → `1.2` → `1.0` |
| Curve | `Curves.easeInOut` |
| Repeat | Loop |

### 5.5 Gradient Text Flow

| Property | Value |
| :--- | :--- |
| Max Font Size | `18px` (newest text) |
| Min Font Size | `11px` (oldest text) |
| Max Opacity | `1.0` |
| Min Opacity | `0.35` |
| Visible Char Count | `25` |
| Fade Mask Width | `20px` |
| Text Alignment | Right (newest text anchored right) |

## 6. State Machine

### 6.1 Capsule States

```
┌─────────────────────────────────────────────────────────────┐
│                       CapsuleState                          │
├─────────────────────────────────────────────────────────────┤
│  idle          │ Window hidden, no activity                 │
│  listening     │ Recording active, breathing dot + ripples  │
│  processing    │ VAD triggered, submitting text             │
│  error         │ Error occurred, shows error indicator      │
│  initializing  │ First run model check                      │
│  downloading   │ Model download in progress                 │
│  extracting    │ Model extraction in progress               │
│  copiedToClipboard │ Text copied, green checkmark shown     │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Init Phases

```
┌─────────────────────────────────────────────────────────────┐
│                        InitPhase                            │
├─────────────────────────────────────────────────────────────┤
│  checkingModel  │ Detecting model status                    │
│  selectingMode  │ User chooses auto/manual install          │
│  downloading    │ Auto download in progress                 │
│  extracting     │ Extracting downloaded archive             │
│  verifying      │ Verifying model integrity                 │
│  manualGuide    │ Showing manual install instructions       │
│  completed      │ Model ready, initialization done          │
│  error          │ Download/extraction failed                │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Tray Status

```
┌─────────────────────────────────────────────────────────────┐
│                       TrayStatus                            │
├─────────────────────────────────────────────────────────────┤
│  normal   │ Default icon, everything working               │
│  warning  │ Yellow icon, connection issues                 │
│  error    │ Red icon, severe errors                        │
└─────────────────────────────────────────────────────────────┘
```

## 7. Error Handling UX

### 7.1 Error Categories

| Category | Error Types | Indicator | Actions |
| :--- | :--- | :--- | :--- |
| **Audio** | NoDevice, DeviceBusy, PermissionDenied, DeviceLost, InitFailed | Gray/Yellow dot | Refresh/Retry |
| **Model** | NotFound, Incomplete, Corrupted, LoadFailed | Yellow dot | Redownload/Delete+Redownload |
| **Socket** | ConnectionFailed, Timeout, SendFailed, PermissionInsecure | Yellow dot | Retry Submit/Copy Text |

### 7.2 Error Action Buttons

- **Primary Button**: Red background (`#FF4757`), white text.
- **Secondary Button**: Text only, hint color (`#A4B0BE`).
- **Max Buttons**: 3 per error state.
- **Layout**: Horizontal row, centered.

### 7.3 Preserved Text Protection

When submission fails (socket error, device lost during recording):

- Original text is preserved in `preservedText` field.
- User can: Copy Text / Retry Submit / Discard.
- Displayed in italic style with quotes.

## 8. Internationalization

### 8.1 Supported Languages

- **Chinese (Simplified)**: `zh` (default based on system locale)
- **English**: `en`

### 8.2 Language Switch

- Via tray menu: 语言 (Language) → 简体中文 / English
- Immediate effect, no restart required.
- Persisted to settings file.

### 8.3 Localized Elements

- All tray menu items
- Init wizard text and buttons
- Error messages
- Hint text ("正在聆听..." / "Listening...")
- Action button labels
- Notification messages

## 9. Hotkey Configuration

### 9.1 Default Hotkey

- **Key**: `Right Alt` (single key, no modifiers)
- **Behavior**: Toggle recording on/off

### 9.2 Configuration File

Location: `~/.config/nextalk/settings.yaml`

```yaml
hotkey:
  key: altRight
  modifiers: []  # or: [ctrl, shift]
```

### 9.3 Supported Keys

- **Modifier Keys** (as main key): `altRight`, `altLeft`
- **Function Keys**: `f1`-`f12`
- **Special Keys**: `space`, `escape`, `tab`, `enter`, `backspace`, `capsLock`
- **Arrow Keys**: `up`, `down`, `left`, `right`
- **Edit Keys**: `insert`, `delete`, `home`, `end`, `pageUp`, `pageDown`
- **Letter Keys**: `a`-`z`
- **Number Keys**: `0`-`9`, `numpad0`-`numpad9`

### 9.4 Supported Modifiers

- `ctrl`, `shift`, `alt`, `meta`

## 10. Window Position Memory

### 10.1 Storage

- **Keys**: `nextalk_window_x`, `nextalk_window_y`
- **Storage**: `SharedPreferences`

### 10.2 Validation Bounds

| Property | Value | Purpose |
| :--- | :--- | :--- |
| Min X | `-200` | Allow partial off-screen left |
| Max X | `4000` | Support multi-monitor setups |
| Min Y | `-50` | Allow partial off-screen top |
| Max Y | `2500` | Support multi-monitor setups |

### 10.3 Save Triggers

- Window moved (drag released)
- Window closed
