# Story 3.7: 初始化向导与错误处理系统 (Init Wizard & Error Handling)

Status: done

## Prerequisites

> **前置条件**: Epic 1, Epic 2, Story 3-1 ~ 3-6 必须全部完成
> - ✅ Epic 1: IPC 桥梁 - FcitxClient 已实现
> - ✅ Epic 2: 语音识别引擎 - Pipeline + ModelManager 已实现
> - ✅ Story 3-6: 完整业务流串联 - 核心流程已实现
> - ⚠️ 本 Story 补充完善的异常处理机制和初次运行引导流程

## Story

As a **用户**,
I want **在各种异常情况下获得清晰的提示和恢复指引**,
So that **即使遇到问题也能自助解决，获得流畅的使用体验**。

## Acceptance Criteria

### 初次运行引导 (Init Wizard)

| AC | 描述 | 验证方法 |
|----|------|----------|
| AC1 | 首次运行检测到模型缺失时显示初始化向导 | 删除模型目录后启动应用 |
| AC2 | 初始化向导提供"自动下载"和"手动安装"两种选项 | 观察 UI |
| AC3 | 自动下载时显示进度百分比和已下载大小 | 执行下载并观察 |
| AC4 | 下载失败时显示具体错误并提供重试/切换手动选项 | 断网后测试 |
| AC5 | 手动安装引导显示下载链接和目标路径 | 选择手动安装 |
| AC6 | 手动安装提供"复制链接"和"打开目录"按钮 | 点击按钮测试 |
| AC7 | 手动安装后可检测模型是否正确放置 | 放置模型后点击检测 |

### 模型错误处理

| AC | 描述 | 验证方法 |
|----|------|----------|
| AC8 | 模型不完整时显示"模型文件不完整"并提供重新下载选项 | 删除部分模型文件测试 |
| AC9 | 模型加载失败时显示具体原因（如内存不足） | 模拟加载失败 |
| AC10 | 错误状态下提供可操作的恢复按钮 | 触发错误后观察 UI |

### 音频错误处理

| AC | 描述 | 验证方法 |
|----|------|----------|
| AC11 | 无麦克风设备时显示"未检测到麦克风"并提供刷新检测 | 拔掉麦克风测试 |
| AC12 | 设备被占用时显示"麦克风被其他应用占用" | 用其他应用占用后测试 |
| AC13 | 运行时设备断开时保存已识别文本并显示警告 | 录音中拔掉麦克风 |

### Socket/Fcitx5 错误处理

| AC | 描述 | 验证方法 |
|----|------|----------|
| AC14 | Fcitx5 未运行时显示"Fcitx5 未运行，请先启动输入法" | 停止 Fcitx5 后测试 |
| AC15 | 提交失败时保护用户文本，提供"复制文本"按钮 | 断开连接后测试提交 |
| AC16 | 托盘菜单提供"重新连接 Fcitx5"选项 | 查看托盘菜单 |

### 运行时异常处理

| AC | 描述 | 验证方法 |
|----|------|----------|
| AC17 | 全局错误边界捕获未处理异常 | 模拟异常 |
| AC18 | 致命错误时显示错误对话框而非崩溃 | 触发致命错误 |
| AC19 | 托盘图标显示连接状态角标 | 观察不同状态下的图标 |

## 技术规格

### 状态扩展 [Source: 变更提案 #1-5]

**CapsuleState 扩展:**
```dart
enum CapsuleState {
  idle,
  listening,
  processing,
  error,
  // 新增
  initializing,    // 初始化中 (首次运行)
  downloading,     // 模型下载中
  extracting,      // 模型解压中
}
```

**CapsuleErrorType 细化:**
```dart
enum CapsuleErrorType {
  // 音频相关 (细化)
  audioNoDevice,          // 未检测到麦克风
  audioDeviceBusy,        // 设备被占用
  audioPermissionDenied,  // 权限不足
  audioDeviceLost,        // 运行时设备丢失
  audioInitFailed,        // 初始化失败 (通用)

  // 模型相关 (细化)
  modelNotFound,          // 模型未找到
  modelIncomplete,        // 模型不完整
  modelCorrupted,         // 模型损坏
  modelLoadFailed,        // 加载失败

  // 连接相关 (统一类型，细化消息由 FcitxError 决定)
  socketError,            // Socket/Fcitx5 错误 (使用 fcitxError 字段细化)

  // 其他
  unknown,
}
```

**⚠️ 重要: Socket 错误使用现有 FcitxError**

`FcitxClient` 已定义 `FcitxError` 枚举，避免重复定义：
```dart
// 已存在于 lib/services/fcitx_client.dart
enum FcitxError {
  socketNotFound,     // Socket 文件不存在
  connectionFailed,   // 连接失败
  sendFailed,         // 发送失败
  reconnectFailed,    // 重连失败
}
```

`CapsuleStateData` 扩展以携带 `FcitxError`：
```dart
class CapsuleStateData {
  // ... 现有字段
  final FcitxError? fcitxError;  // 新增: Socket 错误细化

  String get displayMessage {
    if (state != CapsuleState.error) return recognizedText;
    if (errorType == CapsuleErrorType.socketError && fcitxError != null) {
      return switch (fcitxError!) {
        FcitxError.socketNotFound => 'Fcitx5 未运行，请先启动输入法',
        FcitxError.connectionFailed => 'Fcitx5 连接失败',
        FcitxError.sendFailed => '文本发送失败',
        FcitxError.reconnectFailed => 'Fcitx5 重连失败，请检查服务状态',
      };
    }
    return errorMessage ?? _defaultErrorMessage;
  }
}
```

### 目标文件结构

```text
voice_capsule/
├── lib/
│   ├── main.dart                          # 🔄 修改 (全局错误边界)
│   ├── app/
│   │   └── nextalk_app.dart               # 🔄 修改 (状态路由)
│   ├── state/
│   │   ├── capsule_state.dart             # 🔄 修改 (扩展枚举)
│   │   └── init_state.dart                # 🆕 新增 (初始化状态管理)
│   ├── services/
│   │   ├── model_manager.dart             # 🔄 修改 (新增工具方法)
│   │   ├── audio_capture.dart             # 🔄 修改 (设备检测)
│   │   ├── audio_inference_pipeline.dart  # 🔄 修改 (运行时异常)
│   │   ├── hotkey_controller.dart         # 🔄 修改 (文本保护)
│   │   └── tray_service.dart              # 🔄 修改 (状态角标+重连)
│   ├── ui/
│   │   ├── init_wizard/                   # 🆕 新增目录
│   │   │   ├── init_mode_selector.dart    # 选择安装方式
│   │   │   ├── download_progress.dart     # 下载进度
│   │   │   └── manual_install_guide.dart  # 手动安装引导
│   │   ├── error_action_widget.dart       # 🆕 新增 (带操作按钮的错误UI)
│   │   └── fatal_error_dialog.dart        # 🆕 新增 (致命错误对话框)
│   └── utils/
│       ├── clipboard_helper.dart          # 🆕 新增 (剪贴板工具)
│       └── diagnostic_logger.dart         # 🆕 新增 (诊断日志)
└── test/
    ├── state/
    │   └── init_state_test.dart           # 🆕 新增
    ├── ui/
    │   ├── init_wizard_test.dart          # 🆕 新增
    │   └── error_action_widget_test.dart  # 🆕 新增
    └── integration/
        └── error_handling_test.dart       # 🆕 新增
```

### 初始化向导 UI 设计 [Source: docs/front-end-spec.md#3.2]

**阶段 1: 选择安装方式**
```
┌─────────────────────────────────────────────────────┐
│  🎤 Nextalk 首次启动                                │
│                                                     │
│  需要下载语音识别模型 (~150MB)                       │
│                                                     │
│  ┌─────────────────┐   ┌─────────────────┐         │
│  │  📥 自动下载     │   │  📁 手动安装     │         │
│  │  (推荐)         │   │                 │         │
│  └─────────────────┘   └─────────────────┘         │
└─────────────────────────────────────────────────────┘
```

**阶段 2A: 自动下载进度**
```
┌─────────────────────────────────────────────────────┐
│  正在下载模型... 45%                                 │
│  ████████████░░░░░░░░░░░░░░  68MB / 150MB           │
│                                                     │
│  [切换手动安装]                      [取消]          │
└─────────────────────────────────────────────────────┘
```

**阶段 2B: 手动安装引导**
```
┌─────────────────────────────────────────────────────┐
│  📁 手动安装模型                                     │
│                                                     │
│  1. 下载模型文件:                                    │
│     [复制链接] github.com/k2-fsa/sherpa-onnx/...    │
│                                                     │
│  2. 解压并放置到:                                    │
│     [打开目录] ~/.local/share/nextalk/models/       │
│                                                     │
│  3. 目录结构应为:                                    │
│     models/sherpa-onnx-streaming-zipformer.../      │
│       ├── encoder-*.onnx                            │
│       ├── decoder-*.onnx                            │
│       ├── joiner-*.onnx                             │
│       └── tokens.txt                                │
│                                                     │
│  [检测模型]              [返回自动下载]              │
└─────────────────────────────────────────────────────┘
```

### 错误操作 UI 设计 [Source: docs/front-end-spec.md#6]

**带操作按钮的错误显示:**
```
┌─────────────────────────────────────────────────────┐
│  ○  未检测到麦克风                                   │
│  (灰色)                                             │
│     请连接麦克风设备后重试                            │
│                                                     │
│  [刷新检测]                           [查看帮助]     │
└─────────────────────────────────────────────────────┘
```

**文本保护错误显示:**
```
┌─────────────────────────────────────────────────────┐
│  ⚠️  Fcitx5 未连接                                   │
│                                                     │
│  "您刚才说的内容已保存"                              │
│                                                     │
│  [复制文本]    [重试提交]    [放弃]                  │
└─────────────────────────────────────────────────────┘
```

## Tasks / Subtasks

> **执行顺序**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7

### Task 1: 扩展状态枚举和数据模型 (AC: #8-10)

- [x] 1.1 修改 `lib/state/capsule_state.dart`:
  - 扩展 `CapsuleState` 添加 `initializing`, `downloading`, `extracting`
  - 扩展 `CapsuleErrorType` 细化音频、模型、Socket 错误类型
  - 添加 `fcitxError` 字段用于 Socket 错误细化
  - 更新 `displayMessage` getter 返回细化消息
- [x] 1.2 创建 `lib/state/init_state.dart`:

**完整代码规格:**
```dart
// lib/state/init_state.dart

import '../services/model_manager.dart';

/// 初始化阶段枚举
enum InitPhase {
  checkingModel,    // 检测模型状态
  selectingMode,    // 选择安装方式
  downloading,      // 自动下载中
  extracting,       // 解压中
  manualGuide,      // 手动安装引导
  verifying,        // 验证模型
  completed,        // 初始化完成
  error,            // 初始化失败
}

/// 初始化状态数据
class InitStateData {
  const InitStateData({
    required this.phase,
    this.progress = 0.0,
    this.statusMessage = '',
    this.downloadedBytes = 0,
    this.totalBytes = 0,
    this.errorMessage,
    this.modelError,
    this.canRetry = false,
  });

  final InitPhase phase;
  final double progress;          // 0.0 - 1.0
  final String statusMessage;
  final int downloadedBytes;      // 已下载字节数
  final int totalBytes;           // 总字节数
  final String? errorMessage;
  final ModelError? modelError;   // 来自 ModelManager
  final bool canRetry;

  // 工厂构造函数
  factory InitStateData.checking() => const InitStateData(
    phase: InitPhase.checkingModel,
    statusMessage: '检测模型状态...',
  );

  factory InitStateData.selectMode() => const InitStateData(
    phase: InitPhase.selectingMode,
  );

  factory InitStateData.downloading({
    required double progress,
    required int downloaded,
    required int total,
  }) => InitStateData(
    phase: InitPhase.downloading,
    progress: progress,
    downloadedBytes: downloaded,
    totalBytes: total,
    statusMessage: '下载中: ${(progress * 100).toStringAsFixed(1)}%',
  );

  factory InitStateData.extracting(double progress) => InitStateData(
    phase: InitPhase.extracting,
    progress: progress,
    statusMessage: '解压中: ${(progress * 100).toStringAsFixed(1)}%',
  );

  factory InitStateData.manualGuide() => const InitStateData(
    phase: InitPhase.manualGuide,
  );

  factory InitStateData.verifying() => const InitStateData(
    phase: InitPhase.verifying,
    statusMessage: '验证模型...',
  );

  factory InitStateData.completed() => const InitStateData(
    phase: InitPhase.completed,
    progress: 1.0,
    statusMessage: '初始化完成',
  );

  factory InitStateData.error(ModelError error, {String? message}) => InitStateData(
    phase: InitPhase.error,
    modelError: error,
    errorMessage: message ?? _defaultErrorMessage(error),
    canRetry: error != ModelError.permissionDenied,
  );

  static String _defaultErrorMessage(ModelError error) => switch (error) {
    ModelError.networkError => '网络错误，请检查网络连接',
    ModelError.diskSpaceError => '磁盘空间不足',
    ModelError.checksumMismatch => '文件校验失败，请重新下载',
    ModelError.extractionFailed => '解压失败',
    ModelError.permissionDenied => '权限不足',
    ModelError.downloadCancelled => '下载已取消',
    ModelError.none => '',
  };

  /// 格式化下载大小 (如 "68MB / 150MB")
  String get formattedSize {
    if (totalBytes == 0) return '';
    final downloaded = (downloadedBytes / 1024 / 1024).toStringAsFixed(0);
    final total = (totalBytes / 1024 / 1024).toStringAsFixed(0);
    return '${downloaded}MB / ${total}MB';
  }
}
```

### Task 2: 实现初始化向导 UI 组件 (AC: #1-7)

- [x] 2.1 创建 `lib/ui/init_wizard/` 目录
- [x] 2.2 创建 `init_mode_selector.dart`:
  - 双按钮布局 (自动下载/手动安装)
  - 符合胶囊 UI 风格 (深色背景、圆角)
- [x] 2.3 创建 `download_progress.dart`:
  - 进度条 + 百分比 + 已下载大小
  - 切换手动安装 + 取消按钮
  - 错误状态显示和重试
- [x] 2.4 创建 `manual_install_guide.dart`:
  - 步骤说明 (下载链接/目标路径/目录结构)
  - 复制链接 + 打开目录按钮
  - 检测模型 + 返回自动下载按钮

### Task 3: 实现错误操作 UI 组件 (AC: #10-16)

- [x] 3.1 创建 `lib/ui/error_action_widget.dart`:

**完整组件规格:**
```dart
// lib/ui/error_action_widget.dart

import 'package:flutter/material.dart';
import '../state/capsule_state.dart';

/// 错误操作按钮定义
class ErrorAction {
  const ErrorAction({
    required this.label,
    required this.onPressed,
    this.isPrimary = false,
  });

  final String label;
  final VoidCallback onPressed;
  final bool isPrimary;
}

/// 带操作按钮的错误 UI 组件
class ErrorActionWidget extends StatelessWidget {
  const ErrorActionWidget({
    super.key,
    required this.errorType,
    required this.message,
    required this.actions,
    this.preservedText,          // 需保护的文本 (AC15)
    this.iconColor,
  });

  final CapsuleErrorType errorType;
  final String message;
  final List<ErrorAction> actions;
  final String? preservedText;
  final Color? iconColor;

  /// 根据错误类型获取默认图标颜色
  Color get _defaultIconColor => switch (errorType) {
    CapsuleErrorType.audioNoDevice => Colors.grey,
    CapsuleErrorType.modelNotFound => Colors.grey,
    _ => Colors.amber,
  };

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // 错误消息
        Text(message, style: const TextStyle(color: Colors.white)),
        if (preservedText != null && preservedText!.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            '"$preservedText"',
            style: TextStyle(color: Colors.white.withOpacity(0.7)),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
        const SizedBox(height: 12),
        // 操作按钮行 (最多 3 个)
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: actions.take(3).map((action) => Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: TextButton(
              onPressed: action.onPressed,
              child: Text(action.label),
            ),
          )).toList(),
        ),
      ],
    );
  }
}
```

- [x] 3.2 修改 `lib/ui/capsule_widget.dart`:
  - 集成 ErrorActionWidget
  - 根据 `stateData.errorType` 决定显示模式
- [x] 3.3 创建 `lib/utils/clipboard_helper.dart`:
  - 使用 Flutter 内置 `Clipboard.setData()` API
  - 封装复制成功提示 (可选 SnackBar 或状态更新)

### Task 4: 增强 ModelManager (AC: #1, #5, #6)

- [x] 4.1 修改 `lib/services/model_manager.dart`:

**新增公共方法规格:**
```dart
class ModelManager {
  // === 已有方法 ===
  // String get modelPath
  // bool get isModelReady
  // ModelStatus checkModelStatus()
  // Future<ModelError> ensureModelReady({ProgressCallback? onProgress})
  // Future<String> downloadModel({...})
  // Future<bool> verifyChecksum(...)
  // Future<void> extractModel(...)

  // === 新增方法 (Story 3-7) ===

  /// 获取模型下载 URL (用于手动安装引导显示)
  static String get downloadUrl => _downloadUrl;

  /// 获取模型根目录路径 (用于手动安装引导显示)
  static String get modelDirectory => _modelBaseDir;

  /// 使用 xdg-open 打开模型目录 (AC6: 打开目录按钮)
  /// 如果目录不存在则先创建
  Future<void> openModelDirectory() async {
    final dir = Directory(modelDirectory);
    if (!dir.existsSync()) {
      dir.createSync(recursive: true);
    }
    await Process.run('xdg-open', [modelDirectory]);
  }

  /// 获取期望的目录结构描述 (用于手动安装引导显示)
  String getExpectedStructure() => '''
models/$_modelName/
├── encoder-epoch-*.onnx
├── decoder-epoch-*.onnx
├── joiner-epoch-*.onnx
└── tokens.txt
''';

  /// 删除现有模型目录 (用于"重新下载"操作)
  Future<void> deleteModel() async {
    final dir = Directory(modelPath);
    if (dir.existsSync()) {
      await dir.delete(recursive: true);
    }
  }
}
```

### Task 5: 增强错误处理服务 (AC: #11-16)

- [x] 5.1 修改 `lib/services/audio_capture.dart`:

**新增设备状态检测规格:**
```dart
/// 音频设备状态枚举
enum AudioDeviceStatus {
  available,        // 设备可用
  noDevice,         // 无设备
  deviceBusy,       // 设备被占用
  permissionDenied, // 权限不足
  unknown,          // 未知状态
}

class AudioCapture {
  // ... 现有代码

  /// 检查音频设备状态 (不初始化流，仅检测)
  /// 用于在录音前预检测设备可用性
  static Future<AudioDeviceStatus> checkDeviceStatus() async {
    // 1. 调用 Pa_Initialize() 初始化 PortAudio
    // 2. 调用 Pa_GetDeviceCount() 检查设备数量
    // 3. 调用 Pa_GetDefaultInputDevice() 获取默认输入设备
    // 4. 尝试打开流但立即关闭 (检测设备是否被占用)
    // 5. 调用 Pa_Terminate() 释放资源
    // 6. 根据结果返回对应状态
  }

  /// 将 PortAudio 错误码映射到 AudioDeviceStatus
  static AudioDeviceStatus _mapPaError(int paErrorCode) {
    // paNoDevice -> AudioDeviceStatus.noDevice
    // paDeviceUnavailable -> AudioDeviceStatus.deviceBusy
    // 其他 -> AudioDeviceStatus.unknown
  }
}
```

- [x] 5.2 修改 `lib/services/audio_inference_pipeline.dart`:
  - 增强运行时设备断开检测 (监听 Pa_ReadStream 返回值)
  - 设备断开时触发 `EndpointEvent(isDeviceLost: true, finalText: _currentText)`
  - 保存 `_currentText` 供后续恢复

- [x] 5.3 修改 `lib/services/hotkey_controller.dart`:
  - 使用 `FcitxError` 细化消息 (见 CapsuleStateData 扩展)
  - 添加 `String? _lastRecognizedText` 字段保存提交失败的文本
  - 实现文本保护逻辑:
    ```dart
    Future<void> _submitText(String text) async {
      if (text.isEmpty) return;
      try {
        await _fcitxClient!.sendText(text);
      } on FcitxException catch (e) {
        _lastRecognizedText = text;  // 保存文本
        _updateState(CapsuleStateData.error(
          CapsuleErrorType.socketError,
          fcitxError: e.error,
          preservedText: text,
        ));
        // 不自动隐藏，等待用户操作
      }
    }
    ```

- [x] 5.4 修改 `lib/services/tray_service.dart`:

**新增功能规格:**
```dart
/// 托盘状态枚举 (用于图标切换)
enum TrayStatus { normal, warning, error }

class TrayService {
  // ... 现有代码

  TrayStatus _currentStatus = TrayStatus.normal;

  /// 更新托盘状态 (切换图标)
  /// ⚠️ system_tray 不支持角标，使用不同图标文件模拟
  Future<void> updateStatus(TrayStatus status) async {
    if (_currentStatus == status) return;
    _currentStatus = status;

    final iconName = switch (status) {
      TrayStatus.normal => 'icon.png',
      TrayStatus.warning => 'icon_warning.png',
      TrayStatus.error => 'icon_error.png',
    };
    await _systemTray.setImage(await _getIconPath(iconName));
  }

  /// 构建托盘右键菜单 (扩展)
  Future<void> _buildMenu() async {
    final menu = Menu();
    await menu.buildFrom([
      MenuItemLabel(label: TrayConstants.menuTitle, enabled: false),
      MenuSeparator(),
      MenuItemLabel(
        label: TrayConstants.menuShowHide,
        onClicked: (_) => _toggleWindow(),
      ),
      MenuItemLabel(
        label: '重新连接 Fcitx5',  // AC16: 新增
        onClicked: (_) => _reconnectFcitx(),
      ),
      MenuItemLabel(label: TrayConstants.menuSettings, enabled: false),
      MenuSeparator(),
      MenuItemLabel(
        label: TrayConstants.menuExit,
        onClicked: (_) => _exitApp(),
      ),
    ]);
    await _systemTray.setContextMenu(menu);
  }

  /// 重新连接 Fcitx5 (AC16)
  Future<void> _reconnectFcitx() async {
    // 由 main.dart 注入的回调
    if (onReconnectFcitx != null) {
      await onReconnectFcitx!();
    }
  }

  /// 重新连接回调 (由 main.dart 注入)
  Future<void> Function()? onReconnectFcitx;
}
```

**需新增图标资源:**
- `assets/icons/icon_warning.png` - 黄色警告图标
- `assets/icons/icon_error.png` - 红色错误图标

### Task 6: 实现全局错误边界 (AC: #17-18)

- [x] 6.1 修改 `lib/main.dart`:
  - 使用 `runZonedGuarded` 包装应用
  - 捕获未处理异常
  - 调用 DiagnosticLogger 记录错误

- [x] 6.2 创建 `lib/ui/fatal_error_dialog.dart`:
  - 显示致命错误信息
  - 提供重启/退出选项

- [x] 6.3 创建 `lib/utils/diagnostic_logger.dart`:

**完整规格:**
```dart
// lib/utils/diagnostic_logger.dart

import 'dart:io';

/// 诊断日志工具
class DiagnosticLogger {
  DiagnosticLogger._();

  static final DiagnosticLogger instance = DiagnosticLogger._();

  /// XDG 数据目录
  static String get _xdgDataHome {
    final xdgData = Platform.environment['XDG_DATA_HOME'];
    if (xdgData != null && xdgData.isNotEmpty) return xdgData;
    final home = Platform.environment['HOME']!;
    return '$home/.local/share';
  }

  /// 日志文件路径
  static String get logPath => '$_xdgDataHome/nextalk/logs/diagnostic.log';

  /// 最大日志文件大小 (1MB)
  static const int _maxLogSize = 1024 * 1024;

  /// 日志级别
  static const String levelDebug = 'DEBUG';
  static const String levelInfo = 'INFO';
  static const String levelWarn = 'WARN';
  static const String levelError = 'ERROR';
  static const String levelFatal = 'FATAL';

  /// 初始化日志系统 (创建目录)
  Future<void> initialize() async {
    final logDir = Directory('$_xdgDataHome/nextalk/logs');
    if (!logDir.existsSync()) {
      logDir.createSync(recursive: true);
    }
    // 检查日志文件大小，超过则轮转
    final logFile = File(logPath);
    if (logFile.existsSync() && logFile.lengthSync() > _maxLogSize) {
      await _rotateLog(logFile);
    }
  }

  /// 日志轮转 (重命名旧文件)
  Future<void> _rotateLog(File logFile) async {
    final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-');
    final backupPath = '${logPath}_$timestamp.bak';
    await logFile.rename(backupPath);
  }

  /// 记录日志
  /// 格式: [ISO8601] [LEVEL] [TAG] message
  void log(String level, String tag, String message) {
    final timestamp = DateTime.now().toIso8601String();
    final line = '[$timestamp] [$level] [$tag] $message\n';

    try {
      File(logPath).writeAsStringSync(line, mode: FileMode.append);
    } catch (e) {
      // 日志写入失败时输出到 stderr
      stderr.writeln('DiagnosticLogger: 写入失败 - $line');
    }
  }

  // 便捷方法
  void debug(String tag, String message) => log(levelDebug, tag, message);
  void info(String tag, String message) => log(levelInfo, tag, message);
  void warn(String tag, String message) => log(levelWarn, tag, message);
  void error(String tag, String message) => log(levelError, tag, message);
  void fatal(String tag, String message) => log(levelFatal, tag, message);

  /// 记录异常 (含堆栈)
  void exception(String tag, Object error, StackTrace? stackTrace) {
    log(levelError, tag, '$error');
    if (stackTrace != null) {
      log(levelError, tag, 'StackTrace:\n$stackTrace');
    }
  }

  /// 导出诊断报告 (用于问题排查)
  Future<String> exportReport() async {
    final buffer = StringBuffer();

    // 1. 系统信息
    buffer.writeln('=== 系统信息 ===');
    buffer.writeln('平台: ${Platform.operatingSystem} ${Platform.operatingSystemVersion}');
    buffer.writeln('Dart 版本: ${Platform.version}');
    buffer.writeln('时间: ${DateTime.now().toIso8601String()}');
    buffer.writeln();

    // 2. 模型状态
    buffer.writeln('=== 模型状态 ===');
    // 由调用方填充

    // 3. 最近日志 (最后 50 行)
    buffer.writeln('=== 最近日志 ===');
    final logFile = File(logPath);
    if (logFile.existsSync()) {
      final lines = await logFile.readAsLines();
      final recentLines = lines.length > 50 ? lines.sublist(lines.length - 50) : lines;
      buffer.writeln(recentLines.join('\n'));
    } else {
      buffer.writeln('(无日志文件)');
    }

    return buffer.toString();
  }
}
```

### Task 7: 集成和测试 (AC: #1-19)

- [x] 7.1 修改 `lib/app/nextalk_app.dart`:
  - 根据初始化状态路由到不同 UI
  - 处理初始化完成后的状态切换
- [x] 7.2 修改 `lib/main.dart`:
  - 实现完整初始化流程
  - 首先检测模型 → 缺失则显示向导 → 完成后进入主界面
- [x] 7.3 创建测试文件:
  - `test/state/init_state_test.dart`
  - `test/ui/init_wizard_test.dart`
  - `test/ui/error_action_widget_test.dart`
  - `test/integration/error_handling_test.dart`
- [x] 7.4 执行完整验证清单

## Dev Notes

### 错误类型与消息映射

| 错误类型 | 显示消息 | 图标颜色 | 操作按钮 |
|----------|----------|----------|----------|
| `audioNoDevice` | 未检测到麦克风 | 灰色 | [刷新检测] [帮助] |
| `audioDeviceBusy` | 麦克风被其他应用占用 | 黄色 | [重试] |
| `audioDeviceLost` | 麦克风已断开 | 黄色 | [重试] |
| `modelNotFound` | 未找到语音模型 | 灰色 | [下载] [手动安装] |
| `modelIncomplete` | 模型文件不完整 | 黄色 | [重新下载] |
| `modelCorrupted` | 模型文件损坏 | 黄色 | [删除并重新下载] |
| `socketError` + `socketNotFound` | Fcitx5 未运行 | 黄色 | [重试] [帮助] |
| `socketError` + `reconnectFailed` | Fcitx5 连接失败 | 黄色 | [重试] (+ 复制文本) |

### 核心流程 (简化)

**初始化流程:**
```
main() → runZonedGuarded → WindowService → TrayService → HotkeyService
    ↓
ModelManager.checkModelStatus()
    ├─ ready → 正常启动
    └─ notFound → 初始化向导 → [自动/手动] → 验证 → 完成
```

**文本保护流程:**
```
说话 → 识别 → 提交 → 成功? → 隐藏窗口
                    ↓ no
              保存文本 → 显示错误 → [复制/重试/放弃]
```

### 集成点

1. **main.dart**: 模型检查分支到初始化向导
2. **nextalk_app.dart**: StreamBuilder 根据状态显示内容
3. **hotkey_controller.dart**: `_submitText` 捕获异常保存文本
4. **capsule_widget.dart**: 根据 errorType 显示 ErrorActionWidget

### 快速验证命令

```bash
cd /mnt/disk0/project/newx/nextalk/nextalk_fcitx5_v2/voice_capsule

# 1. 模拟首次运行 (删除模型)
rm -rf ~/.local/share/nextalk/models

# 2. 运行应用
flutter run -d linux

# 3. 验证各 AC (参见 Acceptance Criteria 表格)

# 4. 恢复模型后测试其他错误场景
# - 停止 Fcitx5: fcitx5 -d -r
# - 拔掉麦克风测试音频错误
```

### Git 提交信息模板

```
feat: 实现初始化向导与异常处理系统

- 新增初始化向导 UI (自动下载/手动安装)
- 细化错误类型和消息映射
- 实现错误操作 UI 组件
- 增强音频/模型/Socket 错误处理
- 添加文本保护机制
- 实现全局错误边界
- 新增诊断日志系统

Story: 3-7
Epic: 3 (完整产品体验)
Sprint Change Proposal: 2025-12-23
```

### References

- [docs/prd.md](docs/prd.md) - 产品需求文档
- [docs/architecture.md](docs/architecture.md) - 系统架构文档
- [docs/front-end-spec.md](docs/front-end-spec.md) - UX 交互规范 (Section 3.2, 6)
- [_bmad-output/sprint-change-proposal-2025-12-23.md](_bmad-output/sprint-change-proposal-2025-12-23.md) - 变更提案
- [3-6-full-business-flow.md](3-6-full-business-flow.md) - 前置 Story 参考

## Dev Agent Record

### Agent Model Used

(待开发时填写)

### Debug Log References

(待开发时填写)

### Completion Notes List

(待开发时填写)

### File List

| 文件 | 操作 | 说明 |
|------|------|------|
| `lib/state/capsule_state.dart` | 🔄 修改 | 扩展状态枚举，添加 fcitxError 字段 |
| `lib/state/init_state.dart` | 🆕 新增 | 初始化状态管理 |
| `lib/ui/init_wizard/init_mode_selector.dart` | 🆕 新增 | 安装方式选择 |
| `lib/ui/init_wizard/download_progress.dart` | 🆕 新增 | 下载进度 |
| `lib/ui/init_wizard/manual_install_guide.dart` | 🆕 新增 | 手动安装引导 |
| `lib/ui/error_action_widget.dart` | 🆕 新增 | 错误操作组件 |
| `lib/ui/fatal_error_dialog.dart` | 🆕 新增 | 致命错误对话框 |
| `lib/ui/capsule_widget.dart` | 🔄 修改 | 集成错误操作组件 |
| `lib/services/model_manager.dart` | 🔄 修改 | 新增 downloadUrl, modelDirectory, openModelDirectory, getExpectedStructure, deleteModel |
| `lib/services/audio_capture.dart` | 🔄 修改 | 新增 AudioDeviceStatus 枚举和 checkDeviceStatus() |
| `lib/services/audio_inference_pipeline.dart` | 🔄 修改 | 运行时设备断开检测 |
| `lib/services/hotkey_controller.dart` | 🔄 修改 | 文本保护，使用 FcitxError 细化 |
| `lib/services/tray_service.dart` | 🔄 修改 | 重连菜单 + TrayStatus 状态切换 |
| `lib/utils/clipboard_helper.dart` | 🆕 新增 | 剪贴板工具 |
| `lib/utils/diagnostic_logger.dart` | 🆕 新增 | 诊断日志系统 |
| `lib/main.dart` | 🔄 修改 | 全局错误边界+初始化流程 |
| `lib/app/nextalk_app.dart` | 🔄 修改 | 状态路由 |
| `assets/icons/icon_warning.png` | 🆕 新增 | 警告状态托盘图标 |
| `assets/icons/icon_error.png` | 🆕 新增 | 错误状态托盘图标 |

---

## SM Validation Record

| Date | Validator | Result | Notes |
|------|-----------|--------|-------|
| 2025-12-23 | SM Agent (Bob) | ✅ PASS (after improvements) | 应用了 3 个关键修复, 4 个增强, 3 个优化 |

**Applied Improvements:**

| # | Category | Issue | Fix Applied |
|---|----------|-------|-------------|
| C1 | CRITICAL | ModelManager 新增方法缺少完整规格 | ✅ 添加完整方法签名和代码示例 |
| C2 | CRITICAL | init_state.dart 缺少状态机定义 | ✅ 添加完整 InitPhase 枚举和 InitStateData 类 |
| C3 | CRITICAL | CapsuleErrorType 与 FcitxError 重复定义 | ✅ 统一使用 socketError + fcitxError 字段 |
| E1 | ENHANCE | AudioCapture.checkDeviceStatus() 缺少规格 | ✅ 添加 AudioDeviceStatus 枚举和方法规格 |
| E2 | ENHANCE | 托盘状态角标实现不明确 | ✅ 添加 TrayStatus 枚举、updateStatus() 方法和图标资源需求 |
| E3 | ENHANCE | ErrorActionWidget 回调规格缺失 | ✅ 添加完整组件定义和 ErrorAction 类 |
| E4 | ENHANCE | DiagnosticLogger 日志格式未定义 | ✅ 添加完整类实现，包含日志轮转和诊断报告导出 |
| O1 | OPTIMIZE | Dev Notes 架构约束表与 Tech Spec 重复 | ✅ 删除重复表格 |
| O2 | OPTIMIZE | 大型 ASCII 流程图占用过多空间 | ✅ 简化为紧凑文本格式 |
| O3 | OPTIMIZE | 手动验证清单与 AC 表格重复 | ✅ 删除重复清单，引用 AC 表格 |

**Validation Summary:**
- Story 结构完整，符合 BMAD 标准
- 19 条验收标准全部可追溯到 Tasks
- 所有新增代码均有完整规格示例
- 与现有代码 (FcitxError, ModelManager, TrayService) 集成点明确
- Token 优化: 删除约 85 行重复内容
