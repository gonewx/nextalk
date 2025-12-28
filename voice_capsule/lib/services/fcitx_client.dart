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
        return '输入法插件未运行或未加载';
      case FcitxError.connectionFailed:
        return '连接被拒绝';
      case FcitxError.connectionTimeout:
        return '连接超时';
      case FcitxError.sendFailed:
        return '发送失败';
      case FcitxError.messageTooLarge:
        return '消息过大 (超过 1MB)';
      case FcitxError.reconnectFailed:
        return '重连失败，请检查输入法状态';
      case FcitxError.socketPermissionInsecure:
        return 'Socket 权限不安全';
    }
  }
}

/// FcitxClient - SCP-002 简化版
///
/// 职责：
/// - 通过 Unix Socket 发送文本到 Fcitx5 插件
/// - 连接管理和错误处理
///
/// SCP-002 变更：
/// - 移除对 InputMethodDetector 的依赖
/// - 只支持 Fcitx5（非 Fcitx5 环境由调用方处理剪贴板 fallback）
class FcitxClient {
  Socket? _socket;
  StreamSubscription? _socketSubscription;
  final _stateController = StreamController<FcitxConnectionState>.broadcast();
  FcitxConnectionState _state = FcitxConnectionState.disconnected;
  bool _inDegradedMode = false;
  bool _isDisposed = false;

  /// 剪贴板模式标志：当 Fcitx5 不可用时为 true
  /// UI 层可以通过此属性判断是否需要显示剪贴板提示
  bool _isClipboardMode = false;

  /// 是否处于剪贴板模式（Fcitx5 不可用）
  bool get isClipboardMode => _isClipboardMode;

  // 并发控制: 防止同时执行 connect/sendText/dispose
  Completer<void>? _connectCompleter;

  // 操作锁: 防止并发 sendText 同时触发重连
  Future<void>? _sendLock;

  // 自定义 socket 路径 (用于测试)
  final String? _customSocketPath;

  static const _connectTimeout = Duration(seconds: 5);
  static const _maxRetries = 3;
  static const _retryDelay = Duration(seconds: 1);

  /// 创建 FcitxClient 实例
  /// [socketPath] 可选的自定义 socket 路径，用于测试
  FcitxClient({String? socketPath}) : _customSocketPath = socketPath;

  Stream<FcitxConnectionState> get stateStream => _stateController.stream;
  FcitxConnectionState get state => _state;
  bool get isInDegradedMode => _inDegradedMode;

  /// 获取 Socket 路径
  /// SCP-002: 简化为只支持 Fcitx5
  String get _socketPath {
    final customPath = _customSocketPath;
    if (customPath != null) return customPath;

    final runtimeDir = Platform.environment['XDG_RUNTIME_DIR'];
    if (runtimeDir != null && runtimeDir.isNotEmpty) {
      return '$runtimeDir/nextalk-fcitx5.sock';
    }
    return '/tmp/nextalk-fcitx5.sock';
  }

  /// 检查 Fcitx5 插件是否可用
  Future<bool> isAvailable() async {
    try {
      final socketFile = File(_socketPath);
      return await socketFile.exists();
    } catch (e) {
      return false;
    }
  }

  /// 检查并更新剪贴板模式状态
  /// 在应用启动时调用，确定是否需要使用剪贴板 fallback
  Future<void> checkClipboardMode() async {
    _isClipboardMode = !(await isAvailable());
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
      // [FIX-M1] 权限验证是可选功能，调用方可通过 verifySocketPermissions() 手动检查
      // 不在 connect() 中自动验证，避免无意义的调用

      _socket = await Socket.connect(
        InternetAddress(_socketPath, type: InternetAddressType.unix),
        0,
      ).timeout(_connectTimeout);

      // 监听 socket 断开事件 (连接断开检测)
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
      _connectCompleter = null; // 重置 Completer，允许下次重试
      throw FcitxError.connectionTimeout;
    } catch (e) {
      _setState(FcitxConnectionState.error);
      _connectCompleter = null; // 重置 Completer，允许下次重试
      if (e is FcitxError) {
        rethrow;
      }
      throw FcitxError.connectionFailed;
    }
  }

  // [FIX-M4] 提取清理逻辑到单独方法，支持同步回调和异步 dispose
  void _handleSocketClosed() {
    if (_isDisposed) return;
    _socket = null;
    // 在回调上下文中不 await，但订阅会被后续 dispose 清理
    _socketSubscription?.cancel();
    _socketSubscription = null;
    _setState(FcitxConnectionState.disconnected);
  }

  Future<void> sendText(String text) async {
    if (_isDisposed) throw StateError('FcitxClient has been disposed');

    // [FIX-H1] 使用互斥锁确保串行执行
    while (_sendLock != null) {
      await _sendLock;
    }

    final completer = Completer<void>();
    _sendLock = completer.future;

    try {
      if (_state != FcitxConnectionState.connected) {
        await _reconnectWithRetry();
      }

      // [FIX-H2] 在使用前检查 socket 是否有效，避免竞态条件下的空指针
      final socket = _socket;
      if (socket == null) {
        throw FcitxError.sendFailed;
      }

      final message = _encodeMessage(text);
      socket.add(message);
      await socket.flush();
    } catch (e) {
      if (e is FcitxError) {
        rethrow;
      }
      _handleSocketClosed();
      throw FcitxError.sendFailed;
    } finally {
      _sendLock = null;
      completer.complete();
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
    // 降级模式生效 - 不再自动重连
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
    if (_isDisposed) return; // 防止向已关闭的 controller 发送事件
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
