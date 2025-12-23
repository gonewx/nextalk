import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

class MockFcitxServer {
  ServerSocket? _server;
  final List<Uint8List> receivedMessages = [];
  final List<String> decodedTexts = []; // 解码后的文本 (用于验证)
  final String socketPath;
  Socket? _lastClient;

  // [FIX-M3] TCP 分包缓冲区
  final List<int> _buffer = [];

  MockFcitxServer({String? path})
      : socketPath = path ??
            '/tmp/test-nextalk-${DateTime.now().millisecondsSinceEpoch}.sock';

  Future<void> start() async {
    // 清理旧 socket 文件
    final file = File(socketPath);
    if (await file.exists()) await file.delete();

    _server = await ServerSocket.bind(
      InternetAddress(socketPath, type: InternetAddressType.unix),
      0,
    );

    _server!.listen((client) {
      _lastClient = client;
      client.listen((data) {
        // [FIX-M3] 添加到缓冲区并尝试解析完整消息
        _buffer.addAll(data);
        _processBuffer();
      });
    });
  }

  // [FIX-M3] 处理缓冲区中的完整消息
  void _processBuffer() {
    while (_buffer.length >= 4) {
      // 读取消息长度
      final byteData =
          ByteData.sublistView(Uint8List.fromList(_buffer.sublist(0, 4)));
      final length = byteData.getUint32(0, Endian.little);

      // 检查是否有完整消息
      if (_buffer.length < 4 + length) {
        break; // 等待更多数据
      }

      // 提取完整消息
      final messageBytes = Uint8List.fromList(_buffer.sublist(0, 4 + length));
      receivedMessages.add(messageBytes);

      // 解码文本
      try {
        final text = utf8.decode(_buffer.sublist(4, 4 + length));
        decodedTexts.add(text);
      } catch (e) {
        // UTF-8 解码失败，跳过
      }

      // 从缓冲区移除已处理的消息
      _buffer.removeRange(0, 4 + length);
    }
  }

  /// 获取最后一条解码的消息文本
  String? get lastDecodedText =>
      decodedTexts.isNotEmpty ? decodedTexts.last : null;

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

  /// 模拟服务端关闭连接
  Future<void> disconnectClient() async {
    await _lastClient?.close();
    _lastClient = null;
  }

  Future<void> stop() async {
    await _lastClient?.close();
    await _server?.close();
    final file = File(socketPath);
    if (await file.exists()) await file.delete();
  }

  void clear() {
    receivedMessages.clear();
    decodedTexts.clear();
    _buffer.clear(); // [FIX-M3] 清理缓冲区
  }
}
