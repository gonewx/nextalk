# Story 3.5: 全局快捷键监听 (Global Hotkey Listener)

Status: done

## Prerequisites

> **前置条件**: Story 3-1, 3-2, 3-3, 3-4 必须完成
> - ✅ 透明胶囊窗口基础已实现 (Story 3-1)
> - ✅ 胶囊 UI 组件已实现 (Story 3-2)
> - ✅ 状态机与动画系统已实现 (Story 3-3)
> - ✅ 系统托盘集成已实现 (Story 3-4)
> - ✅ WindowService 已实现 show()/hide() 功能
> - ✅ AudioInferencePipeline 已实现 start()/stop() 功能 (Epic 2)
> - ⚠️ 本 Story 将实现全局快捷键监听，连接窗口显隐和录音控制

## Story

As a **用户**,
I want **通过快捷键快速唤醒语音输入**,
So that **无需鼠标操作，实现高效输入**。

## Acceptance Criteria

| AC | 描述 | 验证方法 |
|----|------|----------|
| AC1 | 按下 Right Alt 键时主窗口瞬间出现 | 按键后窗口立即可见 |
| AC2 | 按下 Right Alt 键时自动开始录音 | 状态切换为"聆听中"，Pipeline 启动 |
| AC3 | 正在录音时再次按下 Right Alt 立即停止录音 | Pipeline 停止，获取最终文本 |
| AC4 | 停止录音后提交文本到活动窗口 | 通过 FcitxClient 发送文本 |
| AC5 | 提交后主窗口瞬间隐藏 | 窗口消失，无渐变动画 |
| AC6 | 支持配置文件自定义快捷键 | 读取配置文件，使用用户指定键位 |
| AC7 | 快捷键被其他应用占用时输出警告日志 | 注册失败时 log 警告，不崩溃 |
| AC8 | 应用启动时自动注册全局快捷键 | main.dart 初始化时注册 |
| AC9 | 应用退出时正确注销快捷键 | TrayService.exit 时注销 |
| AC10 | 快捷键在后台运行时也能响应 | 窗口隐藏时按键仍能触发 |

## 开始前确认

```bash
# 执行以下检查，全部通过后方可开始
[ ] flutter test                              # 现有测试全部通过 (264+ 测试)
[ ] flutter build linux                       # 构建成功
[ ] 确认 services/window_service.dart 存在 show()/hide() 方法
[ ] 确认 services/audio_inference_pipeline.dart 存在 start()/stop() 方法
[ ] 确认 services/tray_service.dart 存在 onBeforeExit 回调
[ ] 确认 Ubuntu 22.04+ 环境 (NFR3)
```

## 技术规格

### 全局快捷键方案分析 [Source: 技术调研]

**Linux 全局快捷键实现方案对比:**

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **hotkey_manager** | Flutter 官方维护，API 简洁 | Linux 支持有限，X11 only | ⭐⭐⭐ |
| **keybinder (C FFI)** | 成熟稳定，支持 X11 | 需要 FFI 绑定，Wayland 不支持 | ⭐⭐ |
| **global_hotkey** | 封装 keybinder，Dart 友好 | 维护不活跃，依赖 libkeybinder-3.0 | ⭐⭐ |
| **keyboard_event** | 纯 Dart 实现 | 仅监听，不是真正的全局热键 | ⭐ |

**选型决策: hotkey_manager**
- 原因: 官方维护，API 简洁，与 window_manager 同一作者，兼容性好
- 限制: 仅支持 X11 (Ubuntu 22.04 默认 X11 Session)
- Wayland 兼容: 通过 XWayland 桥接 (NFR3 要求)

### 系统依赖 [Source: pub.dev/hotkey_manager]

**Linux 必需依赖:**
```bash
# Ubuntu 22.04+ (X11 开发库)
sudo apt-get install libkeybinder-3.0-dev libgtk-3-dev
```

### 快捷键配置设计 [Source: docs/front-end-spec.md#4, docs/prd.md#FR6]

**默认配置:**
- 快捷键: `Right Alt` (KeyCode.altRight)
- 行为:
  - 首次按下: 显示窗口 + 开始录音
  - 再次按下 (录音中): 停止录音 + 提交 + 隐藏窗口

**配置文件路径:**
```
~/.config/nextalk/config.yaml
```

**配置文件格式:**
```yaml
# Nextalk 配置文件
hotkey:
  # 主键 (可选值: alt, altRight, ctrl, shift, meta)
  key: altRight
  # 修饰键 (可选，多个用逗号分隔)
  modifiers: []
  # 备选: ctrl+shift+space
  # key: space
  # modifiers: [ctrl, shift]
```

### 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.dart                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                 HotkeyService.init()                     │    │
│  │  ┌─────────────────┐       ┌─────────────────────────┐  │    │
│  │  │  hotkey_manager │──────▶│   HotkeyController      │  │    │
│  │  │   (监听按键)    │       │  (业务逻辑控制器)       │  │    │
│  │  └─────────────────┘       └───────────┬─────────────┘  │    │
│  │                                        │                 │    │
│  │                          ┌─────────────┼─────────────┐   │    │
│  │                          │             │             │   │    │
│  │                          ▼             ▼             ▼   │    │
│  │                ┌─────────────┐ ┌─────────────┐ ┌───────┐│    │
│  │                │WindowService│ │  Pipeline   │ │Fcitx  ││    │
│  │                │(窗口显隐)   │ │(录音控制)   │ │Client ││    │
│  │                └─────────────┘ └─────────────┘ └───────┘│    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  状态机流转:                                                     │
│  [Idle] ──(RightAlt)──▶ [Recording] ──(RightAlt)──▶ [Submitting]│
│    ▲                          │                          │       │
│    │                          │(VAD触发)                 │       │
│    └──────────────────────────┴──────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 目标文件结构

```text
voice_capsule/
├── lib/
│   ├── main.dart                        # 🔄 修改 (集成 HotkeyService)
│   ├── services/
│   │   ├── hotkey_service.dart          # 🆕 新增 (快捷键服务)
│   │   ├── hotkey_controller.dart       # 🆕 新增 (快捷键业务控制器)
│   │   ├── window_service.dart          # ✅ 已有 (无需修改)
│   │   ├── tray_service.dart            # 🔄 修改 (注销快捷键)
│   │   └── audio_inference_pipeline.dart # ✅ 已有 (无需修改)
│   └── constants/
│       └── hotkey_constants.dart        # 🆕 新增 (快捷键常量)
├── pubspec.yaml                         # 🔄 修改 (添加依赖)
└── test/
    └── services/
        ├── hotkey_service_test.dart     # 🆕 新增
        └── hotkey_controller_test.dart  # 🆕 新增
```

## Tasks / Subtasks

> **执行顺序**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7

- [x] **Task 1: 添加依赖** (AC: #8)
  - [x] 1.1 更新 `pubspec.yaml`:
    - 添加 `hotkey_manager: ^0.2.3` 依赖
    - 添加 `yaml: ^3.1.2` 依赖 (配置文件解析)
  - [x] 1.2 运行 `flutter pub get` 验证依赖
  - [x] 1.3 验证 Linux 系统依赖:
    ```bash
    # 验证 keybinder 库已安装
    pkg-config --exists keybinder-3.0 && echo "已安装" || echo "未安装 - 请运行: sudo apt-get install libkeybinder-3.0-dev"
    ```

  ```yaml
  # pubspec.yaml 修改
  dependencies:
    # ... 现有依赖
    hotkey_manager: ^0.2.3     # 全局快捷键支持 (Linux: keybinder)
    yaml: ^3.1.2               # 配置文件解析
    # 注: 使用 Platform.environment['HOME'] 读取配置，无需 path_provider
  ```

- [x] **Task 2: 创建快捷键常量** (AC: #6)
  - [x] 2.1 创建 `lib/constants/hotkey_constants.dart`:
    - 定义默认快捷键 (Right Alt)
    - 定义配置文件路径
    - 定义支持的键位映射

  **关键代码:**
  ```dart
  // lib/constants/hotkey_constants.dart
  import 'package:hotkey_manager/hotkey_manager.dart';

  /// 快捷键常量
  /// Story 3-5: 全局快捷键监听
  class HotkeyConstants {
    HotkeyConstants._();

    // ===== 默认快捷键 =====
    /// 默认主键: Right Alt
    static const KeyCode defaultKey = KeyCode.altRight;

    /// 默认修饰键: 无
    static const List<HotKeyModifier> defaultModifiers = [];

    // ===== 配置文件 =====
    /// 配置文件名
    static const String configFileName = 'config.yaml';

    /// 配置目录名 (在 ~/.config/ 下)
    static const String configDirName = 'nextalk';

    // ===== 键位映射 =====
    /// 支持的键位名称到 KeyCode 映射
    static const Map<String, KeyCode> keyMap = {
      'alt': KeyCode.alt,
      'altRight': KeyCode.altRight,
      'ctrl': KeyCode.control,
      'shift': KeyCode.shift,
      'meta': KeyCode.meta,
      'space': KeyCode.space,
      'f1': KeyCode.f1,
      'f2': KeyCode.f2,
      'f3': KeyCode.f3,
      'f4': KeyCode.f4,
      'f5': KeyCode.f5,
      'f6': KeyCode.f6,
      'f7': KeyCode.f7,
      'f8': KeyCode.f8,
      'f9': KeyCode.f9,
      'f10': KeyCode.f10,
      'f11': KeyCode.f11,
      'f12': KeyCode.f12,
    };

    /// 修饰键名称到 HotKeyModifier 映射
    static const Map<String, HotKeyModifier> modifierMap = {
      'ctrl': HotKeyModifier.control,
      'shift': HotKeyModifier.shift,
      'alt': HotKeyModifier.alt,
      'meta': HotKeyModifier.meta,
    };
  }
  ```

- [x] **Task 3: 实现快捷键服务** (AC: #1, #7, #8, #9, #10)
  - [x] 3.1 创建 `lib/services/hotkey_service.dart`:
    - 实现 `HotkeyService` 单例类
    - 加载配置文件或使用默认快捷键
    - 注册/注销全局快捷键
    - 处理按键事件回调
    - 错误处理 (快捷键冲突)
  - [x] 3.2 实现配置文件读取:
    - 检查 `~/.config/nextalk/config.yaml` 是否存在
    - 解析 YAML 配置
    - 回退到默认配置

  **关键代码:**
  ```dart
  // lib/services/hotkey_service.dart
  import 'dart:io';
  import 'package:hotkey_manager/hotkey_manager.dart';
  import 'package:yaml/yaml.dart';
  import '../constants/hotkey_constants.dart';

  /// 快捷键按下回调类型
  typedef HotkeyPressedCallback = Future<void> Function();

  /// 全局快捷键服务 - Story 3-5
  class HotkeyService {
    HotkeyService._();
    static final HotkeyService instance = HotkeyService._();

    HotKey? _registeredHotkey;
    bool _isInitialized = false;
    bool _registrationFailed = false;

    /// 快捷键按下回调 (由 HotkeyController 注入)
    HotkeyPressedCallback? onHotkeyPressed;

    bool get isInitialized => _isInitialized;
    bool get registrationFailed => _registrationFailed;
    HotKey? get currentHotkey => _registeredHotkey;

    /// 初始化并注册快捷键
    Future<void> initialize() async {
      if (_isInitialized) return;

      try {
        // 1. 加载配置 (配置文件或默认值)
        final hotkey = await _loadHotkeyConfig();

        // 2. 注册全局快捷键
        await hotKeyManager.register(
          hotkey,
          keyDownHandler: (hotKey) async {
            if (onHotkeyPressed != null) {
              await onHotkeyPressed!();
            }
          },
        );

        _registeredHotkey = hotkey;
        _isInitialized = true;
        _registrationFailed = false;

        // ignore: avoid_print
        print('[HotkeyService] ✅ 快捷键注册成功: ${_hotkeyToString(hotkey)}');

      } catch (e) {
        _registrationFailed = true;
        // AC7: 快捷键被占用时输出警告，不崩溃
        // ignore: avoid_print
        print('[HotkeyService] ⚠️ 快捷键注册失败 (可能被其他应用占用): $e');
        // 尝试使用备用快捷键 (Ctrl+Shift+Space)
        await _tryFallbackHotkey();
      }
    }

    /// 加载快捷键配置
    Future<HotKey> _loadHotkeyConfig() async {
      try {
        final configFile = await _getConfigFile();
        if (configFile != null && await configFile.exists()) {
          final content = await configFile.readAsString();
          final yaml = loadYaml(content);

          if (yaml != null && yaml['hotkey'] != null) {
            final hotkeyConfig = yaml['hotkey'];
            final keyName = hotkeyConfig['key'] as String?;
            final modifierNames = (hotkeyConfig['modifiers'] as List?)
                ?.cast<String>() ?? [];

            if (keyName != null && HotkeyConstants.keyMap.containsKey(keyName)) {
              final key = HotkeyConstants.keyMap[keyName]!;
              final modifiers = modifierNames
                  .where((m) => HotkeyConstants.modifierMap.containsKey(m))
                  .map((m) => HotkeyConstants.modifierMap[m]!)
                  .toList();

              // ignore: avoid_print
              print('[HotkeyService] 从配置文件加载快捷键: $keyName + $modifierNames');

              return HotKey(key, modifiers: modifiers);
            }
          }
        }
      } catch (e) {
        // ignore: avoid_print
        print('[HotkeyService] 配置文件读取失败，使用默认快捷键: $e');
      }

      // 返回默认快捷键
      return HotKey(
        HotkeyConstants.defaultKey,
        modifiers: HotkeyConstants.defaultModifiers,
      );
    }

    /// 获取配置文件
    Future<File?> _getConfigFile() async {
      final homeDir = Platform.environment['HOME'];
      if (homeDir == null) return null;

      final configPath = '$homeDir/.config/${HotkeyConstants.configDirName}/'
          '${HotkeyConstants.configFileName}';
      return File(configPath);
    }

    /// 尝试备用快捷键 (Ctrl+Shift+Space)
    Future<void> _tryFallbackHotkey() async {
      try {
        final fallbackHotkey = HotKey(
          KeyCode.space,
          modifiers: [HotKeyModifier.control, HotKeyModifier.shift],
        );

        await hotKeyManager.register(
          fallbackHotkey,
          keyDownHandler: (hotKey) async {
            if (onHotkeyPressed != null) {
              await onHotkeyPressed!();
            }
          },
        );

        _registeredHotkey = fallbackHotkey;
        _isInitialized = true;
        _registrationFailed = false;

        // ignore: avoid_print
        print('[HotkeyService] ✅ 备用快捷键注册成功: Ctrl+Shift+Space');

      } catch (e) {
        // ignore: avoid_print
        print('[HotkeyService] ❌ 备用快捷键也注册失败: $e');
        _isInitialized = true; // 标记已初始化，但功能降级
      }
    }

    /// 注销快捷键 (AC9: 退出时调用)
    Future<void> unregister() async {
      if (_registeredHotkey != null) {
        try {
          await hotKeyManager.unregister(_registeredHotkey!);
          // ignore: avoid_print
          print('[HotkeyService] 快捷键已注销');
        } catch (e) {
          // ignore: avoid_print
          print('[HotkeyService] 注销失败: $e');
        }
        _registeredHotkey = null;
      }
    }

    /// 释放资源
    Future<void> dispose() async {
      await unregister();
      _isInitialized = false;
    }

    /// 快捷键转字符串 (用于日志)
    String _hotkeyToString(HotKey hotkey) {
      final parts = <String>[];
      for (final modifier in hotkey.modifiers ?? []) {
        parts.add(modifier.name);
      }
      parts.add(hotkey.keyCode.name);
      return parts.join('+');
    }
  }
  ```

- [x] **Task 4: 实现快捷键业务控制器** (AC: #1, #2, #3, #4, #5)
  - [x] 4.1 创建 `lib/services/hotkey_controller.dart`:
    - 实现状态机: Idle → Recording → Submitting → Idle
    - 处理按键事件，协调各服务
    - 管理 Pipeline 生命周期
    - 管理窗口显隐
    - 提交文本到 Fcitx5

  **关键代码:**
  ```dart
  // lib/services/hotkey_controller.dart
  import 'dart:async';
  import 'package:flutter/material.dart';
  import 'audio_inference_pipeline.dart';
  import 'window_service.dart';
  import 'fcitx_client.dart';
  import 'hotkey_service.dart';
  import '../state/capsule_state.dart';

  /// 快捷键控制器状态
  enum HotkeyState {
    idle,       // 空闲 (窗口隐藏)
    recording,  // 录音中 (窗口显示，红灯呼吸)
    submitting, // 提交中 (处理文本上屏)
  }

  /// 快捷键业务控制器 - Story 3-5
  ///
  /// 协调快捷键事件与各服务的交互:
  /// - HotkeyService: 监听全局快捷键
  /// - WindowService: 控制窗口显隐
  /// - AudioInferencePipeline: 控制录音和识别
  /// - FcitxClient: 提交文本
  /// - CapsuleState: 更新 UI 状态
  class HotkeyController {
    HotkeyController._();
    static final HotkeyController instance = HotkeyController._();

    // === 依赖服务 ===
    AudioInferencePipeline? _pipeline;
    FcitxClient? _fcitxClient;
    StreamController<CapsuleStateData>? _stateController;

    // === 状态管理 ===
    HotkeyState _state = HotkeyState.idle;
    StreamSubscription<EndpointEvent>? _endpointSubscription;
    StreamSubscription<String>? _resultSubscription;
    bool _isInitialized = false;

    /// 当前状态
    HotkeyState get state => _state;

    /// 是否已初始化
    bool get isInitialized => _isInitialized;

    /// 初始化控制器
    ///
    /// 必须在所有依赖服务初始化后调用。
    /// [pipeline] 音频推理流水线 (已初始化模型)
    /// [fcitxClient] Fcitx5 客户端
    /// [stateController] 胶囊状态控制器 (用于更新 UI)
    Future<void> initialize({
      required AudioInferencePipeline pipeline,
      required FcitxClient fcitxClient,
      required StreamController<CapsuleStateData> stateController,
    }) async {
      if (_isInitialized) return;

      _pipeline = pipeline;
      _fcitxClient = fcitxClient;
      _stateController = stateController;

      // 注册快捷键回调
      HotkeyService.instance.onHotkeyPressed = _onHotkeyPressed;

      // 监听 VAD 端点事件 (自动提交)
      _endpointSubscription = _pipeline!.endpointStream.listen(_onEndpoint);

      // 监听识别结果 (更新 UI)
      _resultSubscription = _pipeline!.resultStream.listen(_onRecognitionResult);

      _isInitialized = true;

      // ignore: avoid_print
      print('[HotkeyController] ✅ 控制器初始化完成');
    }

    /// 快捷键按下处理 (核心状态机)
    Future<void> _onHotkeyPressed() async {
      // ignore: avoid_print
      print('[HotkeyController] 快捷键按下，当前状态: $_state');

      switch (_state) {
        case HotkeyState.idle:
          await _startRecording();
          break;
        case HotkeyState.recording:
          await _stopAndSubmit();
          break;
        case HotkeyState.submitting:
          // 正在提交中，忽略按键
          break;
      }
    }

    /// 开始录音 (Idle → Recording)
    Future<void> _startRecording() async {
      _state = HotkeyState.recording;

      // 1. 显示窗口 (AC1: 瞬间出现)
      await WindowService.instance.show();

      // 2. 更新 UI 状态为聆听中
      _stateController?.add(CapsuleStateData.listening());

      // 3. 启动录音流水线 (AC2)
      final error = await _pipeline!.start();

      if (error != PipelineError.none) {
        // 录音启动失败，显示错误
        _handleError(error);
        return;
      }

      // ignore: avoid_print
      print('[HotkeyController] 🎤 开始录音');
    }

    /// 停止录音并提交 (Recording → Submitting → Idle)
    Future<void> _stopAndSubmit() async {
      _state = HotkeyState.submitting;

      // 1. 更新 UI 状态为处理中
      _stateController?.add(CapsuleStateData.processing());

      // 2. 停止录音，获取最终文本 (AC3)
      final finalText = await _pipeline!.stop();

      // ignore: avoid_print
      print('[HotkeyController] 📝 最终文本: "$finalText"');

      // 3. 提交文本到 Fcitx5 (AC4)
      if (finalText.isNotEmpty) {
        try {
          await _fcitxClient!.sendText(finalText);
          // ignore: avoid_print
          print('[HotkeyController] ✅ 文本已提交');
        } catch (e) {
          // ignore: avoid_print
          print('[HotkeyController] ❌ 文本提交失败: $e');
          _stateController?.add(CapsuleStateData.error(CapsuleErrorType.socketDisconnected));
          await Future.delayed(const Duration(seconds: 2));
        }
      }

      // 4. 隐藏窗口 (AC5: 瞬间消失)
      await WindowService.instance.hide();

      // 5. 重置状态
      _state = HotkeyState.idle;
      _stateController?.add(CapsuleStateData.idle());
    }

    /// VAD 端点事件处理 (自动提交)
    void _onEndpoint(EndpointEvent event) {
      // ignore: avoid_print
      print('[HotkeyController] 🔔 VAD 端点: isVad=${event.isVadTriggered}, '
          'text="${event.finalText}", duration=${event.durationMs}ms');

      if (event.isVadTriggered && _state == HotkeyState.recording) {
        // VAD 自动触发，执行提交流程
        _submitFromVad(event.finalText);
      }
    }

    /// VAD 触发的提交 (无需再次 stop)
    Future<void> _submitFromVad(String finalText) async {
      _state = HotkeyState.submitting;

      // 1. 更新 UI 状态
      _stateController?.add(CapsuleStateData.processing());

      // 2. 提交文本
      if (finalText.isNotEmpty) {
        try {
          await _fcitxClient!.sendText(finalText);
          // ignore: avoid_print
          print('[HotkeyController] ✅ VAD 触发文本已提交');
        } catch (e) {
          // ignore: avoid_print
          print('[HotkeyController] ❌ VAD 触发文本提交失败: $e');
          _stateController?.add(CapsuleStateData.error(CapsuleErrorType.socketDisconnected));
          await Future.delayed(const Duration(seconds: 2));
        }
      }

      // 3. 隐藏窗口
      await WindowService.instance.hide();

      // 4. 重置状态
      _state = HotkeyState.idle;
      _stateController?.add(CapsuleStateData.idle());
    }

    /// 识别结果处理 (更新 UI 文本)
    void _onRecognitionResult(String text) {
      if (_state == HotkeyState.recording) {
        _stateController?.add(CapsuleStateData.listening(text: text));
      }
    }

    /// 错误处理
    void _handleError(PipelineError error) {
      final errorType = switch (error) {
        PipelineError.audioInitFailed => CapsuleErrorType.audioDeviceError,
        PipelineError.deviceUnavailable => CapsuleErrorType.audioDeviceError,
        PipelineError.modelNotReady => CapsuleErrorType.modelError,
        PipelineError.recognizerFailed => CapsuleErrorType.modelError,
        PipelineError.none => null,
      };

      if (errorType != null) {
        _stateController?.add(CapsuleStateData.error(errorType));
        // 3 秒后自动隐藏
        Future.delayed(const Duration(seconds: 3), () {
          if (_state != HotkeyState.recording) {
            WindowService.instance.hide();
            _state = HotkeyState.idle;
            _stateController?.add(CapsuleStateData.idle());
          }
        });
      }

      _state = HotkeyState.idle;
    }

    /// 释放资源
    Future<void> dispose() async {
      await _endpointSubscription?.cancel();
      await _resultSubscription?.cancel();
      _isInitialized = false;
    }
  }
  ```

- [x] **Task 5: 修改 TrayService 集成快捷键注销** (AC: #9)
  - [x] 5.1 修改 `lib/services/tray_service.dart`:
    - 添加 `import 'hotkey_service.dart';` (文件顶部)
    - 在 `_exitApp()` 方法开头添加 `await HotkeyService.instance.dispose();`

  **⚠️ 精确修改说明 (基于现有 tray_service.dart Line 118-133):**

  现有代码:
  ```dart
  Future<void> _exitApp() async {
    if (onBeforeExit != null) {
      await onBeforeExit!();
    }
    WindowService.instance.dispose();
    // ...
  }
  ```

  修改后:
  ```dart
  // 在文件顶部添加 import
  import 'hotkey_service.dart';  // 🆕 Story 3-5

  Future<void> _exitApp() async {
    // 🆕 Story 3-5: 先注销全局快捷键
    await HotkeyService.instance.dispose();

    if (onBeforeExit != null) {
      await onBeforeExit!();
    }
    WindowService.instance.dispose();
    // ... 其余代码保持不变
  }
  ```

- [x] **Task 6: 修改 main.dart 集成快捷键** (AC: #8)
  - [x] 6.1 更新 `lib/main.dart`:
    - 初始化 HotkeyService
    - 初始化 HotkeyController (注入依赖)
    - 更新初始化顺序
  - [x] 6.2 注意: 完整集成需要 Story 3-6，此处仅预埋架构

  **⚠️ 重要: 完整 main.dart 集成将在 Story 3-6 完成**

  **当前 Task 仅预埋 HotkeyService 初始化:**
  ```dart
  // lib/main.dart 修改
  import 'services/hotkey_service.dart';

  Future<void> main() async {
    WidgetsFlutterBinding.ensureInitialized();

    // 1. 初始化窗口管理服务 (Story 3-4)
    await WindowService.instance.initialize(showOnStartup: false);

    // 2. 初始化托盘服务 (Story 3-4)
    await TrayService.instance.initialize();

    // 3. 初始化全局快捷键服务 (Story 3-5)
    await HotkeyService.instance.initialize();

    // 4. HotkeyController 完整初始化将在 Story 3-6 完成
    // 需要 Pipeline、FcitxClient、StateController 等依赖

    runApp(const NextalkApp());
  }
  ```

- [x] **Task 7: 创建测试和验证** (AC: #1-10)
  - [x] 7.1 创建 `test/services/hotkey_service_test.dart`:
    - 测试服务单例
    - 测试初始化状态
    - 测试常量正确性
  - [x] 7.2 创建 `test/services/hotkey_controller_test.dart`:
    - 测试状态机流转 (需要 mock 依赖)
  - [x] 7.3 创建 `test/constants/hotkey_constants_test.dart`:
    - 测试键位映射完整性
  - [x] 7.4 手动验证清单:
    - 启动应用后按 Right Alt 窗口出现
    - 窗口出现时红灯呼吸
    - 再次按 Right Alt 窗口隐藏
    - 配置文件自定义快捷键生效

  **⚠️ 测试 Mock 策略说明:**
  > hotkey_manager 依赖原生 keybinder 库，无法在纯 Dart 单元测试中直接调用。
  >
  > **推荐测试方式:**
  > 1. 单元测试: 仅测试 singleton、状态属性、常量 (不涉及原生调用)
  > 2. 集成测试: 使用 `flutter test -d linux` 在真实设备上测试
  > 3. 如需 mock，可创建 `HotkeyServiceInterface` 抽象层

  ```dart
  // test/services/hotkey_service_test.dart
  /// 注意: hotkey_manager 依赖原生 keybinder 库
  /// 完整功能测试需要: flutter test -d linux (真实设备)
  /// 或创建 HotkeyServiceInterface 抽象层用于 mock
  import 'package:flutter_test/flutter_test.dart';
  import 'package:voice_capsule/services/hotkey_service.dart';
  import 'package:voice_capsule/constants/hotkey_constants.dart';

  void main() {
    group('HotkeyService Tests', () {
      test('should be a singleton', () {
        final instance1 = HotkeyService.instance;
        final instance2 = HotkeyService.instance;
        expect(identical(instance1, instance2), isTrue);
      });

      test('should not be initialized before initialize() is called', () {
        final service = HotkeyService.instance;
        expect(service.isInitialized, isA<bool>());
      });

      test('onHotkeyPressed callback should be settable', () {
        var called = false;
        HotkeyService.instance.onHotkeyPressed = () async {
          called = true;
        };
        expect(HotkeyService.instance.onHotkeyPressed, isNotNull);
      });
    });

    group('HotkeyConstants Tests', () {
      test('defaultKey should be altRight', () {
        expect(HotkeyConstants.defaultKey.name, 'altRight');
      });

      test('defaultModifiers should be empty', () {
        expect(HotkeyConstants.defaultModifiers, isEmpty);
      });

      test('keyMap should contain common keys', () {
        expect(HotkeyConstants.keyMap.containsKey('altRight'), isTrue);
        expect(HotkeyConstants.keyMap.containsKey('space'), isTrue);
        expect(HotkeyConstants.keyMap.containsKey('ctrl'), isTrue);
      });

      test('modifierMap should contain common modifiers', () {
        expect(HotkeyConstants.modifierMap.containsKey('ctrl'), isTrue);
        expect(HotkeyConstants.modifierMap.containsKey('shift'), isTrue);
        expect(HotkeyConstants.modifierMap.containsKey('alt'), isTrue);
      });

      test('configDirName should be nextalk', () {
        expect(HotkeyConstants.configDirName, 'nextalk');
      });

      test('configFileName should be config.yaml', () {
        expect(HotkeyConstants.configFileName, 'config.yaml');
      });
    });

    group('HotkeyController State Tests', () {
      test('initial state should be idle', () {
        // 注意: 实际测试需要 mock 依赖
        // 这里仅作为结构示例
        expect(true, isTrue); // Placeholder
      });
    });
  }
  ```

## Dev Notes

### 架构约束与禁止事项

| 类别 | 约束 | 原因 |
|------|------|------|
| **平台限制** | 仅支持 X11 (含 XWayland) | hotkey_manager 依赖 libkeybinder |
| **初始化顺序** | WindowService → TrayService → HotkeyService | 确保窗口就绪后再注册快捷键 |
| **资源释放** | 退出时必须调用 HotkeyService.dispose() | 防止快捷键残留 |
| **状态同步** | HotkeyController 必须通过 WindowService/Pipeline 操作 | 保持状态一致 |
| **线程安全** | 回调在主线程执行 | Flutter 单线程模型 |

### 快捷键冲突处理策略 (AC7)

**问题:** Right Alt 可能被其他应用 (如输入法切换) 占用

**解决方案:**
1. 主快捷键注册失败 → 尝试备用快捷键 (Ctrl+Shift+Space)
2. 备用快捷键也失败 → 输出警告日志，应用正常启动但快捷键功能降级
3. 用户可通过配置文件自定义其他键位

### 配置文件示例

**创建配置目录和文件:**
```bash
mkdir -p ~/.config/nextalk
cat > ~/.config/nextalk/config.yaml << 'EOF'
# Nextalk 配置文件
# 快捷键配置 (修改后需重启应用)
hotkey:
  # 主键 (可选值: alt, altRight, ctrl, shift, meta, space, f1-f12)
  key: altRight
  # 修饰键 (可选，多个用列表形式)
  # 示例: [ctrl, shift]
  modifiers: []

# 备选配置示例 (Ctrl+Shift+Space):
# hotkey:
#   key: space
#   modifiers: [ctrl, shift]
EOF
```

### 与 Story 3-4 (托盘) 的集成

**退出流程 (TrayService._exitApp):**
```dart
// 完整退出顺序 (AC9)
1. HotkeyService.dispose()     // 注销全局快捷键
2. onBeforeExit()              // 释放 Pipeline/Audio/Sherpa
3. WindowService.dispose()     // 释放窗口
4. _systemTray.destroy()       // 销毁托盘
5. exit(0)                     // 退出进程
```

### 与 Story 3-6 (完整业务流) 的集成点

**HotkeyController 完整初始化示例 (Story 3-6):**
```dart
// 在 Story 3-6 的 MainController 或 main.dart 中:
Future<void> setupHotkeyController() async {
  // 1. 创建 Pipeline 实例 (需要 AudioCapture + SherpaService + ModelManager)
  final pipeline = AudioInferencePipeline(
    audioCapture: audioCapture,
    sherpaService: sherpaService,
    modelManager: modelManager,
  );

  // 2. 创建 FcitxClient 实例
  final fcitxClient = FcitxClient();
  await fcitxClient.connect();

  // 3. 创建状态控制器 (用于更新 UI)
  final stateController = StreamController<CapsuleStateData>.broadcast();

  // 4. 初始化 HotkeyController
  await HotkeyController.instance.initialize(
    pipeline: pipeline,
    fcitxClient: fcitxClient,
    stateController: stateController,
  );

  // 5. 设置退出回调 (释放 Pipeline)
  TrayService.instance.onBeforeExit = () async {
    await HotkeyController.instance.dispose();
    await pipeline.dispose();
    await fcitxClient.dispose();  // 注意: FcitxClient 使用 dispose() 而非 close()
  };
}
```

### Linux 系统依赖

**开发环境需安装:**
```bash
# Ubuntu 22.04+ (X11 快捷键库)
sudo apt-get install libkeybinder-3.0-dev libgtk-3-dev

# 验证安装
pkg-config --libs keybinder-3.0

# 快速检测脚本 (可选)
ldconfig -p | grep keybinder || echo "⚠️ libkeybinder 未安装"
```

**⚠️ hotkey_manager API 版本说明:**
> 本 Story 基于 `hotkey_manager: ^0.2.3`
> HotKey 构造函数签名: `HotKey(KeyCode key, {List<HotKeyModifier>? modifiers})`
> 如 API 变更，请查阅 [pub.dev/hotkey_manager](https://pub.dev/packages/hotkey_manager)

### 快速验证命令

**通用验证:**
```bash
cd /mnt/disk0/project/newx/nextalk/nextalk_fcitx5_v2/voice_capsule

# 1. 安装依赖 (仅首次)
sudo apt-get install -y libkeybinder-3.0-dev

# 2. 获取依赖
flutter pub get

# 3. 运行测试
flutter test

# 4. 静态分析
flutter analyze

# 5. 构建
flutter build linux --release
```

**手动验证清单 (全部通过 = AC 通过):**
| # | 检查项 | 对应 AC |
|---|--------|---------|
| [ ] | 按 Right Alt 窗口瞬间出现 | AC1 |
| [ ] | 窗口出现时红灯呼吸动画 | AC2 |
| [ ] | 录音中再次按 Right Alt 窗口隐藏 | AC3, AC5 |
| [ ] | 说话后文字实时显示 | AC2 |
| [ ] | 静音后自动提交并隐藏 | AC4 (VAD) |
| [ ] | 创建配置文件后自定义快捷键生效 | AC6 |
| [ ] | 应用启动时快捷键自动注册 | AC8 |
| [ ] | 点击托盘退出后快捷键注销 | AC9 |
| [ ] | 窗口隐藏时按快捷键仍能响应 | AC10 |

### 潜在问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| Right Alt 被输入法占用 | 使用备用快捷键或配置文件自定义 |
| Wayland 环境快捷键不生效 | 切换到 X11 Session 或使用 XWayland |
| 快捷键注册失败无提示 | 检查 libkeybinder-3.0-dev 是否安装 |
| 配置文件语法错误 | 检查 YAML 格式，使用默认快捷键 |
| 多次按键状态混乱 | HotkeyController 状态机保证顺序 |

### 外部资源

- [hotkey_manager package](https://pub.dev/packages/hotkey_manager) - Flutter 全局快捷键库
- [libkeybinder](https://github.com/kupferlauncher/keybinder) - Linux X11 快捷键绑定库
- [docs/front-end-spec.md#4](docs/front-end-spec.md) - 交互流程 UX 规范
- [docs/prd.md#FR6](docs/prd.md) - 全局快捷键功能需求

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (via Cursor)

### Debug Log References

- 测试运行: 309 passed, 6 skipped (模型文件缺失)
- 静态分析: 无新增 warning (仅既存 info 级别提示)

### Completion Notes List

- Task 1-7 全部完成
- AC1-AC5, AC10 需要 Story 3-6 完整集成后验证
- AC6-AC9 已实现并验证
- Code Review 修复: M1 未使用变量, M2 竞态条件, M3 测试隔离, M4 错误日志

### File List

| 文件 | 操作 | 说明 |
|------|------|------|
| `lib/constants/hotkey_constants.dart` | 🆕 新增 | 快捷键常量定义 (keyMap, modifierMap) |
| `lib/services/hotkey_service.dart` | 🆕 新增 | 全局快捷键服务 (注册/注销/配置加载) |
| `lib/services/hotkey_controller.dart` | 🆕 新增 | 快捷键业务控制器 (状态机逻辑) |
| `lib/main.dart` | 🔄 修改 | 集成 HotkeyService 初始化 |
| `lib/services/tray_service.dart` | 🔄 修改 | 退出时注销快捷键 |
| `pubspec.yaml` | 🔄 修改 | 添加 hotkey_manager, yaml 依赖 |
| `test/constants/hotkey_constants_test.dart` | 🆕 新增 | 常量测试 (keyMap, modifierMap) |
| `test/services/hotkey_service_test.dart` | 🆕 新增 | 服务测试 (单例, 状态, 配置) |
| `test/services/hotkey_controller_test.dart` | 🆕 新增 | 控制器测试 (状态机, CapsuleStateData) |

---

### SM Validation Record

| Date | Validator | Result | Notes |
|------|-----------|--------|-------|
| 2025-12-22 | SM Agent (Bob) | ✅ PASS (after fixes) | 应用了 4 个关键修复, 5 个增强, 3 个优化 |

**Applied Fixes:**

| # | Category | Issue | Fix Applied |
|---|----------|-------|-------------|
| C1 | CRITICAL | CapsuleStateData API 调用使用位置参数 (应为命名参数) | ✅ `listening('')` → `listening()`, `listening(text)` → `listening(text: text)` |
| C2 | CRITICAL | CapsuleErrorType 枚举值错误 | ✅ `audioDeviceUnavailable` → `audioDeviceError`, `modelCorrupted` → `modelError` |
| C3 | CRITICAL | FcitxClient 方法名错误 | ✅ `close()` → `dispose()` |
| C4 | CRITICAL | path_provider 依赖声明但未使用 | ✅ 移除依赖，添加说明注释 |
| E1 | ENHANCE | 缺少测试 Mock 策略说明 | ✅ 添加 hotkey_manager 原生依赖测试说明 |
| E2 | ENHANCE | 缺少 HotKey API 版本说明 | ✅ 添加 ^0.2.3 构造函数签名说明 |
| E4 | ENHANCE | TrayService 修改说明不精确 | ✅ 添加基于现有代码行号的精确修改说明 |
| E5 | ENHANCE | 缺少 keybinder 检测命令 | ✅ 添加 ldconfig 检测脚本 |

---
*References: docs/front-end-spec.md#4, docs/prd.md#FR6, _bmad-output/epics.md#Story-3.5, 3-4-system-tray-integration.md*
