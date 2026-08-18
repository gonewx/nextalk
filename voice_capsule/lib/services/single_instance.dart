import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';

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

  /// 命令处理完毕后回写给客户端的确认字节 (ASCII ACK)。
  ///
  /// 存在的理由：Unix socket 的 listen backlog 会让 connect()/write() 在
  /// **没有任何人 accept** 的情况下照样成功——内核只管把连接放进队列。一旦
  /// Dart isolate 已死而进程空壳仍持有 socket，nextalk-toggle 就会把"内核收下了"
  /// 误判成"应用处理了"，从此永远不走冷启动回退，用户按多少次都零反应。
  /// 只有应用层亲自回一个字节，才能证明命令真的被 onCommand 消费掉了。
  static const int ackByte = 0x06;

  /// 测试专用的 socket 路径覆盖点。
  ///
  /// 必须存在的理由: [socketPath] 默认取 XDG_RUNTIME_DIR, 而 Dart 测试改不了
  /// Platform.environment。若不覆盖, 测试会去 bind 用户**正在运行**的实例的
  /// socket, 甚至把它当残留文件删掉 —— 跑一次测试就把用户的语音输入搞坏。
  @visibleForTesting
  static String? socketPathOverride;

  /// 获取 Socket 路径
  String get socketPath {
    final override = socketPathOverride;
    if (override != null) {
      return override;
    }
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

      // 触发回调。回调抛错不能打断后面的 ACK 与 buffer 清理:
      // 少回一个 ACK 会让 nextalk-toggle 白花一轮 /proc 存活判定, 而 buffer
      // 不清理更糟 —— 这条命令会残留在缓冲区里, 被后续每次数据到达反复重放。
      if (onCommand != null) {
        try {
          onCommand!(command);
        } catch (e) {
          // ignore: avoid_print
          print('[SingleInstance] 命令处理异常: $e');
        }
      }

      // 回写 ACK：证明这一字节出自应用层代码, 而非内核代收 (对端可能已 close，失败无害)
      _sendAck(client);

      // 清除已处理的数据
      buffer.clear();
      if (data.length > 4 + len) {
        buffer.add(data.sublist(4 + len));
      }
    }
  }

  /// 回写单字节 ACK。
  ///
  /// `nextalk --toggle` 内部的 [sendCommandToRunningInstance] 发完即 close,
  /// 不读 ACK, 于是这里几乎必然撞上已关闭的连接。两条失败路径都得堵住:
  ///   - IOSink 自身已关闭 -> [Socket.add] **同步**抛 StateError
  ///   - 对端先行 close -> write 的 EPIPE 经 [Socket.done] **异步**上报,
  ///     不接住就会冒泡成未捕获异常 (被 runZonedGuarded 记成 Unhandled 脏日志)
  /// 两者都无害: ACK 只是给 nextalk-toggle 的存活证明, 送不到不影响命令已执行。
  void _sendAck(Socket client) {
    try {
      client.add(const [ackByte]);
    } catch (_) {
      return; // IOSink 已关闭
    }
    client.done.ignore();
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
