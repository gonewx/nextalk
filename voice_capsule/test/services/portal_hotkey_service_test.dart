import 'dart:async';

import 'package:dbus/dbus.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/constants/hotkey_constants.dart';
import 'package:voice_capsule/services/portal_hotkey_service.dart';

/// Story 3-10: PortalHotkeyService 单元测试
///
/// 用 FakeGlobalShortcutsBackend 注入替换真实 D-Bus 层，验证编排逻辑：
/// - 探测成功 → 注册；接口缺失 / 版本过低 → 降级
/// - CreateSession/BindShortcuts 失败 → 降级并清理 session
/// - Activated 信号按 session + id 过滤后触发回调（AC2）
/// - 单次运行禁止重复重绑（AC3）
/// - dispose 关闭 session（AC7）
///
/// Mock 模式参考 test/services/ 既有 service 测试的构造注入 + fake 依赖惯例。

/// 可编程的 D-Bus 层伪实现
class FakeGlobalShortcutsBackend implements GlobalShortcutsBackend {
  FakeGlobalShortcutsBackend({
    this.version = 2,
    this.versionError,
    this.createError,
    this.bindError,
    this.sessionHandle = '/org/freedesktop/portal/desktop/session/fake/s1',
  });

  /// 探测返回的 version
  int version;

  /// 若非 null，getVersion 抛出此错误（模拟接口缺失）
  Object? versionError;

  /// 若非 null，createSession 抛出此错误
  Object? createError;

  /// 若非 null，bindShortcuts 抛出此错误
  Object? bindError;

  String sessionHandle;

  final _activatedController =
      StreamController<PortalShortcutActivation>.broadcast();

  // 调用记录（供断言）
  int getVersionCalls = 0;
  int createSessionCalls = 0;
  int bindShortcutsCalls = 0;
  final List<String> closedSessions = [];
  bool disposed = false;
  List<PortalShortcutBinding>? lastBoundShortcuts;

  /// 测试触发一次激活
  void emitActivated(String session, String shortcutId) {
    _activatedController.add(PortalShortcutActivation(session, shortcutId));
  }

  @override
  Future<int> getVersion() async {
    getVersionCalls++;
    if (versionError != null) throw versionError!;
    return version;
  }

  @override
  Future<String> createSession(String sessionToken) async {
    createSessionCalls++;
    if (createError != null) throw createError!;
    return sessionHandle;
  }

  @override
  Future<void> bindShortcuts(
    String sessionHandle,
    List<PortalShortcutBinding> shortcuts,
  ) async {
    bindShortcutsCalls++;
    lastBoundShortcuts = shortcuts;
    if (bindError != null) throw bindError!;
  }

  @override
  Stream<PortalShortcutActivation> get onActivated =>
      _activatedController.stream;

  @override
  Future<void> closeSession(String sessionHandle) async {
    closedSessions.add(sessionHandle);
  }

  @override
  Future<void> dispose() async {
    disposed = true;
    await _activatedController.close();
  }
}

void main() {
  group('PortalHotkeyService', () {
    group('能力探测与降级 (AC1/AC4)', () {
      test('接口可用且版本满足 → 注册成功', () async {
        final backend = FakeGlobalShortcutsBackend(version: 2);
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
        );

        final result = await service.register();

        expect(result, PortalRegistrationResult.registered);
        expect(service.isRegistered, isTrue);
        expect(service.fallbackReason, isNull);
        expect(backend.createSessionCalls, 1);
        expect(backend.bindShortcutsCalls, 1);
      });

      test('接口不存在（getVersion 抛错）→ unsupported 降级', () async {
        final backend = FakeGlobalShortcutsBackend(
          versionError: Exception('org.freedesktop.DBus.Error.UnknownInterface'),
        );
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
        );

        final result = await service.register();

        expect(result, PortalRegistrationResult.unsupported);
        expect(service.isRegistered, isFalse);
        expect(service.fallbackReason, isNotNull);
        expect(backend.createSessionCalls, 0); // 不应尝试建会话
      });

      test('版本过低 → unsupported 降级', () async {
        final backend = FakeGlobalShortcutsBackend(version: 0);
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
          minVersion: 1,
        );

        final result = await service.register();

        expect(result, PortalRegistrationResult.unsupported);
        expect(service.fallbackReason, contains('版本过低'));
        expect(backend.createSessionCalls, 0);
      });
    });

    group('注册流程失败 (AC4)', () {
      test('CreateSession 失败 → failed 降级', () async {
        final backend = FakeGlobalShortcutsBackend(
          createError: Exception('create boom'),
        );
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
        );

        final result = await service.register();

        expect(result, PortalRegistrationResult.failed);
        expect(service.isRegistered, isFalse);
        expect(service.fallbackReason, contains('Portal 注册失败'));
      });

      test('BindShortcuts 失败 → failed 降级并清理已开 session', () async {
        final backend = FakeGlobalShortcutsBackend(
          bindError: Exception('bind boom'),
        );
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
        );

        final result = await service.register();

        expect(result, PortalRegistrationResult.failed);
        expect(service.isRegistered, isFalse);
        // 已开 session 必须被关闭，避免残留（AC7）
        expect(backend.closedSessions, contains(backend.sessionHandle));
      });

      test('用户取消绑定 → cancelled 降级，且不锁定可重试（决策 2A）', () async {
        final backend = FakeGlobalShortcutsBackend(
          bindError: const PortalUserCancelledException(),
        );
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
        );

        final result = await service.register();

        expect(result, PortalRegistrationResult.cancelled);
        expect(service.isRegistered, isFalse);
        // 已开 session 必须被清理
        expect(backend.closedSessions, contains(backend.sessionHandle));

        // 取消不锁定 _registerAttempted：再次 register 应真正重新尝试
        backend.bindError = null;
        final retry = await service.register();
        expect(retry, PortalRegistrationResult.registered);
        expect(service.isRegistered, isTrue);
        expect(backend.createSessionCalls, 2); // 第二次确实重建了 session
      });

      test('非取消类失败会锁定，不再重试（避免 GNOME 反复弹窗）', () async {
        final backend = FakeGlobalShortcutsBackend(
          bindError: Exception('bind boom'),
        );
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
        );

        expect(await service.register(), PortalRegistrationResult.failed);

        // 即便后续 backend 恢复，也不再重试（守卫锁定）
        backend.bindError = null;
        expect(await service.register(), PortalRegistrationResult.failed);
        expect(backend.createSessionCalls, 1); // 只尝试过一次
      });
    });

    group('BindShortcuts 参数 (AC1/2.2)', () {
      test('绑定使用稳定 id 与默认 Super+Z trigger（避开 WM 占用键）', () async {
        final backend = FakeGlobalShortcutsBackend();
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
        );

        await service.register();

        final bound = backend.lastBoundShortcuts!;
        expect(bound, hasLength(1));
        expect(bound.first.id, HotkeyConstants.portalShortcutId);
        expect(bound.first.preferredTrigger, HotkeyConstants.portalDefaultTrigger);
        // ALT+space 与 GNOME activate-window-menu 冲突，默认键不得使用它
        expect(bound.first.preferredTrigger, isNot(equals('ALT+space')));
      });
    });

    group('Activated 信号处理 (AC2/AC6)', () {
      test('匹配的 session + id 触发回调', () async {
        final backend = FakeGlobalShortcutsBackend();
        var toggleCount = 0;
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async => toggleCount++,
        );
        await service.register();

        backend.emitActivated(
          backend.sessionHandle,
          HotkeyConstants.portalShortcutId,
        );
        await Future.delayed(Duration.zero);

        expect(toggleCount, 1);
      });

      test('不匹配的 session 不触发回调', () async {
        final backend = FakeGlobalShortcutsBackend();
        var toggleCount = 0;
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async => toggleCount++,
        );
        await service.register();

        backend.emitActivated(
          '/some/other/session',
          HotkeyConstants.portalShortcutId,
        );
        await Future.delayed(Duration.zero);

        expect(toggleCount, 0);
      });

      test('不匹配的 shortcut id 不触发回调', () async {
        final backend = FakeGlobalShortcutsBackend();
        var toggleCount = 0;
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async => toggleCount++,
        );
        await service.register();

        backend.emitActivated(backend.sessionHandle, 'some-other-shortcut');
        await Future.delayed(Duration.zero);

        expect(toggleCount, 0);
      });
    });

    group('单次运行禁止重复重绑 (AC3)', () {
      test('重复调用 register 不再重建 session', () async {
        final backend = FakeGlobalShortcutsBackend();
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
        );

        final r1 = await service.register();
        final r2 = await service.register();

        expect(r1, PortalRegistrationResult.registered);
        expect(r2, PortalRegistrationResult.registered);
        expect(backend.createSessionCalls, 1); // 只建一次
        expect(backend.bindShortcutsCalls, 1); // 只绑一次
      });
    });

    group('dispose 清理 (AC7)', () {
      test('dispose 关闭 session 并释放连接', () async {
        final backend = FakeGlobalShortcutsBackend();
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
        );
        await service.register();

        await service.dispose();

        expect(backend.closedSessions, contains(backend.sessionHandle));
        expect(backend.disposed, isTrue);
        expect(service.isRegistered, isFalse);
      });

      test('未注册时 dispose 仍安全释放连接', () async {
        final backend = FakeGlobalShortcutsBackend(
          versionError: Exception('unsupported'),
        );
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: () async {},
        );
        await service.register(); // 降级，无 session

        await service.dispose();

        expect(backend.closedSessions, isEmpty); // 无 session 可关
        expect(backend.disposed, isTrue);
      });
    });

    group('双触发路径防抖回归 (AC6)', () {
      // 系统快捷键命令 (SingleInstance.onCommand) 与 Portal Activated 信号
      // 都收敛到 HotkeyController.instance.toggle()——同一带重入防护
      // (_isProcessing) 的唯一入口。此测试建模该防护，验证两个触发源并发时
      // 不会双重执行，从而不产生状态机竞态。
      test('两个触发源经同一重入防护入口并发触发只生效一次', () async {
        // 复刻 HotkeyController._onHotkeyPressed 的 _isProcessing 防护语义
        var processing = false;
        var effectiveRuns = 0;
        Future<void> guardedToggle() async {
          if (processing) return; // 重入防护：上一操作进行中则忽略
          processing = true;
          try {
            effectiveRuns++;
            await Future<void>.delayed(const Duration(milliseconds: 20));
          } finally {
            processing = false;
          }
        }

        final backend = FakeGlobalShortcutsBackend();
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: guardedToggle, // Portal 路径 → 共享入口
        );
        await service.register();

        // 并发：命令路径直接调用 + Portal Activated 几乎同时触发
        final commandPath = guardedToggle();
        backend.emitActivated(
          backend.sessionHandle,
          HotkeyConstants.portalShortcutId,
        );
        await Future.delayed(Duration.zero); // 让 Activated 派发到监听器
        await commandPath;

        // 重叠窗口内只应生效一次，第二个被 _isProcessing 挡下
        expect(effectiveRuns, 1);
      });

      test('两次串行触发（防护释放后）各自生效一次', () async {
        var processing = false;
        var effectiveRuns = 0;
        Future<void> guardedToggle() async {
          if (processing) return;
          processing = true;
          try {
            effectiveRuns++;
          } finally {
            processing = false;
          }
        }

        final backend = FakeGlobalShortcutsBackend();
        final service = PortalHotkeyService(
          backend: backend,
          onActivated: guardedToggle,
        );
        await service.register();

        // 第一次触发完成后再触发第二次（防护已释放）
        backend.emitActivated(
          backend.sessionHandle,
          HotkeyConstants.portalShortcutId,
        );
        await Future.delayed(const Duration(milliseconds: 5));
        backend.emitActivated(
          backend.sessionHandle,
          HotkeyConstants.portalShortcutId,
        );
        await Future.delayed(const Duration(milliseconds: 5));

        expect(effectiveRuns, 2);
      });
    });

    group('GNOME 48.0 假失败识别 (portal-gnome 上游 27511907)', () {
      const binding = PortalShortcutBinding(
        id: 'toggle-voice-input',
        description: 'Toggle Nextalk voice input',
      );

      /// 构造 portal Response results 里的 shortcuts 数组（(sa{sv}) 结构）
      DBusArray shortcutsArray(List<String> ids) => DBusArray(
            DBusSignature('(sa{sv})'),
            ids
                .map((id) => DBusStruct([
                      DBusString(id),
                      DBusDict.stringVariant(const {}),
                    ]))
                .toList(),
          );

      test('response=2 但 results 携带全部请求 id → 判为实际绑定成功', () {
        final results = <String, DBusValue>{
          'shortcuts': shortcutsArray(['toggle-voice-input']),
        };
        expect(
          DBusGlobalShortcutsBackend.shortcutsActuallyBound(
              results, const [binding]),
          isTrue,
        );
      });

      test('results 为空 vardict（真失败路径）→ 不误判', () {
        expect(
          DBusGlobalShortcutsBackend.shortcutsActuallyBound(
              const {}, const [binding]),
          isFalse,
        );
      });

      test('shortcuts 数组缺请求 id → 不误判', () {
        final results = <String, DBusValue>{
          'shortcuts': shortcutsArray(['other-shortcut']),
        };
        expect(
          DBusGlobalShortcutsBackend.shortcutsActuallyBound(
              results, const [binding]),
          isFalse,
        );
      });

      test('shortcuts 为空数组 → 不误判', () {
        final results = <String, DBusValue>{
          'shortcuts': shortcutsArray(const []),
        };
        expect(
          DBusGlobalShortcutsBackend.shortcutsActuallyBound(
              results, const [binding]),
          isFalse,
        );
      });
    });
  });
}
