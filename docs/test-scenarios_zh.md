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

## GNOME + IBus 文本注入

**前置条件**：GNOME Wayland 会话使用 IBus，未运行 Fcitx5；安装 v0.3.3 或更新版本，启用 `nextalk@gonewx.com` 后注销重新登录。测试窗口从图形会话内启动，不通过 SSH 启动，并明确聚焦目标。测试安装包前删除覆盖系统版本的用户级扩展副本。

**模拟方法**：

1. 打开 Wayland 原生 ptyxis 终端。测试 XWayland 时，从会话终端运行 `GDK_BACKEND=x11 ptyxis -s`，避免复用 Wayland 实例。
2. 在目标终端运行 `stty -icanon; cat > /tmp/nextalk-inject.txt`，提交期间保持 `cat` 运行。
3. 在另一会话终端从仓库根目录运行下列命令，并在 5 秒内聚焦目标。从另一终端读取 `/tmp/nextalk-inject.txt`，逐字比对载荷；每次测试使用新文件。结束后在目标终端按 Ctrl+C 并运行 `stty sane`。

```bash
scripts/poc/ibus-panel-commit.sh 5 '你好世界，Nextalk Panel 注入测试 OK'
scripts/poc/ibus-panel-commit.sh --legacy 5 '你好世界，Nextalk Panel 注入测试 OK'
```

默认调用诊断方法 `CommitTextViaPanel`；`--legacy` 调用正式 `CommitText`，现在也优先走 Panel。该参数已不能隔离旧的仅 inputMethod 实现。这些 D-Bus 探针不会自行复制剪贴板：每种场景还需通过 Nextalk 语音输入复测，以验证完整注入链和剪贴板 UI。

| 场景 | 预期结果 |
|------|----------|
| Wayland 原生终端，`cat` 正在运行 | 两种方法均返回 OK，文件读回逐字一致；Nextalk 直接上屏，无剪贴板提示 |
| XWayland 终端（`GDK_BACKEND=x11 ptyxis -s`），`cat` 正在运行 | 两种方法均经 Panel 返回 OK，文件读回逐字一致，无剪贴板提示 |
| Nautilus 获得焦点，但无活动可编辑控件 | Panel 因无真实输入上下文返回 ERR；正式 CommitText 在 inputMethod 也失败后返回 ERR；Nextalk 复制文本并显示剪贴板提示 |
| libpinyin 中文模式，显示 `ni hao` 预编辑 | 文本插在预编辑之前；预编辑、候选框及 libpinyin 引擎保持不变；先目视确认，再完成组词后比对文件 |
| 禁用扩展后重新登录会话 | D-Bus 接口不可用；Nextalk 回退剪贴板，手动粘贴并比对文本 |

**恢复方法**：运行 `gnome-extensions enable nextalk@gonewx.com` 重新启用扩展，注销重新登录，再次验证终端场景。只关闭测试窗口，避免对共享 ptyxis 进程执行 `pkill -f`。

**证据与缺口**：[Fedora 43 VM POC 与正式版回归](research/ibus-support-2026.md#81-poc-实测结果2026-11-01) 已验证 Wayland/XWayland 终端读回及 Nautilus 拒绝提交；预编辑保留已在 Panel POC 中验证。禁用扩展后的剪贴板行为是待执行回归场景，并非本次新增的 VM 实测结果。纯 XIM（daemon 无 `--xim`）、Qt-X11 和 Electron 尚未验证；非 GNOME 的 IBus 桌面在无 Fcitx5 时仍使用剪贴板。

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
