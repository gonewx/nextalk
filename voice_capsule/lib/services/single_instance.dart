import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

/// 单实例管理器
/// SCP-002: 支持 --toggle 命令行参数
///
/// 功能：
/// - 确保应用只有一个实例运行
/// - 支持向已运行实例发送命令 (toggle, show, hide)
/// - 通过 Unix Socket 实现 IPC
class SingleInstance {
  SingleInstance._();
  static final SingleInstance instance = SingleInstance._();

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
      return '$runtimeDir/nextalk.sock';
    }
    return '/tmp/nextalk.sock';
  }

  /// 尝试成为主实例
  ///
  /// 返回 true 表示成功成为主实例，false 表示已有实例运行
  Future<bool> tryBecomeMainInstance() async {
    try {
      // 尝试删除旧的 socket 文件
      final socketFile = File(socketPath);
      if (await socketFile.exists()) {
        // 尝试连接，判断是否有实例运行
        try {
          final address = InternetAddress(socketPath, type: InternetAddressType.unix);
          final socket = await Socket.connect(address, 0, timeout: const Duration(milliseconds: 500));
          await socket.close();
          // 连接成功，说明已有实例运行
          return false;
        } catch (e) {
          // 连接失败，说明是残留的 socket 文件，删除它
          await socketFile.delete();
        }
      }

      // 创建服务器
      final address = InternetAddress(socketPath, type: InternetAddressType.unix);
      _serverSocket = await ServerSocket.bind(address, 0);
      _isRunning = true;

      // ignore: avoid_print
      print('[SingleInstance] ✅ 主实例启动: $socketPath');

      // 监听连接
      _serverSocket!.listen(
        _handleConnection,
        onError: (error) {
          // ignore: avoid_print
          print('[SingleInstance] 服务器错误: $error');
        },
        onDone: () {
          // ignore: avoid_print
          print('[SingleInstance] 服务器关闭');
          _isRunning = false;
        },
      );

      return true;
    } catch (e) {
      // ignore: avoid_print
      print('[SingleInstance] ❌ 启动失败: $e');
      return false;
    }
  }

  /// 向已运行实例发送命令
  Future<bool> sendCommandToRunningInstance(String command) async {
    try {
      final address = InternetAddress(socketPath, type: InternetAddressType.unix);
      final socket = await Socket.connect(address, 0, timeout: const Duration(seconds: 2));

      // 发送命令 (协议: 4字节长度 + UTF-8文本)
      final commandBytes = Uint8List.fromList(command.codeUnits);
      final lenBytes = ByteData(4);
      lenBytes.setUint32(0, commandBytes.length, Endian.little);

      socket.add(lenBytes.buffer.asUint8List());
      socket.add(commandBytes);
      await socket.flush();
      await socket.close();

      // ignore: avoid_print
      print('[SingleInstance] ✅ 命令已发送: $command');
      return true;
    } catch (e) {
      // ignore: avoid_print
      print('[SingleInstance] ❌ 发送命令失败: $e');
      return false;
    }
  }

  /// 处理客户端连接
  void _handleConnection(Socket client) {
    _clients.add(client);
    // ignore: avoid_print
    print('[SingleInstance] 收到连接');

    final buffer = BytesBuilder();

    client.listen(
      (data) {
        buffer.add(data);
        _processBuffer(buffer, client);
      },
      onError: (error) {
        // ignore: avoid_print
        print('[SingleInstance] 客户端错误: $error');
        _clients.remove(client);
      },
      onDone: () {
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
      print('[SingleInstance] 收到命令: $command');

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

  /// 停止服务
  Future<void> dispose() async {
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
    print('[SingleInstance] 已停止');
  }
}
