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
