# 异常场景测试指南

简体中文 | [English](test-scenarios.md)

本文档记录 Nextalk 应用的异常场景及其模拟方法，用于测试托盘图标状态和错误处理。

## 托盘状态说明

| 状态 | 图标文件 | 含义 |
|------|----------|------|
| `TrayStatus.normal` | `tray_icon.png` | 正常运行 |
| `TrayStatus.warning` | `tray_icon_warning.png` | 可恢复问题 |
| `TrayStatus.error` | `tray_icon_error.png` | 严重错误 |

---

## 🟡 Warning 场景（可恢复）

### 1. Fcitx5 连接断开

**错误类型**: `CapsuleErrorType.socketError` + `FcitxError.connectionFailed`

**模拟方法**:
```bash
# 停止 fcitx5
killall fcitx5

# 启动应用后，尝试语音输入
# 或通过托盘菜单 -> "重新连接 Fcitx5"
```

**恢复方法**:
```bash
fcitx5 &
# 然后托盘菜单 -> "重新连接 Fcitx5"
```

---

### 2. Fcitx5 未运行（Socket 不存在）

**错误类型**: `CapsuleErrorType.socketError` + `FcitxError.socketNotFound`

**模拟方法**:
```bash
# 确保 fcitx5 未运行
killall fcitx5

# 删除 socket 文件（如果存在）
rm -f $XDG_RUNTIME_DIR/nextalk-fcitx5.sock

# 启动应用
```

---

### 3. 音频设备被占用

**错误类型**: `CapsuleErrorType.audioDeviceBusy`

**模拟方法**:
```bash
# 终端 1: 独占麦克风
arecord -f cd -D plughw:0,0 /dev/null

# 终端 2: 启动应用并尝试录音
```

**恢复方法**: 关闭占用麦克风的应用

---

### 4. 音频设备断开

**错误类型**: `CapsuleErrorType.audioDeviceLost`

**模拟方法**:
- USB 麦克风: 在应用运行时拔掉
- 蓝牙麦克风: 断开蓝牙连接

---

## 🔴 Error 场景（严重/不可恢复）

### 1. 模型不存在

**错误类型**: `CapsuleErrorType.modelNotFound`

**模拟方法**:
```bash
# 备份模型目录
mv ~/.local/share/nextalk/models ~/.local/share/nextalk/models.bak

# 启动应用
```

**恢复方法**:
```bash
mv ~/.local/share/nextalk/models.bak ~/.local/share/nextalk/models
```

---

### 2. 模型文件不完整

**错误类型**: `CapsuleErrorType.modelIncomplete`

**模拟方法**:
```bash
# 删除部分模型文件
rm ~/.local/share/nextalk/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en/tokens.txt
```

---

### 3. 模型损坏

**错误类型**: `CapsuleErrorType.modelCorrupted`

**模拟方法**:
```bash
# 截断 onnx 文件使其损坏
MODEL_DIR=~/.local/share/nextalk/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en

# 先备份
cp $MODEL_DIR/encoder-epoch-99-avg-1.onnx $MODEL_DIR/encoder-epoch-99-avg-1.onnx.bak

# 截断文件
truncate -s 1000 $MODEL_DIR/encoder-epoch-99-avg-1.onnx
```

**恢复方法**:
```bash
mv $MODEL_DIR/encoder-epoch-99-avg-1.onnx.bak $MODEL_DIR/encoder-epoch-99-avg-1.onnx
```

---

### 4. 模型加载失败

**错误类型**: `CapsuleErrorType.modelLoadFailed`

**模拟方法**:
```bash
# 用无效内容替换模型文件
MODEL_DIR=~/.local/share/nextalk/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en

cp $MODEL_DIR/encoder-epoch-99-avg-1.onnx $MODEL_DIR/encoder-epoch-99-avg-1.onnx.bak
echo "invalid onnx content" > $MODEL_DIR/encoder-epoch-99-avg-1.onnx
```

---

### 5. 无麦克风设备

**错误类型**: `CapsuleErrorType.audioNoDevice`

**模拟方法**:
```bash
# 方法 1: 禁用 PulseAudio 源
pactl list sources short
pactl suspend-source <source_name> 1

# 方法 2: 在无音频设备的虚拟机/容器中运行

# 方法 3: 临时卸载音频驱动（需要 root，谨慎操作）
sudo modprobe -r snd_hda_intel
```

---

### 6. 麦克风权限拒绝

**错误类型**: `CapsuleErrorType.audioPermissionDenied`

**模拟方法**:
```bash
# 方法 1: 在 Flatpak 沙箱中运行（不授予音频权限）

# 方法 2: 修改音频设备权限
sudo chmod 000 /dev/snd/*
# 恢复: sudo chmod 660 /dev/snd/*

# 方法 3: 将用户从 audio 组移除（需要重新登录）
sudo gpasswd -d $USER audio
```

---

## 托盘状态映射建议

在检测到错误时，根据错误类型更新托盘状态：

```dart
void updateTrayForError(CapsuleErrorType? type) {
  if (type == null) {
    TrayService.instance.updateStatus(TrayStatus.normal);
    return;
  }

  switch (type) {
    // Warning: 可恢复问题
    case CapsuleErrorType.socketError:
    case CapsuleErrorType.audioDeviceBusy:
    case CapsuleErrorType.audioDeviceLost:
      TrayService.instance.updateStatus(TrayStatus.warning);
      break;

    // Error: 严重问题
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

## 测试检查清单

- [ ] Warning 图标在 Fcitx5 断开时显示
- [ ] Warning 图标在音频设备被占用时显示
- [ ] Error 图标在模型缺失时显示
- [ ] Error 图标在模型损坏时显示
- [ ] Error 图标在无麦克风时显示
- [ ] 问题恢复后图标恢复 Normal 状态
- [ ] 托盘菜单"重新连接 Fcitx5"功能正常
