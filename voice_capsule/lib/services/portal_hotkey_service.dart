import 'dart:async';
import 'dart:math';

import 'package:dbus/dbus.dart';
import 'package:meta/meta.dart';

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

  /// 用户在系统授权对话框中取消了绑定（response=1）——应回退，但允许后续重试
  cancelled,
}

/// 用户在系统授权/绑定对话框中取消（Portal Response code=1）。
///
/// 与 backend 报错区分：取消是用户主观选择，服务不应把它当作“不支持”而
/// 永久锁定，允许后续再次尝试注册。
class PortalUserCancelledException implements Exception {
  const PortalUserCancelledException();

  @override
  String toString() => 'PortalUserCancelledException: 用户取消了 Portal 快捷键绑定';
}

/// Portal 请求失败（Response code≥2），携带 results 供调用方细判。
///
/// 保留 results 是因为 xdg-desktop-portal-gnome 48.0 存在未初始化变量 bug
/// （上游 27511907 已修复）：静默授权绑定成功后仍回 response=2，但 results
/// 里带着已绑定的 shortcuts——调用方需要 results 才能识别这种"假失败"。
class PortalRequestFailedException implements Exception {
  final int code;
  final Map<String, DBusValue> results;

  const PortalRequestFailedException(this.code, this.results);

  @override
  String toString() => 'PortalRequestFailedException: Portal 请求失败 (response=$code)';
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
  DBusGlobalShortcutsBackend({
    DBusClient? client,
    Duration? timeout,
    Duration? interactiveTimeout,
  })  : _client = client ?? DBusClient.session(),
        _timeout = timeout ?? const Duration(seconds: 2),
        // 交互式请求（CreateSession/BindShortcuts）的 Response 只有在用户点掉
        // 系统授权对话框后才发出——探测用的 2s 短超时会把它必然误判为失败。
        // 首启用户往往不会立刻处理弹出的授权框（实测 60s 会超时锁定，用户
        // 稍后点"添加"也无法在本次会话生效）；GNOME 对话框会一直挂着等操作，
        // Response 在用户点按钮时必然发出，故放宽到 10 分钟——超时仅兜底
        // "backend 既不弹框也不回复"的异常平台。
        _interactiveTimeout =
            interactiveTimeout ?? timeout ?? const Duration(minutes: 10) {
    _portalObject = DBusRemoteObject(
      _client,
      name: 'org.freedesktop.portal.Desktop',
      path: DBusObjectPath('/org/freedesktop/portal/desktop'),
    );
  }

  final DBusClient _client;

  /// 非交互请求超时（version 探测、closeSession）——短，快速判定接口缺失。
  final Duration _timeout;

  /// 交互请求超时（CreateSession/BindShortcuts 等待用户操作授权框）——长。
  final Duration _interactiveTimeout;
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
    // xdg-desktop-portal 的 xdp_is_valid_token 只允许 [A-Za-z0-9_]——token 会
    // 拼进 session 对象路径。连字符等一律替换，否则 CreateSession 直接被
    // InvalidArgument ("Invalid token") 拒绝（shortcut id 无此限制，可保留连字符）。
    final safeToken = sessionToken.replaceAll(RegExp(r'[^A-Za-z0-9_]'), '_');
    final results = await _sendRequest(() async {
      final options = <String, DBusValue>{
        'handle_token': DBusString(_generateToken()),
        'session_handle_token': DBusString(safeToken),
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

    try {
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
    } on PortalRequestFailedException catch (e) {
      // xdg-desktop-portal-gnome 48.0（Debian 13 在售版本）成功路径漏赋
      // response（上游 27511907 修复）：静默授权绑定实际已生效（grab 成功、
      // ShortcutsChanged 已发出），却回 response=2。特征是 results 仍带
      // 非空 shortcuts——真失败路径 results 为空 vardict，可安全区分。
      if (!shortcutsActuallyBound(e.results, shortcuts)) rethrow;
    }
  }

  /// 判定 BindShortcuts 的"假失败"：results 携带的已绑定列表覆盖了全部
  /// 请求的 shortcut id 时视为绑定成功。
  @visibleForTesting
  static bool shortcutsActuallyBound(
    Map<String, DBusValue> results,
    List<PortalShortcutBinding> requested,
  ) {
    final bound = results['shortcuts'];
    if (bound is! DBusArray || bound.children.isEmpty) return false;
    final boundIds = bound.children
        .whereType<DBusStruct>()
        .map((s) => s.children.isNotEmpty ? s.children[0] : null)
        .whereType<DBusString>()
        .map((s) => s.value)
        .toSet();
    return requested.every((s) => boundIds.contains(s.id));
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
      sender: 'org.freedesktop.portal.Desktop',
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
      sender: 'org.freedesktop.portal.Desktop',
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
          completer.completeError(const PortalUserCancelledException());
          break;
        default:
          completer.completeError(PortalRequestFailedException(code, results));
      }
    });

    try {
      requestPath = await send();
      return await completer.future.timeout(_interactiveTimeout);
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

    // 1. 能力探测（AC1/AC4）
    final int version;
    try {
      version = await _backend.getVersion();
    } catch (e) {
      // 探测失败即视为已尝试（接口缺失不会因重试而改变）
      _registerAttempted = true;
      return _fallback(
        PortalRegistrationResult.unsupported,
        'GlobalShortcuts 接口不可用: $e',
      );
    }
    if (version < _minVersion) {
      _registerAttempted = true;
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
    } on PortalUserCancelledException {
      // 用户主动取消：清理 session，但**不锁定** _registerAttempted，
      // 允许后续再次尝试注册（决策 2A）。
      final handle = _sessionHandle;
      _sessionHandle = null;
      if (handle != null) {
        await _backend.closeSession(handle);
      }
      _registered = false;
      _fallbackReason = '用户取消了 Portal 快捷键绑定';
      DiagnosticLogger.instance
          .info('PortalHotkey', 'ℹ️ 用户取消绑定，暂用系统快捷键（可重试）');
      return PortalRegistrationResult.cancelled;
    } catch (e) {
      // 非取消类失败：视为已尝试，避免重复重绑骚扰（GNOME 反复弹窗）
      _registerAttempted = true;
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

    _registerAttempted = true;

    // 3. 监听 Activated → 收敛到 HotkeyController（AC2）
    _activatedSubscription = _backend.onActivated.listen((event) {
      if (event.sessionHandle != _sessionHandle) return;
      if (event.shortcutId != _shortcutId) return;
      // 交给唯一业务入口，复用其 _isProcessing 重入保护（AC6）。
      // fire-and-forget：显式吞掉并记录异常，避免逃逸为未处理的异步错误。
      unawaited(_onActivated().catchError((Object e) {
        DiagnosticLogger.instance
            .warn('PortalHotkey', 'toggle 执行异常: $e');
      }));
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
