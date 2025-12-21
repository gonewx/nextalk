# Story 1.3: Dart Socket Client 实现

Status: ready-for-dev

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

> **并行提示**: Task 1-2 (目录创建+协议实现) 可顺序执行；Task 3 (错误处理) 可与 Task 4 (测试) 并行准备

- [ ] **Task 0: 前置条件验证** (Prerequisites)
  - [ ] 0.1 验证 Flutter 项目存在: `test -d voice_capsule/lib`
  - [ ] 0.2 若不存在，执行 Story 1.4 或手动创建 Flutter 项目
  - [ ] 0.3 验证 Story 1-1, 1-2 已完成: `test -x scripts/install_addon.sh`
  - **失败处理**: 若前置条件不满足，停止并报告依赖问题

- [ ] **Task 1: 创建服务文件** (AC: #1)
  - [ ] 1.1 创建 `voice_capsule/lib/services/` 目录 (若不存在)
  - [ ] 1.2 创建 `fcitx_client.dart` 文件
  - [ ] 1.3 实现 `FcitxClient` 类基础结构
  - [ ] 1.4 添加 Socket 路径常量和 MAX_MESSAGE_SIZE 常量
  - **验证**: 文件存在且无语法错误

- [ ] **Task 2: 实现 Socket 连接** (AC: #1, #2)
  - [ ] 2.1 实现 `connect()` 方法 - 使用 `Socket.connect` 连接 Unix Socket
  - [ ] 2.2 实现连接超时 (5 秒)
  - [ ] 2.3 实现 `sendText(String text)` 方法
  - [ ] 2.4 实现协议编码：[4字节长度 LE] + [UTF-8 文本]
  - [ ] 2.5 添加消息大小验证 (不超过 MAX_MESSAGE_SIZE)
  - [ ] 2.6 使用 `ByteData` 写入小端序 uint32
  - **验证**: `dart analyze` 无错误

- [ ] **Task 3: 实现错误处理** (AC: #3, #4)
  - [ ] 3.1 定义 `FcitxConnectionState` 枚举: `disconnected`, `connecting`, `connected`, `error`
  - [ ] 3.2 定义 `FcitxError` 枚举: `socketNotFound`, `connectionFailed`, `sendFailed`, `timeout`, `messageTooLarge`, `reconnectFailed`
  - [ ] 3.3 实现 `_reconnect()` 方法 (最多 3 次，间隔 1 秒)
  - [ ] 3.4 实现降级模式: 重连失败后设置 `_inDegradedMode = true`
  - [ ] 3.5 使用 `Stream<FcitxConnectionState>` 暴露连接状态供 UI 订阅
  - **验证**: 移除 Socket 文件后调用应返回 `FcitxError.socketNotFound`

- [ ] **Task 4: 实现资源管理** (AC: #5)
  - [ ] 4.1 实现 `dispose()` 方法关闭 Socket
  - [ ] 4.2 确保 StreamController 正确关闭
  - [ ] 4.3 处理并发调用 (使用 `Completer` 或 `synchronized`)
  - **验证**: 多次调用 `dispose()` 不报错

- [ ] **Task 5: 单元测试** (AC: 全部)
  - [ ] 5.1 创建 `test/services/fcitx_client_test.dart`
  - [ ] 5.2 创建 `test/helpers/mock_fcitx_server.dart` (Mock Socket Server)
  - [ ] 5.3 测试成功连接场景 (使用 Mock Server)
  - [ ] 5.4 测试 Socket 不存在场景
  - [ ] 5.5 测试协议编码正确性 (验证字节序列)
  - [ ] 5.6 测试消息大小超限场景
  - [ ] 5.7 测试 dispose 多次调用
  - [ ] 5.8 测试重连逻辑 (模拟断开)
  - **验证**: `flutter test` 全部通过

- [ ] **Task 6: 端到端验证** (AC: #2)
  - [ ] 6.1 验证前置 Story 完成: `test -x scripts/install_addon.sh && ls addons/fcitx5/build/nextalk.so`
  - [ ] 6.2 安装插件: `./scripts/install_addon.sh --user && fcitx5 -r`
  - [ ] 6.3 验证 Socket 就绪: `ls -la $XDG_RUNTIME_DIR/nextalk-fcitx5.sock`
  - [ ] 6.4 编写简单的测试脚本调用 `FcitxClient.sendText("测试文本")`
  - [ ] 6.5 验证文本出现在文本编辑器中
  - **预期**: gedit/kate 等编辑器输入框应显示 "测试文本"

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

**协议编码实现**:
```dart
/// 编码消息为 IPC 协议格式
/// 抛出 FcitxError.messageTooLarge 如果消息超过 1MB
Uint8List encodeMessage(String text) {
  final textBytes = utf8.encode(text);

  // 服务端限制检查
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
```

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
}

class FcitxClient {
  Socket? _socket;
  final _stateController = StreamController<FcitxConnectionState>.broadcast();
  FcitxConnectionState _state = FcitxConnectionState.disconnected;
  bool _inDegradedMode = false;

  static const _connectTimeout = Duration(seconds: 5);
  static const _maxRetries = 3;
  static const _retryDelay = Duration(seconds: 1);

  Stream<FcitxConnectionState> get stateStream => _stateController.stream;
  FcitxConnectionState get state => _state;

  String get _socketPath {
    final xdgRuntimeDir = Platform.environment['XDG_RUNTIME_DIR'];
    if (xdgRuntimeDir == null) throw FcitxError.socketNotFound;
    return '$xdgRuntimeDir/nextalk-fcitx5.sock';
  }

  Future<void> connect() async {
    _setState(FcitxConnectionState.connecting);
    try {
      _socket = await Socket.connect(
        InternetAddress(_socketPath, type: InternetAddressType.unix),
        0,
      ).timeout(_connectTimeout);
      _inDegradedMode = false;
      _setState(FcitxConnectionState.connected);
    } on TimeoutException {
      _setState(FcitxConnectionState.error);
      throw FcitxError.connectionTimeout;
    } catch (e) {
      _setState(FcitxConnectionState.error);
      throw FcitxError.connectionFailed;
    }
  }

  Future<void> sendText(String text) async {
    if (_state != FcitxConnectionState.connected) {
      await _reconnectWithRetry();
    }

    final message = _encodeMessage(text);
    try {
      _socket!.add(message);
      await _socket!.flush();
    } catch (e) {
      _setState(FcitxConnectionState.error);
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

  void _setState(FcitxConnectionState newState) {
    _state = newState;
    _stateController.add(newState);
  }

  Future<void> dispose() async {
    await _socket?.close();
    _socket = null;
    await _stateController.close();
    _setState(FcitxConnectionState.disconnected);
  }
}
```

### Mock Socket Server (测试用)

```dart
// test/helpers/mock_fcitx_server.dart
import 'dart:io';
import 'dart:typed_data';

class MockFcitxServer {
  ServerSocket? _server;
  final List<Uint8List> receivedMessages = [];
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
      });
    });
  }

  Future<void> stop() async {
    await _server?.close();
    final file = File(socketPath);
    if (await file.exists()) await file.delete();
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

(待开发时填写)

### Debug Log References

### Completion Notes List

### Change Log

- 2025-12-21: Story Review - 添加依赖检查、MAX_MESSAGE_SIZE 约束、Mock 测试策略、重连降级模式

### File List

---
*References: docs/architecture.md#4.1, docs/architecture.md#2.2, docs/prd.md#FR4, _bmad-output/epics.md#Story-1.3, _bmad-output/implementation-artifacts/1-1-fcitx5-plugin-integration.md, _bmad-output/implementation-artifacts/1-2-plugin-install-script.md*
