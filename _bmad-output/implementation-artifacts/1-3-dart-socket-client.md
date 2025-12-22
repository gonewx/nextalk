# Story 1.3: Dart Socket Client 实现

Status: done

## Prerequisites

> **CRITICAL**: 本 Story 依赖 Flutter 项目结构。执行前请确认:
> - [ ] Story 1.4 (Flutter 项目初始化) 已完成，或
> - [ ] `voice_capsule/` 目录已存在且包含有效的 Flutter 项目
>
> 若 Flutter 项目不存在，请先执行 Story 1.4 或手动创建:
> ```bash
> cd /mnt/disk0/project/newx/nextalk/nextalk_fcitx5_v2
> flutter create voice_capsule --platforms=linux
> mkdir -p voice_capsule/lib/services
> ```

## Story

As a Flutter 客户端,
I want 能够通过 Unix Domain Socket 与 Fcitx5 插件通信,
So that 可以将识别出的文本注入到任何应用程序的输入框中。

## Acceptance Criteria

1. **AC1: Socket 连接**
   - **Given** Fcitx5 插件已安装并运行，Socket 文件存在于 `$XDG_RUNTIME_DIR/nextalk-fcitx5.sock`
   - **When** Dart 客户端初始化
   - **Then** 能够成功连接到 Socket 文件
   - **And** 连接超时合理 (5 秒)
   - **And** 可选: 验证 Socket 文件权限为 0600 (安全检查)

2. **AC2: 文本发送协议**
   - **Given** Socket 连接已建立
   - **When** Dart 客户端调用 `sendText("Hello World")`
   - **Then** 客户端按协议格式发送数据 (详见 Dev Notes - IPC 协议)
   - **And** 消息大小不超过 1MB (服务端限制)
   - **And** 文本成功出现在当前活动窗口的输入框中

3. **AC3: 连接失败处理**
   - **Given** Socket 文件不存在或连接失败
   - **When** 尝试发送文本
   - **Then** 返回连接错误，不崩溃
   - **And** 提供可用于 UI 显示的错误状态 (枚举类型)

4. **AC4: 断开重连**
   - **Given** Socket 连接意外断开
   - **When** 尝试发送文本
   - **Then** 自动尝试重新连接 (最多 3 次，间隔 1 秒)
   - **And** 重连失败后返回 `FcitxError.reconnectFailed` 错误状态
   - **And** 进入 "降级模式": 不再自动重连，等待用户手动触发或下次 `sendText` 调用

5. **AC5: 资源清理**
   - **Given** 客户端使用完毕
   - **When** 调用 `dispose()` 或应用退出
   - **Then** Socket 连接正确关闭
   - **And** 无资源泄漏

## Tasks / Subtasks

> **执行顺序**: Task 0-4 按顺序执行；Task 5 (单元测试) 可在 Task 4 完成后独立进行；Task 6 (端到端验证) 需最后执行

- [x] **Task 0: 前置条件验证** (Prerequisites)
  - [x] 0.1 验证 Flutter 项目存在: `test -d voice_capsule/lib`
  - [x] 0.2 若不存在，执行 Story 1.4 或手动创建 Flutter 项目
  - [x] 0.3 验证 Story 1-1, 1-2 已完成: `test -x scripts/install_addon.sh`
  - **失败处理**: 若前置条件不满足，停止并报告依赖问题

- [x] **Task 1: 创建服务文件** (AC: #1)
  - [x] 1.1 创建 `voice_capsule/lib/services/` 目录 (若不存在)
  - [x] 1.2 创建 `fcitx_client.dart` 文件
  - [x] 1.3 实现 `FcitxClient` 类基础结构
  - [x] 1.4 添加 Socket 路径常量和 MAX_MESSAGE_SIZE 常量
  - **验证**: 文件存在且无语法错误

- [x] **Task 2: 实现 Socket 连接** (AC: #1, #2)
  - [x] 2.1 实现 `connect()` 方法 - 使用 `Socket.connect` 连接 Unix Socket
  - [x] 2.2 实现连接超时 (5 秒)
  - [x] 2.3 实现 `sendText(String text)` 方法
  - [x] 2.4 实现协议编码：[4字节长度 LE] + [UTF-8 文本]
  - [x] 2.5 添加消息大小验证 (不超过 MAX_MESSAGE_SIZE)
  - [x] 2.6 使用 `ByteData` 写入小端序 uint32
  - **验证**: `dart analyze` 无错误

- [x] **Task 3: 实现错误处理** (AC: #3, #4)
  - [x] 3.1 定义 `FcitxConnectionState` 枚举: `disconnected`, `connecting`, `connected`, `error`
  - [x] 3.2 定义 `FcitxError` 枚举: `socketNotFound`, `connectionFailed`, `sendFailed`, `timeout`, `messageTooLarge`, `reconnectFailed`
  - [x] 3.3 实现 `_reconnect()` 方法 (最多 3 次，间隔 1 秒)
  - [x] 3.4 实现降级模式: 重连失败后设置 `_inDegradedMode = true`
  - [x] 3.5 使用 `Stream<FcitxConnectionState>` 暴露连接状态供 UI 订阅
  - **验证**: 移除 Socket 文件后调用应返回 `FcitxError.socketNotFound`

- [x] **Task 4: 实现资源管理** (AC: #5)
  - [x] 4.1 实现 `dispose()` 方法关闭 Socket
  - [x] 4.2 确保 StreamController 正确关闭
  - [x] 4.3 处理并发调用 (使用 `Completer` 或 `synchronized`)
  - **验证**: 多次调用 `dispose()` 不报错

- [x] **Task 5: 单元测试** (AC: 全部)
  - [x] 5.1 创建 `test/services/fcitx_client_test.dart`
  - [x] 5.2 创建 `test/helpers/mock_fcitx_server.dart` (Mock Socket Server)
  - [x] 5.3 测试成功连接场景 (使用 Mock Server)
  - [x] 5.4 测试 Socket 不存在场景
  - [x] 5.5 测试协议编码正确性 (验证字节序列)
  - [x] 5.6 测试消息大小超限场景
  - [x] 5.7 测试 dispose 多次调用
  - [x] 5.8 测试重连逻辑 (模拟断开)
  - **验证**: `flutter test` 全部通过 (21/21 tests)

- [x] **Task 6: 端到端验证** (AC: #2)
  - [x] 6.1 验证前置 Story 完成: `test -x scripts/install_addon.sh && ls addons/fcitx5/build/nextalk.so`
  - [x] 6.2 安装插件: `./scripts/install_addon.sh --user && fcitx5 -r`
  - [x] 6.3 验证 Socket 就绪: `ls -la $XDG_RUNTIME_DIR/nextalk-fcitx5.sock`
  - [x] 6.4 编写简单的测试脚本调用 `FcitxClient.sendText("测试文本")`
  - [x] 6.5 验证文本出现在文本编辑器中 (手动验证通过 2025-12-22)
  - **预期**: gedit/kate 等编辑器输入框应显示 "测试文本"
  - **注意**: E2E 测试脚本已创建 (`test/e2e/fcitx_e2e_test.dart`)，需在桌面环境手动运行验证

## Dev Notes

### 服务端约束 (来自 Story 1-1)

| 约束 | 值 | 说明 |
|------|-----|------|
| MAX_MESSAGE_SIZE | 1MB (1024 * 1024) | 服务端拒绝超过此大小的消息 |
| Socket 权限 | 0600 | 仅所有者可读写 (安全要求) |
| EINTR 处理 | 已实现 | 服务端 recv() 有中断重试 |

### IPC 协议详解

| Offset | Type | Size | Description |
|--------|------|------|-------------|
| 0 | uint32_le | 4 | Payload length (小端序) |
| 4 | bytes | N | UTF-8 encoded text |

**协议编码**: 见下方完整类实现中的 `_encodeMessage()` 方法。

### Socket 路径

```dart
String get socketPath {
  final xdgRuntimeDir = Platform.environment['XDG_RUNTIME_DIR'];
  if (xdgRuntimeDir == null) {
    throw FcitxError.socketNotFound;
  }
  return '$xdgRuntimeDir/nextalk-fcitx5.sock';
}
```

> **验证路径**: `/run/user/1000/nextalk-fcitx5.sock` (Story 1-1 确认)

### 完整类实现骨架

```dart
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

/// 服务端消息大小限制 (来自 Story 1-1)
const int maxMessageSize = 1024 * 1024; // 1MB

enum FcitxConnectionState {
  disconnected,
  connecting,
  connected,
  error,
}

enum FcitxError {
  socketNotFound,
  connectionFailed,
  connectionTimeout,
  sendFailed,
  messageTooLarge,
  reconnectFailed,
  socketPermissionInsecure,
}

/// FcitxError 人类可读消息扩展 (用于 UI 显示)
extension FcitxErrorExtension on FcitxError {
  String get localizedMessage {
    switch (this) {
      case FcitxError.socketNotFound:
        return 'Fcitx5 未运行或插件未加载';
      case FcitxError.connectionFailed:
        return '连接被拒绝';
      case FcitxError.connectionTimeout:
        return '连接超时';
      case FcitxError.sendFailed:
        return '发送失败';
      case FcitxError.messageTooLarge:
        return '消息过大 (超过 1MB)';
      case FcitxError.reconnectFailed:
        return '重连失败，请检查 Fcitx5 状态';
      case FcitxError.socketPermissionInsecure:
        return 'Socket 权限不安全';
    }
  }
}

class FcitxClient {
  Socket? _socket;
  StreamSubscription? _socketSubscription;
  final _stateController = StreamController<FcitxConnectionState>.broadcast();
  FcitxConnectionState _state = FcitxConnectionState.disconnected;
  bool _inDegradedMode = false;
  bool _isDisposed = false;

  // 并发控制: 防止同时执行 connect/sendText/dispose
  Completer<void>? _connectCompleter;
  final _operationLock = Completer<void>()..complete();

  static const _connectTimeout = Duration(seconds: 5);
  static const _maxRetries = 3;
  static const _retryDelay = Duration(seconds: 1);

  Stream<FcitxConnectionState> get stateStream => _stateController.stream;
  FcitxConnectionState get state => _state;
  bool get isInDegradedMode => _inDegradedMode;

  String get _socketPath {
    final xdgRuntimeDir = Platform.environment['XDG_RUNTIME_DIR'];
    if (xdgRuntimeDir == null) throw FcitxError.socketNotFound;
    return '$xdgRuntimeDir/nextalk-fcitx5.sock';
  }

  /// 验证 Socket 文件权限是否安全 (0600)
  Future<bool> verifySocketPermissions() async {
    try {
      final stat = await FileStat.stat(_socketPath);
      // 检查权限为 0600 (所有者读写，其他无权限)
      // stat.mode 包含文件类型位，需要 & 0777 提取权限位
      final permissions = stat.mode & 0x1FF; // 0777 octal = 0x1FF
      return permissions == 0x180; // 0600 octal = 0x180
    } catch (e) {
      return false;
    }
  }

  Future<void> connect() async {
    if (_isDisposed) throw StateError('FcitxClient has been disposed');

    // 如果已有连接正在进行，等待它完成
    if (_connectCompleter != null && !_connectCompleter!.isCompleted) {
      await _connectCompleter!.future;
      return;
    }

    _connectCompleter = Completer<void>();
    _setState(FcitxConnectionState.connecting);

    try {
      // 可选: 验证 Socket 权限 (安全检查)
      if (!await verifySocketPermissions()) {
        // 仅记录警告，不阻止连接 (因为 AC1 标记为可选)
        // 如需强制检查，取消下面的注释:
        // throw FcitxError.socketPermissionInsecure;
      }

      _socket = await Socket.connect(
        InternetAddress(_socketPath, type: InternetAddressType.unix),
        0,
      ).timeout(_connectTimeout);

      // 监听 socket 断开事件 (C2: 连接断开检测)
      _socketSubscription = _socket!.listen(
        (_) {}, // 服务端不发送数据，忽略
        onDone: _handleSocketClosed,
        onError: (e) => _handleSocketClosed(),
        cancelOnError: true,
      );

      _inDegradedMode = false;
      _setState(FcitxConnectionState.connected);
      _connectCompleter!.complete();
    } on TimeoutException {
      _setState(FcitxConnectionState.error);
      _connectCompleter!.completeError(FcitxError.connectionTimeout);
      throw FcitxError.connectionTimeout;
    } catch (e) {
      _setState(FcitxConnectionState.error);
      if (e is FcitxError) {
        _connectCompleter!.completeError(e);
        rethrow;
      }
      _connectCompleter!.completeError(FcitxError.connectionFailed);
      throw FcitxError.connectionFailed;
    }
  }

  void _handleSocketClosed() {
    if (_isDisposed) return;
    _socket = null;
    _socketSubscription?.cancel();
    _socketSubscription = null;
    _setState(FcitxConnectionState.disconnected);
  }

  Future<void> sendText(String text) async {
    if (_isDisposed) throw StateError('FcitxClient has been disposed');

    if (_state != FcitxConnectionState.connected) {
      await _reconnectWithRetry();
    }

    final message = _encodeMessage(text);
    try {
      _socket!.add(message);
      await _socket!.flush();
    } catch (e) {
      _handleSocketClosed();
      throw FcitxError.sendFailed;
    }
  }

  Uint8List _encodeMessage(String text) {
    final textBytes = utf8.encode(text);
    if (textBytes.length > maxMessageSize) {
      throw FcitxError.messageTooLarge;
    }

    final buffer = ByteData(4 + textBytes.length);
    buffer.setUint32(0, textBytes.length, Endian.little);

    final result = Uint8List(4 + textBytes.length);
    result.setRange(0, 4, buffer.buffer.asUint8List());
    result.setRange(4, 4 + textBytes.length, textBytes);
    return result;
  }

  Future<void> _reconnectWithRetry() async {
    // C3: 降级模式生效 - 不再自动重连
    if (_inDegradedMode) {
      throw FcitxError.reconnectFailed;
    }

    for (var i = 0; i < _maxRetries; i++) {
      try {
        await connect();
        return;
      } catch (e) {
        if (i < _maxRetries - 1) {
          await Future.delayed(_retryDelay);
        }
      }
    }
    _inDegradedMode = true;
    throw FcitxError.reconnectFailed;
  }

  /// 重置降级模式，允许下次 sendText 时重新尝试连接
  void resetDegradedMode() {
    _inDegradedMode = false;
  }

  void _setState(FcitxConnectionState newState) {
    if (_isDisposed) return; // C1: 防止向已关闭的 controller 发送事件
    _state = newState;
    _stateController.add(newState);
  }

  Future<void> dispose() async {
    if (_isDisposed) return; // 幂等性: 多次调用不报错
    _isDisposed = true;

    // 先更新状态 (在关闭 controller 之前)
    _state = FcitxConnectionState.disconnected;

    // 取消 socket 监听
    await _socketSubscription?.cancel();
    _socketSubscription = null;

    // 关闭 socket
    await _socket?.close();
    _socket = null;

    // 最后关闭 controller
    await _stateController.close();
  }
}
```

### Mock Socket Server (测试用)

```dart
// test/helpers/mock_fcitx_server.dart
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

class MockFcitxServer {
  ServerSocket? _server;
  final List<Uint8List> receivedMessages = [];
  final List<String> decodedTexts = []; // 解码后的文本 (用于验证)
  final String socketPath;

  MockFcitxServer({String? path})
    : socketPath = path ?? '/tmp/test-nextalk-${DateTime.now().millisecondsSinceEpoch}.sock';

  Future<void> start() async {
    // 清理旧 socket 文件
    final file = File(socketPath);
    if (await file.exists()) await file.delete();

    _server = await ServerSocket.bind(
      InternetAddress(socketPath, type: InternetAddressType.unix),
      0,
    );

    _server!.listen((client) {
      client.listen((data) {
        receivedMessages.add(Uint8List.fromList(data));
        // 解析协议并记录文本
        final decoded = _decodeMessage(Uint8List.fromList(data));
        if (decoded != null) {
          decodedTexts.add(decoded);
        }
      });
    });
  }

  /// 解码 IPC 协议消息
  /// 返回 null 表示协议格式错误
  String? _decodeMessage(Uint8List data) {
    if (data.length < 4) return null;

    final byteData = ByteData.sublistView(data);
    final length = byteData.getUint32(0, Endian.little);

    if (data.length < 4 + length) return null;

    try {
      return utf8.decode(data.sublist(4, 4 + length));
    } catch (e) {
      return null; // UTF-8 解码失败
    }
  }

  /// 获取最后一条解码的消息文本
  String? get lastDecodedText => decodedTexts.isNotEmpty ? decodedTexts.last : null;

  /// 验证最后一条消息是否与预期匹配
  bool verifyLastMessage(String expected) {
    return lastDecodedText == expected;
  }

  /// 验证协议格式是否正确 (用于测试协议编码)
  bool verifyProtocolFormat(Uint8List data) {
    if (data.length < 4) return false;
    final byteData = ByteData.sublistView(data);
    final declaredLength = byteData.getUint32(0, Endian.little);
    return data.length == 4 + declaredLength;
  }

  Future<void> stop() async {
    await _server?.close();
    final file = File(socketPath);
    if (await file.exists()) await file.delete();
  }

  void clear() {
    receivedMessages.clear();
    decodedTexts.clear();
  }
}
```

### 依赖项

本 Story 无需添加外部依赖，仅使用 Dart SDK 自带的:
- `dart:io` - Socket API
- `dart:convert` - UTF-8 编码
- `dart:typed_data` - ByteData
- `dart:async` - Stream, Completer

### 与前置 Story 的关系

| Story | 状态 | 依赖关系 |
|-------|------|----------|
| 1-1 Fcitx5 插件集成 | done | Socket 服务端已就绪，MAX_MESSAGE_SIZE=1MB |
| 1-2 插件安装脚本 | done | 可快速部署测试环境 |
| 1-4 Flutter 项目初始化 | **必需** | 提供 `voice_capsule/` 项目结构 |

### 架构约束

| 约束 | 要求 | 来源 |
|------|------|------|
| Socket 路径 | `$XDG_RUNTIME_DIR/nextalk-fcitx5.sock` | docs/architecture.md#4.1 |
| 协议格式 | [4字节长度 LE] + [UTF-8 文本] | docs/architecture.md#4.1 |
| 消息大小 | <= 1MB | Story 1-1 (MAX_MESSAGE_SIZE) |
| 目录结构 | `lib/services/fcitx_client.dart` | docs/architecture.md#2.2 |

### 测试前置条件

```bash
# 1. 验证前置 Story 完成
test -x scripts/install_addon.sh || echo "Story 1-2 未完成"
test -d voice_capsule/lib || echo "Story 1-4 未完成"

# 2. 安装插件
./scripts/install_addon.sh --user

# 3. 重启 Fcitx5
fcitx5 -r

# 4. 验证 Socket 存在 (预期: srw-------, 即权限 600)
ls -la $XDG_RUNTIME_DIR/nextalk-fcitx5.sock
```

### 故障排除

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| Socket 文件不存在 | Fcitx5 未运行或插件未加载 | `fcitx5 -r` 重启 |
| 连接被拒绝 | 权限问题或插件未启动 | 检查 socket 权限为 0600 |
| 文本未出现 | 无活动输入上下文 | 先点击输入框获取焦点 |
| 编码错误 | 字节序错误 | 确认使用 `Endian.little` |
| 消息被截断 | 超过 1MB 限制 | 检查消息大小，分段发送 |
| voice_capsule 不存在 | Story 1-4 未完成 | 先完成 Flutter 项目初始化 |

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- 修复 Dart 字段提升兼容性问题 (Dart < 3.2)
- 修复 Completer.completeError 后重复 throw 导致测试框架报未处理异常

### Completion Notes List

- **实现 FcitxClient 类**: 完整实现 Socket 连接、文本发送、错误处理、资源管理
- **协议编码**: 4字节小端序长度 + UTF-8 文本，符合 Story 1-1 服务端规范
- **错误处理**: 定义 FcitxError 枚举，提供 localizedMessage 扩展用于 UI 显示
- **重连机制**: 最多 3 次重试，间隔 1 秒，失败后进入降级模式
- **并发保护**: 使用 Completer 防止并发 connect() 调用
- **单元测试**: 18 个测试覆盖所有 AC，使用 MockFcitxServer 模拟服务端
- **E2E 测试脚本**: 创建 test/e2e/fcitx_e2e_test.dart 供桌面环境手动验证

### Change Log

- 2025-12-22: Code Review Fix - 修复 6 个问题: H1 并发安全(sendText 互斥锁)、H2 空指针风险(socket null检查)、M1 移除无意义权限验证调用、M2 添加 3 个测试(权限验证/并发安全)、M3 Mock Server TCP分包处理、M4 资源清理注释
- 2025-12-22: Story Implementation - 完成 FcitxClient 实现，18 个单元测试全部通过，创建 E2E 测试脚本
- 2025-12-22: Story Validation - 修复 dispose() bug、添加连接断开检测、降级模式生效、并发保护、Socket权限验证、错误消息扩展、Mock协议验证
- 2025-12-21: Story Review - 添加依赖检查、MAX_MESSAGE_SIZE 约束、Mock 测试策略、重连降级模式

### File List

**新增文件:**
- voice_capsule/lib/services/fcitx_client.dart - FcitxClient 主实现
- voice_capsule/test/services/fcitx_client_test.dart - 单元测试 (21 tests)
- voice_capsule/test/helpers/mock_fcitx_server.dart - Mock Socket 服务器 (含 TCP 分包处理)
- voice_capsule/test/e2e/fcitx_e2e_test.dart - 端到端测试脚本

---
*References: docs/architecture.md#4.1, docs/architecture.md#2.2, docs/prd.md#FR4, _bmad-output/epics.md#Story-1.3, _bmad-output/implementation-artifacts/1-1-fcitx5-plugin-integration.md, _bmad-output/implementation-artifacts/1-2-plugin-install-script.md*
