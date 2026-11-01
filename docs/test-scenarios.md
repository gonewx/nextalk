# Exception Scenario Testing Guide

[简体中文](test-scenarios_zh.md) | English

This document records Nextalk application's exception scenarios and simulation methods for testing tray icon status and error handling.

## Tray Status Description

| Status | Icon File | Meaning |
|--------|-----------|---------|
| `TrayStatus.normal` | `tray_icon.png` | Normal operation |
| `TrayStatus.warning` | `tray_icon_warning.png` | Recoverable issue |
| `TrayStatus.error` | `tray_icon_error.png` | Serious error |

---

## 🟡 Warning Scenarios (Recoverable)

### 1. Fcitx5 Connection Lost

**Error Type**: `CapsuleErrorType.socketError` + `FcitxError.connectionFailed`

**Simulation Method**:
```bash
# Stop fcitx5
killall fcitx5

# Launch app, then try voice input
# Or via tray menu -> "Reconnect Fcitx5"
```

**Recovery Method**:
```bash
fcitx5 &
# Then tray menu -> "Reconnect Fcitx5"
```

---

### 2. Fcitx5 Not Running (Socket Doesn't Exist)

**Error Type**: `CapsuleErrorType.socketError` + `FcitxError.socketNotFound`

**Simulation Method**:
```bash
# Ensure fcitx5 is not running
killall fcitx5

# Delete socket file (if exists)
rm -f $XDG_RUNTIME_DIR/nextalk-fcitx5.sock

# Launch app
```

---

### 3. Audio Device Busy

**Error Type**: `CapsuleErrorType.audioDeviceBusy`

**Simulation Method**:
```bash
# Terminal 1: Exclusively occupy microphone
arecord -f cd -D plughw:0,0 /dev/null

# Terminal 2: Launch app and try recording
```

**Recovery Method**: Close application occupying microphone

---

### 4. Audio Device Disconnected

**Error Type**: `CapsuleErrorType.audioDeviceLost`

**Simulation Method**:
- USB microphone: Unplug while app is running
- Bluetooth microphone: Disconnect Bluetooth connection

---

## 🔴 Error Scenarios (Serious/Unrecoverable)

### 1. Model Not Found

**Error Type**: `CapsuleErrorType.modelNotFound`

**Simulation Method**:
```bash
# Backup model directory
mv ~/.local/share/nextalk/models ~/.local/share/nextalk/models.bak

# Launch app
```

**Recovery Method**:
```bash
mv ~/.local/share/nextalk/models.bak ~/.local/share/nextalk/models
```

---

### 2. Model Files Incomplete

**Error Type**: `CapsuleErrorType.modelIncomplete`

**Simulation Method**:
```bash
# Delete some model files
rm ~/.local/share/nextalk/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en/tokens.txt
```

---

### 3. Model Corrupted

**Error Type**: `CapsuleErrorType.modelCorrupted`

**Simulation Method**:
```bash
# Truncate onnx file to corrupt it
MODEL_DIR=~/.local/share/nextalk/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en

# Backup first
cp $MODEL_DIR/encoder-epoch-99-avg-1.onnx $MODEL_DIR/encoder-epoch-99-avg-1.onnx.bak

# Truncate file
truncate -s 1000 $MODEL_DIR/encoder-epoch-99-avg-1.onnx
```

**Recovery Method**:
```bash
mv $MODEL_DIR/encoder-epoch-99-avg-1.onnx.bak $MODEL_DIR/encoder-epoch-99-avg-1.onnx
```

---

### 4. Model Load Failed

**Error Type**: `CapsuleErrorType.modelLoadFailed`

**Simulation Method**:
```bash
# Replace model file with invalid content
MODEL_DIR=~/.local/share/nextalk/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en

cp $MODEL_DIR/encoder-epoch-99-avg-1.onnx $MODEL_DIR/encoder-epoch-99-avg-1.onnx.bak
echo "invalid onnx content" > $MODEL_DIR/encoder-epoch-99-avg-1.onnx
```

---

### 5. No Microphone Device

**Error Type**: `CapsuleErrorType.audioNoDevice`

**Simulation Method**:
```bash
# Method 1: Disable PulseAudio source
pactl list sources short
pactl suspend-source <source_name> 1

# Method 2: Run in VM/container without audio device

# Method 3: Temporarily unload audio driver (requires root, use caution)
sudo modprobe -r snd_hda_intel
```

---

### 6. Microphone Permission Denied

**Error Type**: `CapsuleErrorType.audioPermissionDenied`

**Simulation Method**:
```bash
# Method 1: Run in Flatpak sandbox (without audio permission)

# Method 2: Modify audio device permissions
sudo chmod 000 /dev/snd/*
# Recovery: sudo chmod 660 /dev/snd/*

# Method 3: Remove user from audio group (requires re-login)
sudo gpasswd -d $USER audio
```

---

## GNOME + IBus Text Injection

**Prerequisites**: GNOME Wayland session with IBus and no running Fcitx5; install v0.3.3 or later, enable `nextalk@gonewx.com`, then log out and back in. Launch test windows inside the graphical session, not over SSH, and explicitly focus the target. Remove any user-local extension copy that overrides the packaged version before testing it.

**Simulation Method**:

1. Open a Wayland-native ptyxis terminal. For XWayland, launch `GDK_BACKEND=x11 ptyxis -s` from a session terminal to avoid reusing the Wayland instance.
2. In the target terminal, run `stty -icanon; cat > /tmp/nextalk-inject.txt`. Keep `cat` running while committing text.
3. From another session terminal, run the commands below from the repository root, then focus the target within 5 seconds. Read `/tmp/nextalk-inject.txt` from another terminal and compare the exact payload; use a fresh file for each run. Finish with Ctrl+C and `stty sane` in the target.

```bash
scripts/poc/ibus-panel-commit.sh 5 '你好世界，Nextalk Panel 注入测试 OK'
scripts/poc/ibus-panel-commit.sh --legacy 5 '你好世界，Nextalk Panel 注入测试 OK'
```

The default calls diagnostic `CommitTextViaPanel`; `--legacy` calls production `CommitText`, which now also tries Panel first. The flag no longer isolates the old inputMethod-only implementation. These D-Bus probes do not copy to clipboard themselves: repeat each scenario through Nextalk voice input to verify the full chain and clipboard UI.

| Scenario | Expected result |
|----------|-----------------|
| Wayland-native terminal with live `cat` | Both methods return OK; exact file readback; Nextalk commits directly without clipboard prompt |
| XWayland terminal (`GDK_BACKEND=x11 ptyxis -s`) with live `cat` | Both methods return OK through Panel; exact file readback; no clipboard prompt |
| Nautilus focused, no editable control active | Panel returns ERR for no real input context; production CommitText returns ERR after inputMethod also fails; Nextalk copies text and shows the clipboard prompt |
| libpinyin Chinese mode, `ni hao` preedit visible | Commit appears before the preedit; preedit, candidate list and libpinyin engine remain intact; confirm visually, then finish composition before file comparison |
| Extension disabled, session re-entered | D-Bus endpoint unavailable; Nextalk falls back to clipboard; manually paste and compare the text |

**Recovery Method**: Re-enable the extension with `gnome-extensions enable nextalk@gonewx.com`, log out and back in, and repeat the terminal checks. Close only test windows; avoid `pkill -f` against the shared ptyxis process.

**Evidence and gaps**: [Fedora 43 VM POC and production regression](research/ibus-support-2026.md#81-poc-实测结果2026-11-01) verified Wayland/XWayland terminal readback and Nautilus rejection; preedit preservation was verified in the Panel POC. Extension-disabled clipboard behavior is a regression scenario to verify, not a newly recorded VM result. Pure XIM (daemon lacks `--xim`), Qt-X11 and Electron remain unverified; non-GNOME IBus desktops still use clipboard without Fcitx5.

---

## Tray Status Mapping Suggestion

When detecting errors, update tray status based on error type:

```dart
void updateTrayForError(CapsuleErrorType? type) {
  if (type == null) {
    TrayService.instance.updateStatus(TrayStatus.normal);
    return;
  }

  switch (type) {
    // Warning: Recoverable issues
    case CapsuleErrorType.socketError:
    case CapsuleErrorType.audioDeviceBusy:
    case CapsuleErrorType.audioDeviceLost:
      TrayService.instance.updateStatus(TrayStatus.warning);
      break;

    // Error: Serious issues
    case CapsuleErrorType.modelNotFound:
    case CapsuleErrorType.modelIncomplete:
    case CapsuleErrorType.modelCorrupted:
    case CapsuleErrorType.modelLoadFailed:
    case CapsuleErrorType.audioNoDevice:
    case CapsuleErrorType.audioPermissionDenied:
    case CapsuleErrorType.audioInitFailed:
      TrayService.instance.updateStatus(TrayStatus.error);
      break;

    case CapsuleErrorType.unknown:
      TrayService.instance.updateStatus(TrayStatus.warning);
      break;
  }
}
```

---

## Testing Checklist

- [ ] Warning icon shows when Fcitx5 disconnected
- [ ] Warning icon shows when audio device busy
- [ ] Error icon shows when model missing
- [ ] Error icon shows when model corrupted
- [ ] Error icon shows when no microphone
- [ ] Icon reverts to Normal after issue resolved
- [ ] Tray menu "Reconnect Fcitx5" function works
