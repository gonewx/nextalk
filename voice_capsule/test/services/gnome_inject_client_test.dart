import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/gnome_inject_client.dart';
import 'package:voice_capsule/services/hotkey_controller.dart';

/// GNOME 扩展注入后端测试 (spec-fix-fedora-inject-clipboard-fallback)
///
/// 通过构造注入 FakeGnomeInjectBackend 覆盖：
/// - GnomeInjectClient 的可用性探测/缓存/失效语义
/// - decideInjectBackend 三级注入链决策 (覆盖 spec I/O 矩阵各行)

/// Fake backend：可编程探测结果与提交结果，记录调用次数
class FakeGnomeInjectBackend implements GnomeInjectBackend {
  FakeGnomeInjectBackend({
    this.probeResult = true,
    this.probeError,
    this.commitResult = 'OK',
    this.commitError,
  });

  bool probeResult;
  Object? probeError;
  String commitResult;
  Object? commitError;

  int probeCalls = 0;
  int commitCalls = 0;
  final List<String> committedTexts = [];
  bool disposed = false;

  @override
  Future<bool> probe() async {
    probeCalls++;
    final error = probeError;
    if (error != null) throw error;
    return probeResult;
  }

  @override
  Future<String> commitText(String text) async {
    commitCalls++;
    committedTexts.add(text);
    final error = commitError;
    if (error != null) throw error;
    return commitResult;
  }

  @override
  Future<void> dispose() async {
    disposed = true;
  }
}

void main() {
  group('GnomeInjectClient', () {
    group('isAvailable', () {
      test('扩展接口已导出时返回 true', () async {
        final backend = FakeGnomeInjectBackend(probeResult: true);
        final client = GnomeInjectClient(backend: backend);

        expect(await client.isAvailable(), isTrue);
      });

      test('接口未导出 (扩展未装/未启用) 时返回 false', () async {
        final backend = FakeGnomeInjectBackend(probeResult: false);
        final client = GnomeInjectClient(backend: backend);

        expect(await client.isAvailable(), isFalse);
      });

      test('探测异常 (非 GNOME 桌面，org.gnome.Shell 不存在) 时静默返回 false', () async {
        final backend =
            FakeGnomeInjectBackend(probeError: Exception('ServiceUnknown'));
        final client = GnomeInjectClient(backend: backend);

        expect(await client.isAvailable(), isFalse);
      });

      test('可用性结果应缓存，不重复探测', () async {
        final backend = FakeGnomeInjectBackend(probeResult: true);
        final client = GnomeInjectClient(backend: backend);

        await client.isAvailable();
        await client.isAvailable();
        await client.isAvailable();

        expect(backend.probeCalls, equals(1));
      });

      test('不可用结果在 TTL 内缓存 (探测超时 ≤500ms 只发生一次)', () async {
        final backend = FakeGnomeInjectBackend(probeResult: false);
        final client = GnomeInjectClient(backend: backend);

        await client.isAvailable();
        await client.isAvailable();

        expect(backend.probeCalls, equals(1));
      });

      test('负缓存过期后重新探测 (登录竞态自愈：扩展加载晚于应用启动)', () async {
        final backend = FakeGnomeInjectBackend(probeResult: false);
        final client = GnomeInjectClient(
          backend: backend,
          negativeCacheTtl: Duration.zero,
        );

        expect(await client.isAvailable(), isFalse);
        backend.probeResult = true; // 模拟 gnome-shell 稍后完成扩展加载
        expect(await client.isAvailable(), isTrue);
        expect(backend.probeCalls, equals(2));

        // 转正后长期缓存，不再重复探测
        expect(await client.isAvailable(), isTrue);
        expect(backend.probeCalls, equals(2));
      });

      test('dispose 后返回 false', () async {
        final backend = FakeGnomeInjectBackend(probeResult: true);
        final client = GnomeInjectClient(backend: backend);

        await client.dispose();

        expect(await client.isAvailable(), isFalse);
        expect(backend.disposed, isTrue);
      });
    });

    group('commitText', () {
      test('扩展返回 OK 时提交成功', () async {
        final backend = FakeGnomeInjectBackend(commitResult: 'OK');
        final client = GnomeInjectClient(backend: backend);

        expect(await client.commitText('你好世界'), isTrue);
        expect(backend.committedTexts, equals(['你好世界']));
      });

      test('空文本不调用后端，直接返回 false', () async {
        final backend = FakeGnomeInjectBackend();
        final client = GnomeInjectClient(backend: backend);

        expect(await client.commitText(''), isFalse);
        expect(backend.commitCalls, equals(0));
      });

      test('扩展返回 ERR 时提交失败', () async {
        final backend = FakeGnomeInjectBackend(
            commitResult: 'ERR: Main.inputMethod is null');
        final client = GnomeInjectClient(backend: backend);

        expect(await client.commitText('文本'), isFalse);
      });

      test('D-Bus 调用异常/超时时提交失败 (不抛异常，文本由调用方走剪贴板保留)', () async {
        final backend =
            FakeGnomeInjectBackend(commitError: Exception('timeout'));
        final client = GnomeInjectClient(backend: backend);

        expect(await client.commitText('文本'), isFalse);
      });

      test('提交失败应使可用性缓存失效，下次重新探测', () async {
        final backend = FakeGnomeInjectBackend(commitResult: 'ERR: boom');
        final client = GnomeInjectClient(backend: backend);

        expect(await client.isAvailable(), isTrue);
        expect(backend.probeCalls, equals(1));

        await client.commitText('文本'); // 失败 → 缓存失效

        await client.isAvailable(); // 触发重新探测
        expect(backend.probeCalls, equals(2));
      });

      test('提交成功不使缓存失效', () async {
        final backend = FakeGnomeInjectBackend(commitResult: 'OK');
        final client = GnomeInjectClient(backend: backend);

        await client.isAvailable();
        await client.commitText('文本');
        await client.isAvailable();

        expect(backend.probeCalls, equals(1));
      });

      test('dispose 后返回 false 且不调用后端', () async {
        final backend = FakeGnomeInjectBackend();
        final client = GnomeInjectClient(backend: backend);

        await client.dispose();

        expect(await client.commitText('文本'), isFalse);
        expect(backend.commitCalls, equals(0));
      });
    });

    group('dispose', () {
      test('幂等：多次调用不报错', () async {
        final client =
            GnomeInjectClient(backend: FakeGnomeInjectBackend());

        await client.dispose();
        await client.dispose();
      });
    });
  });

  group('decideInjectBackend 三级注入链决策 (spec I/O 矩阵)', () {
    test('fcitx5 可用 → fcitx (现状不变，不探测 GNOME)', () async {
      var gnomeProbed = false;

      final backend = await decideInjectBackend(
        text: '你好',
        fcitxAvailable: () async => true,
        gnomeAvailable: () async {
          gnomeProbed = true;
          return true;
        },
      );

      expect(backend, equals(InjectBackend.fcitx));
      expect(gnomeProbed, isFalse, reason: 'Debian 路径零回归：不应探测 GNOME');
    });

    test('fcitx5 不可用 + GNOME 扩展可达 → gnome (Fedora/ibus 场景)', () async {
      final backend = await decideInjectBackend(
        text: '你好',
        fcitxAvailable: () async => false,
        gnomeAvailable: () async => true,
      );

      expect(backend, equals(InjectBackend.gnome));
    });

    test('fcitx5 不可用 + GNOME 不可达 (扩展未装/未启用) → clipboard', () async {
      final backend = await decideInjectBackend(
        text: '你好',
        fcitxAvailable: () async => false,
        gnomeAvailable: () async => false,
      );

      expect(backend, equals(InjectBackend.clipboard));
    });

    test('非 GNOME 桌面 (探测失败即降级) → clipboard', () async {
      // GnomeInjectClient.isAvailable 内部吞掉探测异常返回 false，
      // 此处模拟其对决策链暴露的结果
      final client = GnomeInjectClient(
        backend: FakeGnomeInjectBackend(probeError: Exception('no shell')),
      );

      final backend = await decideInjectBackend(
        text: '你好',
        fcitxAvailable: () async => false,
        gnomeAvailable: client.isAvailable,
      );

      expect(backend, equals(InjectBackend.clipboard));
    });

    test('空文本 → clipboard 收尾，不探测/不调用任何注入后端', () async {
      var gnomeProbed = false;

      final backend = await decideInjectBackend(
        text: '',
        fcitxAvailable: () async => false,
        gnomeAvailable: () async {
          gnomeProbed = true;
          return true;
        },
      );

      expect(backend, equals(InjectBackend.clipboard));
      expect(gnomeProbed, isFalse);
    });

    test('CommitText 失败场景：决策为 gnome 后提交失败 → 调用方走剪贴板，文本保留', () async {
      // 决策为 gnome
      final client = GnomeInjectClient(
        backend: FakeGnomeInjectBackend(commitError: Exception('timeout')),
      );
      final backend = await decideInjectBackend(
        text: '你好',
        fcitxAvailable: () async => false,
        gnomeAvailable: client.isAvailable,
      );
      expect(backend, equals(InjectBackend.gnome));

      // 提交失败返回 false (hotkey_controller 据此恢复窗口并复制剪贴板)
      expect(await client.commitText('你好'), isFalse);
    });
  });
}
