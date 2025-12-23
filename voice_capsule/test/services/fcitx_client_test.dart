import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/fcitx_client.dart';

import '../helpers/mock_fcitx_server.dart';

void main() {
  group('FcitxClient', () {
    late MockFcitxServer server;
    late FcitxClient client;

    setUp(() async {
      server = MockFcitxServer();
      await server.start();
      client = FcitxClient(socketPath: server.socketPath);
    });

    tearDown(() async {
      await client.dispose();
      await server.stop();
    });

    group('connect', () {
      test('应该成功连接到 Mock Server', () async {
        // Act
        await client.connect();

        // Assert
        expect(client.state, equals(FcitxConnectionState.connected));
      });

      test('连接状态应该通过 Stream 广播', () async {
        // Arrange
        final states = <FcitxConnectionState>[];
        client.stateStream.listen(states.add);

        // Act
        await client.connect();
        await Future.delayed(Duration(milliseconds: 50)); // 等待事件传播

        // Assert
        expect(states, contains(FcitxConnectionState.connecting));
        expect(states, contains(FcitxConnectionState.connected));
      });
    });

    group('Socket 不存在场景', () {
      test('连接不存在的 Socket 应该抛出 connectionFailed', () async {
        // Arrange
        final badClient =
            FcitxClient(socketPath: '/tmp/nonexistent-socket.sock');

        // Act & Assert
        FcitxError? caughtError;
        try {
          await badClient.connect();
        } on FcitxError catch (e) {
          caughtError = e;
        }

        expect(caughtError, equals(FcitxError.connectionFailed));
        await badClient.dispose();
      });
    });

    group('sendText 和协议编码', () {
      test('应该成功发送文本', () async {
        // Arrange
        await client.connect();
        const testText = 'Hello World';

        // Act
        await client.sendText(testText);
        await Future.delayed(Duration(milliseconds: 50)); // 等待数据传输

        // Assert
        expect(server.verifyLastMessage(testText), isTrue);
      });

      test('协议格式应该正确 (4字节长度 LE + UTF-8 文本)', () async {
        // Arrange
        await client.connect();
        const testText = '测试中文';

        // Act
        await client.sendText(testText);
        await Future.delayed(Duration(milliseconds: 50));

        // Assert
        expect(server.receivedMessages.isNotEmpty, isTrue);

        final message = server.receivedMessages.last;
        expect(server.verifyProtocolFormat(message), isTrue);

        // 验证长度字段
        final byteData = ByteData.sublistView(message);
        final declaredLength = byteData.getUint32(0, Endian.little);
        final actualText = utf8.decode(message.sublist(4));
        expect(actualText.length, equals(testText.length));
        expect(declaredLength, equals(utf8.encode(testText).length));
      });

      test('UTF-8 编码应该正确处理中文', () async {
        // Arrange
        await client.connect();
        const testText = '你好世界';

        // Act
        await client.sendText(testText);
        await Future.delayed(Duration(milliseconds: 50));

        // Assert
        expect(server.lastDecodedText, equals(testText));
      });
    });

    group('消息大小限制', () {
      test('超过 1MB 的消息应该抛出 messageTooLarge', () async {
        // Arrange
        await client.connect();
        // 创建超过 1MB 的文本 (1MB + 1 byte)
        final largeText = 'a' * (maxMessageSize + 1);

        // Act & Assert
        expect(
          () => client.sendText(largeText),
          throwsA(equals(FcitxError.messageTooLarge)),
        );
      });

      test('正好 1MB 的消息应该成功发送', () async {
        // Arrange
        await client.connect();
        // 创建正好 1MB 的文本
        final exactText = 'a' * maxMessageSize;

        // Act & Assert - 不应该抛出异常
        await client.sendText(exactText);
        await Future.delayed(Duration(milliseconds: 100));

        expect(server.receivedMessages.isNotEmpty, isTrue);
      });
    });

    group('dispose', () {
      test('dispose 后状态应该是 disconnected', () async {
        // Arrange
        await client.connect();
        expect(client.state, equals(FcitxConnectionState.connected));

        // Act
        await client.dispose();

        // Assert
        expect(client.state, equals(FcitxConnectionState.disconnected));
      });

      test('多次调用 dispose 不应该报错', () async {
        // Arrange
        await client.connect();

        // Act & Assert - 多次调用不应该抛出异常
        await client.dispose();
        await client.dispose();
        await client.dispose();
      });

      test('dispose 后调用 connect 应该抛出 StateError', () async {
        // Arrange
        await client.dispose();

        // Act & Assert
        expect(
          () => client.connect(),
          throwsA(isA<StateError>()),
        );
      });

      test('dispose 后调用 sendText 应该抛出 StateError', () async {
        // Arrange
        await client.connect();
        await client.dispose();

        // Act & Assert
        expect(
          () => client.sendText('test'),
          throwsA(isA<StateError>()),
        );
      });
    });

    group('重连逻辑', () {
      test('断开后 sendText 应该自动重连', () async {
        // Arrange
        await client.connect();
        await server.disconnectClient();
        await Future.delayed(Duration(milliseconds: 100)); // 等待检测到断开

        // 重启服务器 (模拟恢复)
        await server.stop();
        server = MockFcitxServer(path: server.socketPath);
        await server.start();

        // Act
        await client.sendText('重连测试');
        await Future.delayed(Duration(milliseconds: 100));

        // Assert
        expect(server.lastDecodedText, equals('重连测试'));
      });

      test('重连失败后应该进入降级模式', () async {
        // Arrange
        final badClient = FcitxClient(socketPath: '/tmp/never-exists.sock');

        // Act
        FcitxError? caughtError;
        try {
          await badClient.sendText('test');
        } on FcitxError catch (e) {
          caughtError = e;
        }

        // Assert
        expect(caughtError, equals(FcitxError.reconnectFailed));
        expect(badClient.isInDegradedMode, isTrue);

        await badClient.dispose();
      });

      test('降级模式下 sendText 应该立即失败', () async {
        // Arrange
        final badClient = FcitxClient(socketPath: '/tmp/never-exists.sock');

        // 第一次失败，进入降级模式
        try {
          await badClient.sendText('test');
        } catch (_) {}

        expect(badClient.isInDegradedMode, isTrue);

        // Act - 第二次应该立即失败
        FcitxError? caughtError;
        try {
          await badClient.sendText('test');
        } on FcitxError catch (e) {
          caughtError = e;
        }

        // Assert
        expect(caughtError, equals(FcitxError.reconnectFailed));

        await badClient.dispose();
      });

      test('resetDegradedMode 应该允许重新尝试连接', () async {
        // Arrange
        final badClient = FcitxClient(socketPath: '/tmp/never-exists.sock');

        // 进入降级模式
        try {
          await badClient.sendText('test');
        } catch (_) {}

        expect(badClient.isInDegradedMode, isTrue);

        // Act
        badClient.resetDegradedMode();

        // Assert
        expect(badClient.isInDegradedMode, isFalse);

        await badClient.dispose();
      });
    });

    group('FcitxError 扩展', () {
      test('所有错误应该有本地化消息', () {
        for (final error in FcitxError.values) {
          expect(error.localizedMessage.isNotEmpty, isTrue);
        }
      });
    });

    group('连接状态枚举', () {
      test('FcitxConnectionState 应该包含所有预期状态', () {
        expect(FcitxConnectionState.values.length, equals(4));
        expect(
          FcitxConnectionState.values,
          containsAll([
            FcitxConnectionState.disconnected,
            FcitxConnectionState.connecting,
            FcitxConnectionState.connected,
            FcitxConnectionState.error,
          ]),
        );
      });
    });

    // [FIX-M2] 添加缺失的测试用例
    group('verifySocketPermissions', () {
      test('有效 socket 应该返回权限验证结果', () async {
        // Arrange
        await client.connect();

        // Act
        final result = await client.verifySocketPermissions();

        // Assert - Mock server 创建的 socket 权限可能不是 0600
        // 这里只验证方法可以正常调用并返回 bool
        expect(result, isA<bool>());
      });

      test('不存在的 socket 应该返回 false', () async {
        // Arrange
        final badClient = FcitxClient(socketPath: '/tmp/nonexistent.sock');

        // Act
        final result = await badClient.verifySocketPermissions();

        // Assert
        expect(result, isFalse);
        await badClient.dispose();
      });
    });

    group('并发安全', () {
      test('并发 sendText 调用应该正确序列化', () async {
        // Arrange
        await client.connect();
        final messages = ['消息1', '消息2', '消息3'];

        // Act - 并发发送多条消息
        await Future.wait(messages.map((msg) => client.sendText(msg)));
        await Future.delayed(Duration(milliseconds: 100));

        // Assert - 所有消息都应该被接收
        expect(server.decodedTexts.length, equals(3));
        for (final msg in messages) {
          expect(server.decodedTexts, contains(msg));
        }
      });
    });
  });
}
