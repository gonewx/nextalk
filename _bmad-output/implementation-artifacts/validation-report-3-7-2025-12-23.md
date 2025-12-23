# Validation Report

**Document:** _bmad-output/implementation-artifacts/3-7-init-wizard-error-handling.md
**Checklist:** _bmad/bmm/workflows/4-implementation/create-story/checklist.md
**Date:** 2025-12-23

## Summary
- Overall: 41/48 passed (85%)
- Critical Issues: 3
- Enhancement Opportunities: 4
- LLM Optimization Issues: 3

## Section Results

### Story Structure & Format
Pass Rate: 6/6 (100%)

✓ **Status field present**: `Status: ready-for-dev` (Line 3)
✓ **Prerequisites documented**: Lines 5-12, 完整列出前置依赖
✓ **Story format complete**: As/I want/So that 格式完整 (Lines 14-17)
✓ **Acceptance Criteria table**: 19 个 AC 完整定义 (Lines 19-63)
✓ **Technical specification present**: Lines 67-144, 包含状态扩展和文件结构
✓ **Tasks/Subtasks defined**: 7 个主 Task，完整拆分 (Lines 218-310)

### Acceptance Criteria Quality
Pass Rate: 17/19 (89%)

✓ AC1-7: 初次运行引导 - 具体且可验证
✓ AC8-10: 模型错误处理 - 具体且可验证
✓ AC11-13: 音频错误处理 - 具体且可验证
✓ AC14-16: Socket/Fcitx5 错误处理 - 具体且可验证
✓ AC17-19: 运行时异常处理 - 具体且可验证

⚠ **PARTIAL** AC13 "运行时设备断开时保存已识别文本并显示警告"
Evidence: Task 5.2 提及 "保存已识别文本" 但未提供具体实现代码示例
Impact: 开发者可能不清楚文本保存位置和恢复机制

⚠ **PARTIAL** AC19 "托盘图标显示连接状态角标"
Evidence: Task 5.4 提及 "实现状态角标 (正常/警告/错误)" 但未提供技术实现细节
Impact: 开发者不清楚如何在 system_tray 包中实现动态图标

### Technical Specification Alignment
Pass Rate: 8/10 (80%)

✓ **State enum extension**: 正确扩展 `CapsuleState` 和 `CapsuleErrorType`
✓ **File structure**: 符合现有架构模式 (`lib/ui/`, `lib/state/`, `lib/utils/`)
✓ **UI design mockups**: 提供 ASCII 原型图 (Lines 147-215)
✓ **Error type mapping**: 完整映射错误类型到消息和操作 (Lines 323-335)
✓ **Initialization flow**: 完整流程图 (Lines 337-361)
✓ **Text protection flow**: 完整流程图 (Lines 363-385)

✗ **FAIL** ModelManager 方法签名不完整
Evidence: Task 4.1 列出 `getDownloadUrl()`, `getModelDirectory()`, `openModelDirectory()`, `getExpectedStructure()` 但未提供方法签名和返回类型
Impact: 开发者可能实现不一致的 API

✗ **FAIL** init_state.dart 缺少完整类定义
Evidence: Task 1.2 提及 `InitPhase` 枚举和 `InitStateData` 类但无代码示例
Impact: 开发者需要自行设计状态机，可能与现有模式不一致

### Previous Story Context Integration
Pass Rate: 5/7 (71%)

✓ **References Story 3-6**: 正确引用前置 Story (Line 464)
✓ **Uses existing CapsuleStateData**: 扩展现有模式而非重建
✓ **Uses existing TrayService pattern**: 基于现有服务扩展
✓ **Uses existing HotkeyController pattern**: 修改而非重写
✓ **Architecture alignment**: 符合 docs/architecture.md 模式

⚠ **PARTIAL** 未引用 Story 3-5 的错误处理学习
Evidence: Story 3-5 实现了 `HotkeyController._handleError()` 方法，但本 Story 未说明如何扩展此方法以支持细化的错误类型
Impact: 可能导致错误处理逻辑分散

✗ **FAIL** 未引用现有 FcitxClient 错误类型
Evidence: `FcitxClient` 已有 `FcitxError` 枚举 (socketNotFound, connectionFailed, etc.)，但 Story 建议在 `CapsuleErrorType` 中重复定义类似类型
Impact: 可能导致错误类型重复定义

### Code Reuse & Anti-Pattern Prevention
Pass Rate: 5/6 (83%)

✓ **Uses existing StreamController pattern**: 与 Story 3-6 一致
✓ **Uses existing WindowService**: 无重复实现
✓ **Uses existing ModelManager**: 扩展而非重写
✓ **Uses existing UI components**: 修改 CapsuleWidget 而非新建
✓ **Follows existing test patterns**: 测试文件结构一致

⚠ **PARTIAL** clipboard_helper.dart 可能重复造轮
Evidence: Flutter 已有 `Clipboard.setData()` API，新建 helper 可能过度封装
Impact: 增加不必要的抽象层

---

## 🚨 CRITICAL ISSUES (Must Fix)

### C1: ModelManager 新增方法缺少完整规格

**问题**: Task 4.1 列出 4 个新方法但未提供：
- 方法签名 (参数类型、返回类型)
- 异常处理策略
- 与现有 `ensureModelReady()` 的关系

**修复建议**: 在 Task 4.1 添加完整方法规格：

```dart
// 新增公共方法规格
class ModelManager {
  // 已有: modelPath, isModelReady, checkModelStatus(), ensureModelReady()

  /// 获取模型下载 URL
  static String get downloadUrl => _downloadUrl;

  /// 获取模型根目录路径
  static String get modelDirectory => _modelBaseDir;

  /// 使用 xdg-open 打开模型目录
  Future<void> openModelDirectory() async {
    await Process.run('xdg-open', [modelDirectory]);
  }

  /// 获取期望的目录结构描述 (用于手动安装引导)
  String getExpectedStructure() => '''
models/$_modelName/
├── encoder-*.onnx
├── decoder-*.onnx
├── joiner-*.onnx
└── tokens.txt
''';
}
```

---

### C2: init_state.dart 缺少状态机定义

**问题**: Task 1.2 提及 `InitPhase` 和 `InitStateData` 但无代码，开发者需自行设计。

**修复建议**: 添加完整状态机代码示例：

```dart
// lib/state/init_state.dart

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
    this.errorMessage,
    this.canRetry = false,
  });

  final InitPhase phase;
  final double progress;      // 0.0 - 1.0
  final String statusMessage;
  final String? errorMessage;
  final bool canRetry;

  // 工厂构造函数...
  factory InitStateData.checking() => const InitStateData(phase: InitPhase.checkingModel);
  factory InitStateData.downloading(double progress) => InitStateData(
    phase: InitPhase.downloading,
    progress: progress,
    statusMessage: '下载中: ${(progress * 100).toStringAsFixed(1)}%',
  );
  // ... 其他工厂方法
}
```

---

### C3: FcitxError 与 CapsuleErrorType 重复定义

**问题**: `FcitxClient` 已有完整的 `FcitxError` 枚举：
- socketNotFound
- connectionFailed
- sendFailed
- reconnectFailed

Story 建议在 `CapsuleErrorType` 中添加类似类型，造成重复。

**修复建议**:
1. `CapsuleErrorType` 保持高层抽象 (socket 系列合并为一个)
2. 错误消息映射时使用 `FcitxError` 细化：

```dart
// 修改 _defaultErrorMessage getter
String get _defaultErrorMessage {
  switch (errorType) {
    case CapsuleErrorType.socketError:
      // 使用 FcitxError 细化消息
      if (fcitxError == FcitxError.socketNotFound) {
        return 'Fcitx5 未运行，请先启动输入法';
      } else if (fcitxError == FcitxError.reconnectFailed) {
        return 'Fcitx5 连接失败，请检查服务状态';
      }
      return 'Fcitx5 未连接';
    // ...
  }
}
```

---

## ⚡ ENHANCEMENT OPPORTUNITIES (Should Add)

### E1: 添加 AudioCapture.checkDeviceStatus() 规格

Task 5.1 提及添加静态方法但未提供完整规格：

```dart
/// 音频设备状态
enum AudioDeviceStatus {
  available,        // 设备可用
  noDevice,         // 无设备
  deviceBusy,       // 设备被占用
  permissionDenied, // 权限不足
}

class AudioCapture {
  /// 检查音频设备状态 (不初始化流)
  static Future<AudioDeviceStatus> checkDeviceStatus() async {
    // 使用 Pa_GetDeviceCount() 和 Pa_GetDefaultInputDevice()
  }
}
```

---

### E2: 添加托盘状态角标实现说明

system_tray 包不直接支持角标，需说明替代方案：

```dart
// TrayService 扩展
enum TrayStatus { normal, warning, error }

/// 更新托盘图标以反映状态
Future<void> updateStatus(TrayStatus status) async {
  final iconName = switch (status) {
    TrayStatus.normal => 'icon.png',
    TrayStatus.warning => 'icon_warning.png',
    TrayStatus.error => 'icon_error.png',
  };
  await _systemTray.setImage(await _getIconPath(iconName));
}
```

**需新增图标文件**:
- `assets/icons/icon_warning.png`
- `assets/icons/icon_error.png`

---

### E3: 补充 ErrorActionWidget 按钮回调规格

Task 3.1 未说明按钮回调如何与状态管理集成：

```dart
class ErrorActionWidget extends StatelessWidget {
  const ErrorActionWidget({
    required this.errorType,
    required this.onPrimaryAction,   // 主操作 (刷新/重试)
    this.onSecondaryAction,          // 次要操作 (帮助/手动)
    this.onDismiss,                  // 关闭
    this.preservedText,              // 需保护的文本
  });
}
```

---

### E4: 添加 DiagnosticLogger 日志格式规格

Task 6.3 未说明日志格式和存储位置：

```dart
class DiagnosticLogger {
  static final _logPath = '${_xdgDataHome}/nextalk/logs/diagnostic.log';

  /// 日志格式: [ISO8601] [LEVEL] [TAG] message
  static void log(String level, String tag, String message) {
    final timestamp = DateTime.now().toIso8601String();
    final line = '[$timestamp] [$level] [$tag] $message\n';
    File(_logPath).writeAsStringSync(line, mode: FileMode.append);
  }

  /// 导出诊断报告 (用于问题排查)
  static Future<String> exportReport() async {
    // 收集: 系统信息、模型状态、最近日志
  }
}
```

---

## 🤖 LLM OPTIMIZATION (Token Efficiency & Clarity)

### O1: Dev Notes 部分冗余

**问题**: "架构约束与禁止事项" 表格与 Technical Specification 内容重复。

**建议**: 合并到 Technical Specification，删除 Dev Notes 中的重复内容。

---

### O2: 流程图可简化

**问题**: 两个大型 ASCII 流程图 (Lines 337-361, 363-385) 占用大量 Token。

**建议**: 使用更紧凑的格式：

```
启动 → ModelManager.check() → ready? → 主流程
                           ↓ no
                      初始化向导 → [自动/手动] → 验证 → 完成
```

---

### O3: 手动验证清单与 AC 重复

**问题**: Lines 415-438 的验证清单与 Lines 19-63 的 AC 表格内容完全重复。

**建议**: 删除手动验证清单，保留 AC 表格即可。开发者可直接使用 AC 表格进行验证。

---

## Recommendations

### 1. Must Fix (Critical)
- C1: 添加 ModelManager 方法完整规格
- C2: 添加 init_state.dart 完整代码示例
- C3: 统一使用 FcitxError 而非重复定义

### 2. Should Improve (Enhancements)
- E1: 添加 AudioCapture.checkDeviceStatus() 完整规格
- E2: 添加托盘状态角标实现说明和图标资源需求
- E3: 添加 ErrorActionWidget 回调规格
- E4: 添加 DiagnosticLogger 日志格式规格

### 3. Consider (Optimizations)
- O1: 删除 Dev Notes 中的重复约束表格
- O2: 简化流程图格式
- O3: 删除重复的手动验证清单

---

*Validation performed by: SM Agent (Bob)*
*Date: 2025-12-23*
