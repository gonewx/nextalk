import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/single_instance.dart';

/// SingleInstance 的 ACK 契约测试。
///
/// 为什么这些用例重要: nextalk-toggle 靠这一个字节判断"应用真的处理了命令"。
/// Unix socket 的 listen backlog 会让 connect()/write() 在没人 accept 时照样成功,
/// 所以"写成功"不能证明命令被消费。ACK 一旦不回, 脚本就得退回到读 /proc 猜存活;
/// ACK 若在 onCommand 之前发出, 又会把"收到连接"冒充成"命令已执行"。
void main() {
  late Directory tmpDir;

  setUp(() async {
    tmpDir = await Directory.systemTemp.createTemp('nextalk_si_test_');
    // 隔离到临时路径: 绝不能碰用户正在运行的实例的 socket
    SingleInstance.socketPathOverride = '${tmpDir.path}/nextalk.sock';
  });

  tearDown(() async {
    await SingleInstance.instance.dispose();
    SingleInstance.instance.onCommand = null;
    SingleInstance.socketPathOverride = null;
    if (await tmpDir.exists()) {
      await tmpDir.delete(recursive: true);
    }
  });

  /// 按协议 (4字节LE长度 + UTF-8) 发送命令, 返回读到的首字节 (超时返回 null)
  Future<int?> sendCommand(String socketPath, String command) async {
    final address =
        InternetAddress(socketPath, type: InternetAddressType.unix);
    final socket = await Socket.connect(address, 0,
        timeout: const Duration(seconds: 2));
    try {
      final bytes = Uint8List.fromList(command.codeUnits);
      final len = ByteData(4)..setUint32(0, bytes.length, Endian.little);
      socket.add(len.buffer.asUint8List());
      socket.add(bytes);
      await socket.flush();

      // 只等首字节, 拿不到就当没回 ACK
      return await socket.first
          .then<int?>((chunk) => chunk.isEmpty ? null : chunk.first)
          .timeout(const Duration(seconds: 2), onTimeout: () => null);
    } finally {
      socket.destroy();
    }
  }

  group('SingleInstance ACK', () {
    test('处理完命令后回写 ackByte', () async {
      // socketPath 取自 XDG_RUNTIME_DIR, 用临时目录避免踩到真实运行的实例
      final si = SingleInstance.instance;
      final became = await si.tryBecomeMainInstance();
      expect(became, isTrue, reason: '应能在临时目录成功 bind');

      final received = <String>[];
      si.onCommand = received.add;

      final ack = await sendCommand(si.socketPath, 'toggle');

      expect(received, ['toggle'], reason: '命令应被 onCommand 消费');
      expect(ack, SingleInstance.ackByte,
          reason: 'ACK 是脚本判定"应用真的处理了"的唯一凭据');
    });

    test('onCommand 抛异常时仍回 ACK, 且命令不被重放', () async {
      final si = SingleInstance.instance;
      await si.tryBecomeMainInstance();

      // 回调抛错是真实可能的 (HotkeyController.toggle 内部任何一层出错都会冒上来)。
      // 若 _sendAck 与 buffer.clear() 被异常跳过, 这条命令会残留在缓冲区,
      // 被后续每次数据到达反复重放 —— 一次按键变成多次录音开关。
      final received = <String>[];
      si.onCommand = (cmd) {
        received.add(cmd);
        throw StateError('boom');
      };

      final ack = await sendCommand(si.socketPath, 'toggle');
      expect(ack, SingleInstance.ackByte,
          reason: '回调抛错不代表实例已死, 仍须回 ACK 免得脚本误杀');
      expect(received, ['toggle']);

      // 再发一条: 若上一条没从 buffer 清掉, 这里会看到它被重放
      si.onCommand = received.add;
      await sendCommand(si.socketPath, 'show');
      expect(received, ['toggle', 'show'], reason: '不得重放已处理的命令');
    });

    test('未注册 onCommand 时也回 ACK (实例仍是活的)', () async {
      final si = SingleInstance.instance;
      await si.tryBecomeMainInstance();
      si.onCommand = null;

      final ack = await sendCommand(si.socketPath, 'toggle');

      expect(ack, SingleInstance.ackByte,
          reason: '回调没挂上不代表实例已死, 不该让脚本误杀它');
    });

    test('连续两条命令各自都回 ACK', () async {
      final si = SingleInstance.instance;
      await si.tryBecomeMainInstance();

      final received = <String>[];
      si.onCommand = received.add;

      final first = await sendCommand(si.socketPath, 'show');
      final second = await sendCommand(si.socketPath, 'hide');

      expect(received, ['show', 'hide']);
      expect(first, SingleInstance.ackByte);
      expect(second, SingleInstance.ackByte);
    });

    test('客户端发完即断开不会拖垮实例 (ACK 写入失败须被吞掉)', () async {
      final si = SingleInstance.instance;
      await si.tryBecomeMainInstance();

      final received = <String>[];
      si.onCommand = received.add;

      // 复刻 `nextalk --toggle` 内部路径: 发完立刻 destroy, 从不读 ACK
      final address =
          InternetAddress(si.socketPath, type: InternetAddressType.unix);
      final socket = await Socket.connect(address, 0);
      final bytes = Uint8List.fromList('toggle'.codeUnits);
      final len = ByteData(4)..setUint32(0, bytes.length, Endian.little);
      socket.add(len.buffer.asUint8List());
      socket.add(bytes);
      await socket.flush();
      socket.destroy();

      // 等实例处理完
      await Future<void>.delayed(const Duration(milliseconds: 300));
      expect(received, ['toggle'], reason: '命令仍应被处理');

      // 关键: 写 ACK 撞上已关闭的连接不能把 server 打挂, 后续命令还得能收
      final ack = await sendCommand(si.socketPath, 'show');
      expect(received, ['toggle', 'show'],
          reason: 'EPIPE 被吞掉后实例应继续服务');
      expect(ack, SingleInstance.ackByte);
    });
  });
}
