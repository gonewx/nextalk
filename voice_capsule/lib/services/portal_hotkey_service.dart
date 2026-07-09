import 'dart:async';
import 'dart:math';

import 'package:dbus/dbus.dart';

import '../constants/hotkey_constants.dart';
import '../utils/diagnostic_logger.dart';
import 'hotkey_controller.dart';

/// Story 3-10: XDG Desktop Portal 全局快捷键（第四代方案）
///
/// 通过 `org.freedesktop.portal.GlobalShortcuts` 在应用内注册全局快捷键，
/// 由桌面环境弹出系统授权对话框完成绑定——Wayland 官方正道，零配置。
///
/// 关键约束（详见 story Background 快捷键演进史）：
/// - **只叠加不取代**：portal backend 不支持时（GNOME <48、wlroots、Ubuntu LTS
///   默认会话），静默降级到系统快捷键 + `nextalk-toggle` 回退方案。
/// - **规范无 restore token**：每次启动用稳定 shortcut id + app_id 重新
///   CreateSession + BindShortcuts，backend 负责记忆用户绑定。
/// - **连接必须保活**：D-Bus 连接生命周期 == session 生命周期，
///   连接断开 = 快捷键失效。
/// - **单次运行禁止重复重绑**：GNOME 会反复弹窗骚扰用户。
///
/// 触发源统一收敛到 `HotkeyController.instance.toggle()`——Portal Activated
/// 只是继 `--toggle` 命令之后的又一个新触发源，不绕过状态机。

/// Portal 快捷键注册结果
enum PortalRegistrationResult {
  /// 注册成功，快捷键已绑定
  registered,

  /// backend 不支持 GlobalShortcuts（接口缺失 / 版本不足）——应回退
  unsupported,

  /// backend 支持但注册流程失败（CreateSession/BindShortcuts 出错或超时）——应回退
  failed,
}

/// 一次快捷键激活事件（backend → service）
class PortalShortcutActivation {
  /// 触发该事件的 session handle（object path 字符串）
  final String sessionHandle;

  /// 被触发的 shortcut id
  final String shortcutId;

  const PortalShortcutActivation(this.sessionHandle, this.shortcutId);
}

/// 待绑定的快捷键描述
class PortalShortcutBinding {
  /// 稳定 id
  final String id;

  /// 人类可读描述（i18n 文案，显示在系统授权对话框中）
  final String description;

  /// 建议触发键（freedesktop Shortcuts 规范格式），null 表示由用户/backend 决定
  final String? preferredTrigger;

  const PortalShortcutBinding({
    required this.id,
    required this.description,
    this.preferredTrigger,
  });
}

/// GlobalShortcuts D-Bus 交互抽象层
///
/// 抽出接口是为了在单测中注入 fake，不依赖真实 session bus
/// （对齐项目既有 FakeASREngine 构造注入模式）。
abstract class GlobalShortcutsBackend {
  /// 读取接口 version 属性探测可用性。
  ///
  /// 接口不存在时抛出明确的 D-Bus 错误（不会挂起）。
  Future<int> getVersion();

  /// CreateSession，返回真正的 session_handle（从 Request::Response 提取）。
  Future<String> createSession(String sessionToken);

  /// BindShortcuts（每个 session 仅允许一次）。
  Future<void> bindShortcuts(
    String sessionHandle,
    List<PortalShortcutBinding> shortcuts,
  );

  /// 所有快捷键激活事件流（service 侧按 session + id 过滤）。
  Stream<PortalShortcutActivation> get onActivated;

  /// 关闭指定 session。
  Future<void> closeSession(String sessionHandle);

  /// 释放底层连接。
  Future<void> dispose();
}

/// 基于 package:dbus 的真实实现。
///
/// 遵循 xdg_desktop_portal 包的 XdgPortalRequest/XdgPortalSession 处理模式：
/// portal 方法返回的是 **Request 对象路径**，真正结果需订阅
/// `org.freedesktop.portal.Request::Response` 信号从 results 提取。
class DBusGlobalShortcutsBackend implements GlobalShortcutsBackend {
  DBusGlobalShortcutsBackend({DBusClient? client, Duration? timeout})
      : _client = client ?? DBusClient.session(),
        _timeout = timeout ?? const Duration(seconds: 2) {
    _portalObject = DBusRemoteObject(
      _client,
      name: 'org.freedesktop.portal.Desktop',
      path: DBusObjectPath('/org/freedesktop/portal/desktop'),
    );
  }

  final DBusClient _client;
  final Duration _timeout;
  late final DBusRemoteObject _portalObject;
  final _random = Random();
  final _usedTokens = <String>{};

  StreamController<PortalShortcutActivation>? _activatedController;
  StreamSubscription<DBusSignal>? _activatedSubscription;

  /// 生成唯一 handle/session token（对齐 xdg_desktop_portal 的 `dart<rand>` 约定）
  String _generateToken() {
    String token;
    do {
      token = 'nextalk${_random.nextInt(1 << 32)}';
    } while (_usedTokens.contains(token));
    _usedTokens.add(token);
    return token;
  }

  @override
  Future<int> getVersion() async {
    final value = await _portalObject
        .getProperty(
          HotkeyConstants.portalInterface,
          'version',
          signature: DBusSignature('u'),
        )
        .timeout(_timeout);
    return value.asUint32();
  }

  @override
  Future<String> createSession(String sessionToken) async {
    final results = await _sendRequest(() async {
      final options = <String, DBusValue>{
        'handle_token': DBusString(_generateToken()),
        'session_handle_token': DBusString(sessionToken),
      };
      final result = await _portalObject.callMethod(
        HotkeyConstants.portalInterface,
        'CreateSession',
        [DBusDict.stringVariant(options)],
        replySignature: DBusSignature('o'),
      );
      return result.returnValues[0].asObjectPath();
    });

    final handle = results['session_handle'];
    if (handle == null) {
      throw StateError('CreateSession Response 缺少 session_handle');
    }
    // session_handle 规范为字符串 's'；个别 backend 曾返回 object path，做兼容
    return handle is DBusObjectPath ? handle.value : handle.asString();
  }

  @override
  Future<void> bindShortcuts(
    String sessionHandle,
    List<PortalShortcutBinding> shortcuts,
  ) async {
    final shortcutStructs = shortcuts.map((s) {
      final vardict = <String, DBusValue>{
        'description': DBusString(s.description),
      };
      if (s.preferredTrigger != null) {
        vardict['preferred_trigger'] = DBusString(s.preferredTrigger!);
      }
      return DBusStruct([DBusString(s.id), DBusDict.stringVariant(vardict)]);
    }).toList();

    await _sendRequest(() async {
      final result = await _portalObject.callMethod(
        HotkeyConstants.portalInterface,
        'BindShortcuts',
        [
          DBusObjectPath(sessionHandle),
          DBusArray(DBusSignature('(sa{sv})'), shortcutStructs),
          const DBusString(''), // parent_window
          DBusDict.stringVariant(const {}),
        ],
        replySignature: DBusSignature('o'),
      );
      return result.returnValues[0].asObjectPath();
    });
  }

  @override
  Stream<PortalShortcutActivation> get onActivated {
    final existing = _activatedController;
    if (existing != null) return existing.stream;

    final controller = StreamController<PortalShortcutActivation>.broadcast(
      onCancel: () {
        _activatedSubscription?.cancel();
        _activatedSubscription = null;
      },
    );
    _activatedController = controller;

    // Activated(session_handle o, shortcut_id s, timestamp t, options a{sv})
    final signalStream = DBusSignalStream(
      _client,
      interface: HotkeyConstants.portalInterface,
      name: 'Activated',
      signature: DBusSignature('osta{sv}'),
    );
    _activatedSubscription = signalStream.listen((signal) {
      final sessionHandle = signal.values[0].asObjectPath().value;
      final shortcutId = signal.values[1].asString();
      controller.add(PortalShortcutActivation(sessionHandle, shortcutId));
    });

    return controller.stream;
  }

  @override
  Future<void> closeSession(String sessionHandle) async {
    try {
      final sessionObject = DBusRemoteObject(
        _client,
        name: 'org.freedesktop.portal.Desktop',
        path: DBusObjectPath(sessionHandle),
      );
      await sessionObject
          .callMethod('org.freedesktop.portal.Session', 'Close', [],
              replySignature: DBusSignature(''))
          .timeout(_timeout);
    } on DBusMethodResponseException {
      // session 可能已被 backend 关闭，忽略
    } on TimeoutException {
      // 关闭超时不阻塞退出
    }
  }

  @override
  Future<void> dispose() async {
    await _activatedSubscription?.cancel();
    _activatedSubscription = null;
    await _activatedController?.close();
    _activatedController = null;
    await _client.close();
  }

  /// 发送一个 portal Request 并等待其 Response 信号，返回 results。
  ///
  /// 严格遵循 XdgPortalRequest：先订阅 Response 信号，再调用方法拿到
  /// Request 路径，按路径匹配 Response。带超时兜底防止 backend 挂起。
  Future<Map<String, DBusValue>> _sendRequest(
    Future<DBusObjectPath> Function() send,
  ) async {
    final completer = Completer<Map<String, DBusValue>>();
    DBusObjectPath? requestPath;

    final responseStream = DBusSignalStream(
      _client,
      interface: 'org.freedesktop.portal.Request',
      name: 'Response',
      signature: DBusSignature('ua{sv}'),
    );
    final subscription = responseStream.listen((signal) {
      if (requestPath == null || signal.path != requestPath) return;
      if (completer.isCompleted) return;

      final code = signal.values[0].asUint32();
      final results = signal.values[1].asStringVariantDict();
      switch (code) {
        case 0:
          completer.complete(results);
          break;
        case 1:
          completer.completeError(
              StateError('Portal 请求被用户取消 (response=1)'));
          break;
        default:
          completer.completeError(
              StateError('Portal 请求失败 (response=$code)'));
      }
    });

    try {
      requestPath = await send();
      return await completer.future.timeout(_timeout);
    } finally {
      await subscription.cancel();
    }
  }
}

/// Portal 全局快捷键编排服务。
///
/// 生命周期：`register()` → 监听 Activated → `dispose()`。
/// 探测失败 / 注册失败均静默降级（返回结果供调用方决定），不抛异常、不阻塞启动。
class PortalHotkeyService {
  PortalHotkeyService({
    GlobalShortcutsBackend? backend,
    Future<void> Function()? onActivated,
    String shortcutId = HotkeyConstants.portalShortcutId,
    String preferredTrigger = HotkeyConstants.portalDefaultTrigger,
    String shortcutDescription = 'Toggle Nextalk voice input',
    int minVersion = 1,
  })  : _backend = backend ?? DBusGlobalShortcutsBackend(),
        _onActivated = onActivated ?? HotkeyController.instance.toggle,
        _shortcutId = shortcutId,
        _preferredTrigger = preferredTrigger,
        _shortcutDescription = shortcutDescription,
        _minVersion = minVersion;

  final GlobalShortcutsBackend _backend;
  final Future<void> Function() _onActivated;
  final String _shortcutId;
  final String _preferredTrigger;
  final String _shortcutDescription;
  final int _minVersion;

  bool _registered = false;
  bool _registerAttempted = false; // 单次运行禁止重复重绑
  String? _sessionHandle;
  String? _fallbackReason;
  StreamSubscription<PortalShortcutActivation>? _activatedSubscription;

  /// 是否已成功注册 Portal 快捷键
  bool get isRegistered => _registered;

  /// 降级原因（未降级时为 null）
  String? get fallbackReason => _fallbackReason;

  /// 探测 + 注册全流程。
  ///
  /// 幂等：单次运行只尝试一次（避免 GNOME 反复弹窗）。返回注册结果，
  /// 任何失败都记入 [_fallbackReason]，调用方据此决定是否走系统快捷键回退。
  Future<PortalRegistrationResult> register() async {
    if (_registerAttempted) {
      return _registered
          ? PortalRegistrationResult.registered
          : PortalRegistrationResult.failed;
    }
    _registerAttempted = true;

    // 1. 能力探测（AC1/AC4）
    final int version;
    try {
      version = await _backend.getVersion();
    } catch (e) {
      return _fallback(
        PortalRegistrationResult.unsupported,
        'GlobalShortcuts 接口不可用: $e',
      );
    }
    if (version < _minVersion) {
      return _fallback(
        PortalRegistrationResult.unsupported,
        'GlobalShortcuts 版本过低 (version=$version < $_minVersion)',
      );
    }

    // 2. CreateSession + BindShortcuts（AC1）
    try {
      _sessionHandle = await _backend.createSession(_shortcutId);
      await _backend.bindShortcuts(_sessionHandle!, [
        PortalShortcutBinding(
          id: _shortcutId,
          description: _shortcutDescription,
          preferredTrigger: _preferredTrigger,
        ),
      ]);
    } catch (e) {
      // 已开的 session 尽力清理，避免残留
      final handle = _sessionHandle;
      _sessionHandle = null;
      if (handle != null) {
        await _backend.closeSession(handle);
      }
      return _fallback(
        PortalRegistrationResult.failed,
        'Portal 注册失败: $e',
      );
    }

    // 3. 监听 Activated → 收敛到 HotkeyController（AC2）
    _activatedSubscription = _backend.onActivated.listen((event) {
      if (event.sessionHandle != _sessionHandle) return;
      if (event.shortcutId != _shortcutId) return;
      // 交给唯一业务入口，复用其 _isProcessing / 防抖竞态防护（AC6）
      _onActivated();
    });

    _registered = true;
    _fallbackReason = null;
    DiagnosticLogger.instance
        .info('PortalHotkey', '✅ Portal 全局快捷键注册成功 (version=$version)');
    return PortalRegistrationResult.registered;
  }

  PortalRegistrationResult _fallback(
    PortalRegistrationResult result,
    String reason,
  ) {
    _registered = false;
    _fallbackReason = reason;
    DiagnosticLogger.instance
        .warn('PortalHotkey', '⚠️ 降级到系统快捷键: $reason');
    return result;
  }

  /// 释放：关闭 session（AC7）与底层连接。
  Future<void> dispose() async {
    await _activatedSubscription?.cancel();
    _activatedSubscription = null;

    final handle = _sessionHandle;
    _sessionHandle = null;
    if (handle != null) {
      await _backend.closeSession(handle);
    }
    await _backend.dispose();

    _registered = false;
  }
}
