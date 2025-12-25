import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

/// 命令服务器 - 接收来自 Fcitx5 插件的命令
///
/// 功能：
/// - 监听 Unix Socket ($XDG_RUNTIME_DIR/nextalk-cmd.sock)
/// - 接收 Fcitx5 插件发送的快捷键触发命令
/// - 通知 Flutter 应用显示/隐藏窗口
///
/// 协议：
/// - 4 字节长度 (小端) + UTF-8 命令文本
/// - 支持命令: "toggle", "show", "hide"
class CommandServer {
  CommandServer._();
  static final CommandServer instance = CommandServer._();

  ServerSocket? _serverSocket;
  bool _isRunning = false;
  final List<Socket> _clients = [];

  /// 命令回调
  void Function(String command)? onCommand;

  /// 是否正在运行
  bool get isRunning => _isRunning;

  /// 获取 Socket 路径
  String get socketPath {
    final runtimeDir = Platform.environment['XDG_RUNTIME_DIR'];
    if (runtimeDir != null && runtimeDir.isNotEmpty) {
      return '$runtimeDir/nextalk-cmd.sock';
    }
    return '/tmp/nextalk-cmd.sock';
  }

  /// 启动服务器
  Future<void> start() async {
    if (_isRunning) {
      // ignore: avoid_print
      print('[CommandServer] Already running');
      return;
    }

    try {
      // 删除旧的 socket 文件
      final socketFile = File(socketPath);
      if (await socketFile.exists()) {
        await socketFile.delete();
      }

      // 创建 Unix Domain Socket 服务器
      final address = InternetAddress(socketPath, type: InternetAddressType.unix);
      _serverSocket = await ServerSocket.bind(address, 0);
      _isRunning = true;

      // ignore: avoid_print
      print('[CommandServer] ✅ 服务器启动成功: $socketPath');

      // 监听连接
      _serverSocket!.listen(
        _handleConnection,
        onError: (error) {
          // ignore: avoid_print
          print('[CommandServer] 服务器错误: $error');
        },
        onDone: () {
          // ignore: avoid_print
          print('[CommandServer] 服务器关闭');
          _isRunning = false;
        },
      );
    } catch (e) {
      // ignore: avoid_print
      print('[CommandServer] ❌ 启动失败: $e');
      _isRunning = false;
    }
  }

  /// 停止服务器
  Future<void> stop() async {
    if (!_isRunning) return;

    // 关闭所有客户端连接
    for (final client in _clients) {
      try {
        await client.close();
      } catch (_) {}
    }
    _clients.clear();

    // 关闭服务器
    await _serverSocket?.close();
    _serverSocket = null;
    _isRunning = false;

    // 删除 socket 文件
    try {
      final socketFile = File(socketPath);
      if (await socketFile.exists()) {
        await socketFile.delete();
      }
    } catch (_) {}

    // ignore: avoid_print
    print('[CommandServer] 服务器已停止');
  }

  /// 处理客户端连接
  void _handleConnection(Socket client) {
    _clients.add(client);
    // ignore: avoid_print
    print('[CommandServer] 客户端连接: ${client.remoteAddress}');

    final buffer = BytesBuilder();

    client.listen(
      (data) {
        buffer.add(data);
        _processBuffer(buffer, client);
      },
      onError: (error) {
        // ignore: avoid_print
        print('[CommandServer] 客户端错误: $error');
        _clients.remove(client);
      },
      onDone: () {
        // ignore: avoid_print
        print('[CommandServer] 客户端断开');
        _clients.remove(client);
      },
    );
  }

  /// 处理接收缓冲区
  void _processBuffer(BytesBuilder buffer, Socket client) {
    while (true) {
      final data = buffer.toBytes();

      // 需要至少 4 字节长度
      if (data.length < 4) break;

      // 读取长度 (小端)
      final lenBytes = ByteData.sublistView(Uint8List.fromList(data.sublist(0, 4)));
      final len = lenBytes.getUint32(0, Endian.little);

      // 检查是否有完整消息
      if (data.length < 4 + len) break;

      // 提取命令
      final commandBytes = data.sublist(4, 4 + len);
      final command = String.fromCharCodes(commandBytes);

      // ignore: avoid_print
      print('[CommandServer] 收到命令: $command');

      // 触发回调
      if (onCommand != null) {
        onCommand!(command);
      }

      // 清除已处理的数据
      buffer.clear();
      if (data.length > 4 + len) {
        buffer.add(data.sublist(4 + len));
      }
    }
  }

  /// 释放资源
  Future<void> dispose() async {
    await stop();
    onCommand = null;
  }
}
