import 'dart:async';
import 'dart:ui';

import 'package:meta/meta.dart';
import 'package:screen_retriever/screen_retriever.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:window_manager/window_manager.dart';

import '../constants/window_constants.dart';

/// 存量坐标的恢复决策
///
/// [position] 为最终要应用的坐标，null 表示走默认位置计算。
/// [clearDirty] 仅在命中 `(0,0)` 脏值签名时为 true —— 越界坐标一律保留，
/// 因为显示器热插拔/会话切换时 `getAllDisplays()` 可能返回不完整集合而不抛异常，
/// 删除会不可恢复地丢掉副屏位置。
@immutable
class PositionRestoreDecision {
  const PositionRestoreDecision({this.position, this.clearDirty = false});

  final Offset? position;
  final bool clearDirty;

  @override
  bool operator ==(Object other) =>
      other is PositionRestoreDecision &&
      other.position == position &&
      other.clearDirty == clearDirty;

  @override
  int get hashCode => Object.hash(position, clearDirty);

  @override
  String toString() =>
      'PositionRestoreDecision(position: $position, clearDirty: $clearDirty)';
}

/// 进入程序化几何变更时如何处置已挂起的防抖保存
enum _PendingSavePolicy {
  /// 先落盘再变更 —— 挂起值是用户拖动结果（`setSize` 等场景）
  flush,

  /// 直接丢弃 —— 挂起值是窗口 map 时的 pre-map 伪坐标（恢复/默认定位场景）
  discard,
}

/// Flutter 原生窗口后端
/// SCP-002: 简化版 - 唯一的窗口后端实现
class FlutterWindowBackend with WindowListener {
  FlutterWindowBackend();

  /// 拖动过程中合并位置写入的防抖时长
  ///
  /// window_manager 的 Linux 端把 `configure-event` 映射为 `move` 事件、
  /// **从不发射 `moved`**（window_manager_plugin.cc 中只有 `_emit_event(plugin, "move")`），
  /// 所以 [onWindowMoved] 在 Linux 是死回调，保存时机只能挂在 [onWindowMove] 上，
  /// 由防抖把一次拖动的连续事件合并成一次写入。
  static const Duration savePositionDebounce = Duration(milliseconds: 400);

  /// 程序化改变窗口几何后的静置窗口
  ///
  /// `setSize`/`setPosition` 同样会触发 `configure-event`，而 WM 可能顺带平移窗口
  /// （实测：在 `4600,1300` 处 resize 后窗口被平移到 `4580,900`）。这段时间内到达的
  /// 移动事件不是用户意图，必须抑制保存，否则向导/展开态之后胶囊会永久停在错位处。
  ///
  /// 与 [savePositionDebounce] 同量级：WM 的平移在一两帧内完成，400ms 足够覆盖；
  /// 代价是紧接程序化变更后 400ms 内完成的极快拖动不被记住（之后的拖动照常生效）。
  static const Duration geometrySettleWindow = Duration(milliseconds: 400);

  SharedPreferences? _prefs;
  bool _isInitialized = false;
  bool _isVisible = false;

  /// 当前实际窗口尺寸
  ///
  /// 位置校验/钳位/默认位置都必须用它，不能一律按胶囊 400×120：
  /// 向导态 540×540 若按胶囊尺寸算底部对齐会溢出工作区，按钮点不到。
  Size _windowSize = WindowConstants.defaultWindowSize;

  Timer? _saveDebounceTimer;

  /// 保存串行化链：避免防抖回调与 `hide()` 的保存交叠后用旧读值覆盖新坐标
  Future<void> _saveChain = Future<void>.value();

  /// 正在进行的程序化几何变更嵌套层数
  ///
  /// 用计数而不是只用时间窗：恢复流程要等 `getAllDisplays()` 之类的通道往返，
  /// 耗时可能超过 [geometrySettleWindow]，纯时间窗会中途过期而漏掉伪坐标。
  int _programmaticDepth = 0;

  /// 程序化变更结束后的抑制尾巴（configure-event 在动作返回之后才陆续到达）
  DateTime? _suppressSaveUntil;

  final StreamController<void> _onMovedController =
      StreamController<void>.broadcast();

  String get name => 'FlutterWindowBackend';

  bool get isInitialized => _isInitialized;

  bool get isVisible => _isVisible;

  /// 当前用于位置计算的窗口尺寸
  @visibleForTesting
  Size get windowSize => _windowSize;

  /// 监听窗口移动结束事件
  Stream<void> get onMoved => _onMovedController.stream;

  Future<void> initialize() async {
    if (_isInitialized) return;

    await windowManager.ensureInitialized();
    _prefs = await SharedPreferences.getInstance();

    // 注册窗口事件监听
    windowManager.addListener(this);

    const windowOptions = WindowOptions(
      size: Size(WindowConstants.windowWidth, WindowConstants.windowHeight),
      center: true,
      skipTaskbar: true,
      titleBarStyle: TitleBarStyle.hidden,
      alwaysOnTop: true,
    );

    // 提前置位：_restorePosition() 经由保存守卫读取该标志
    _isInitialized = true;

    // ⚠️ window_manager 把 waitUntilReadyToShow 的回调声明为 VoidCallback 并
    // **不 await** 它，直接传 async 闭包会让 initialize() 在位置恢复完成前就返回。
    // 这里把回调产生的 Future 捞出来自己 await，保证 initialize() 返回时
    // 位置已恢复、窗口已就绪。
    Future<void>? readyToShow;
    await windowManager.waitUntilReadyToShow(windowOptions, () {
      readyToShow = _onReadyToShow();
    });
    await readyToShow;
  }

  Future<void> _onReadyToShow() async {
    await windowManager.setAsFrameless();
    await _restorePosition();
    await windowManager.show(inactive: true);
    await windowManager.hide();
    _isVisible = false;
  }

  Future<void> show() async {
    if (!_isInitialized) return;
    if (_isVisible) return;

    // 整个"map 窗口 → 恢复位置"期间都算程序化几何变更：
    // 实测窗口会先以 pre-map 伪坐标 (58,0) 出现并触发 configure-event，
    // 那不是用户位置，绝不能落盘
    await _runProgrammaticGeometryChange(
      () async {
        await windowManager.show(inactive: true);
        await windowManager.setSkipTaskbar(true);
        _isVisible = true;

        // 在窗口可见后再设置位置
        await Future.delayed(const Duration(milliseconds: 50));
        await _restorePosition();
      },
      pendingSave: _PendingSavePolicy.discard,
    );
  }

  Future<void> hide() async {
    if (!_isInitialized) return;
    if (!_isVisible) return;

    // 趁窗口仍可见把最新坐标落盘；之后 _isVisible 为 false，保存路径会被守卫挡掉
    await flushPendingSave();
    await windowManager.hide();
    _isVisible = false;
  }

  Future<void> setPosition(double x, double y) async {
    if (!_isInitialized) return;
    await _applyPosition(Offset(x, y));
  }

  Future<(double x, double y)?> getPosition() async {
    if (!_isInitialized) return null;
    final pos = await windowManager.getPosition();
    return (pos.dx, pos.dy);
  }

  /// 保存当前窗口位置
  ///
  /// 串行化：多个来源（防抖回调 / `hide()` / 退出 flush）并发调用时按序执行，
  /// 避免后发起者用更早的读值覆盖更新的坐标。内部吞掉异常，永不抛出。
  ///
  /// [force] 仅供 [flushPendingSave] 在"确有一次用户拖动等待落盘"时使用：
  /// 那是真实用户意图，即使正处在程序化抑制尾巴里也必须写入。
  Future<void> savePosition({bool force = false}) {
    final next = _saveChain.then((_) => _persistCurrentPosition(force: force));
    // 兜底：_persistCurrentPosition() 目前已把所有 await 包在 try 里、抛不出来，
    // 但一旦将来在 try 之外多写一行，未捕获的错误会永久毒化这条链，
    // 之后所有保存都被静默跳过 —— 位置记忆整条失效且无任何报错
    _saveChain = next.catchError((Object _) {});
    return next;
  }

  Future<void> _persistCurrentPosition({bool force = false}) async {
    if (!_isInitialized || _prefs == null) return;
    // 窗口不可见时读到的坐标不可信，跳过以免覆盖上一次有效坐标
    if (!_isVisible) return;
    // ⚠️ 抑制守卫必须在**写入路径**上，不能只放在 _schedulePositionSave()：
    // hide() → flushPendingSave() → savePosition() 完全绕过防抖，
    // 于是"程序化 setSize() 后在静置窗内 hide()"会把 WM 平移后的伪坐标
    // 当成用户位置写进 prefs（向导/展开态之后胶囊永久错位）。
    if (!force && _isSaveSuppressed) return;

    try {
      final position = await windowManager.getPosition();
      // 脏值守卫：(0,0) 是 Wayland 原生后端的伪值签名，写入会污染位置记忆
      if (!WindowConstants.shouldPersistPosition(position.dx, position.dy)) {
        return;
      }
      await _prefs!.setDouble(WindowConstants.positionXKey, position.dx);
      await _prefs!.setDouble(WindowConstants.positionYKey, position.dy);
    } catch (e) {
      // 读取坐标失败 → 静默跳过，不覆盖已有值
    }
  }

  Future<void> setSize(double width, double height) async {
    if (!_isInitialized) return;
    await _runProgrammaticGeometryChange(() async {
      await windowManager.setSize(Size(width, height));
      _windowSize = Size(width, height);
      // 变大后可能溢出工作区：400x120 → 540x540 若原本贴近工作区下沿，
      // 向导窗口会越过下边缘，按钮点不到且要等到下次重启才恢复
      await _clampIntoWorkArea();
    });
  }

  /// 按当前窗口尺寸把窗口回钳进工作区（尺寸变化后调用）
  ///
  /// 只在确实溢出时移动，不干扰用户已选好的位置。
  Future<void> _clampIntoWorkArea() async {
    try {
      final workAreas = await _currentWorkAreas();
      if (workAreas == null) return;

      final position = await windowManager.getPosition();
      if (WindowConstants.isValidPosition(
        position.dx,
        position.dy,
        workAreas: workAreas,
        size: _windowSize,
      )) {
        return;
      }

      final clamped = WindowConstants.clampToWorkAreas(
        position.dx,
        position.dy,
        workAreas,
        size: _windowSize,
      );
      if (clamped != null && clamped != position) {
        await windowManager.setPosition(clamped);
      }
    } catch (e) {
      // 显示器查询/定位失败 → 保持原位，不因回钳失败而破坏现状
    }
  }

  Future<void> setState(String state) async {
    // Flutter 窗口不直接处理状态，由 UI 层处理
  }

  Future<void> setText(String text) async {
    // Flutter 窗口不直接处理文本，由 UI 层处理
  }

  Future<void> resetPosition() async {
    if (_prefs != null) {
      await _prefs!.remove(WindowConstants.positionXKey);
      await _prefs!.remove(WindowConstants.positionYKey);
    }
    await _setDefaultPosition();
  }

  Future<void> startDragging() async {
    if (!_isInitialized) return;
    await windowManager.startDragging();
  }

  /// 立即落盘并取消挂起的防抖
  ///
  /// 退出路径必须真正等到写入完成：拖动后 400ms 内退出应用时，这是唯一的落盘机会。
  Future<void> flushPendingSave() async {
    // 有挂起的防抖 ⇒ 确实存在一次等待落盘的用户拖动，这是真实用户意图，
    // 即使正处在程序化抑制尾巴里也要写入（"进入抑制前先保住用户拖动"的顺序靠它成立）。
    // 没有挂起 ⇒ 无新东西可存，此时若正被抑制，当前坐标只是 WM 平移后的伪值，不能写。
    final hadPendingDrag = _saveDebounceTimer?.isActive ?? false;
    _saveDebounceTimer?.cancel();
    _saveDebounceTimer = null;
    await savePosition(force: hadPendingDrag);
  }

  Future<void> _restorePosition() async {
    if (_prefs == null) return;

    final x = _prefs!.getDouble(WindowConstants.positionXKey);
    final y = _prefs!.getDouble(WindowConstants.positionYKey);

    final decision = resolveRestorePosition(
      x,
      y,
      await _currentWorkAreas(),
      windowSize: _windowSize,
    );

    if (decision.clearDirty) {
      await _prefs!.remove(WindowConstants.positionXKey);
      await _prefs!.remove(WindowConstants.positionYKey);
    }

    final target = decision.position;
    if (target != null) {
      await _applyPosition(target);
      return;
    }

    await _setDefaultPosition();
  }

  /// 存量坐标的恢复决策（纯函数，便于单测）
  ///
  /// - 键缺失 → 走默认位置
  /// - `(0,0)` 脏值签名 / NaN / Infinity → 清键 + 走默认位置
  /// - 有效 → 原样恢复
  /// - 越界但已知显示器集合 → 钳位到最近工作区以保留用户意图，**不清键**
  /// - 越界且拿不到显示器集合 → 走默认位置，**不清键**（显示器齐全后原位置仍可用）
  @visibleForTesting
  static PositionRestoreDecision resolveRestorePosition(
    double? x,
    double? y,
    List<Rect>? workAreas, {
    Size windowSize = WindowConstants.defaultWindowSize,
  }) {
    if (x == null || y == null) return const PositionRestoreDecision();

    // 非有限值必须在钳位之前拦掉：NaN 让所有比较都为 false，
    // clampToWorkAreas 会静默选中第一个工作区、把窗口丢到任意角落。
    // 写路径的 shouldPersistPosition() 同样拒绝非有限值，读写两侧保持对称。
    if (!WindowConstants.shouldPersistPosition(x, y)) {
      return const PositionRestoreDecision(clearDirty: true);
    }

    if (WindowConstants.isValidPosition(
      x,
      y,
      workAreas: workAreas,
      size: windowSize,
    )) {
      return PositionRestoreDecision(position: Offset(x, y));
    }

    final clamped = WindowConstants.clampToWorkAreas(
      x,
      y,
      workAreas,
      size: windowSize,
    );
    // 钳位结果必须回校：目标工作区比窗口还小时 _clampAxis 只能贴到区间起点，
    // 窗口仍可能大部分在屏外，直接当最终位置返回会把用户丢到看不见的地方
    if (clamped != null &&
        WindowConstants.isValidPosition(
          clamped.dx,
          clamped.dy,
          workAreas: workAreas,
          size: windowSize,
        )) {
      return PositionRestoreDecision(position: clamped);
    }

    return const PositionRestoreDecision();
  }

  Future<void> _setDefaultPosition() async {
    await _runProgrammaticGeometryChange(
      () async {
        try {
          final primaryDisplay = await screenRetriever.getPrimaryDisplay();
          final workArea = workAreaOf(primaryDisplay);
          final target = WindowConstants.defaultPosition(
            workArea,
            size: _windowSize,
          );
          // 工作区尺寸非正 → 算不出可信位置；结果正好等于 (0,0) 会撞上脏值哨兵
          // （那个位置永远无法持久化），两种情况都退回 center()
          if (workArea.width > 0 &&
              workArea.height > 0 &&
              WindowConstants.shouldPersistPosition(target.dx, target.dy)) {
            await windowManager.setPosition(target);
            return;
          }
        } catch (e) {
          // workarea 查询失败 → 退回普通居中
        }

        await windowManager.center();
      },
      pendingSave: _PendingSavePolicy.discard,
    );
  }

  /// 当前所有显示器的工作区矩形（绝对坐标）；查询失败或结果为空时返回 null
  Future<List<Rect>?> _currentWorkAreas() async {
    try {
      final displays = await screenRetriever.getAllDisplays();
      if (displays.isEmpty) return null;
      return displays.map(workAreaOf).toList();
    } catch (e) {
      return null;
    }
  }

  /// 提取显示器工作区矩形（绝对坐标）
  ///
  /// `visiblePosition`/`visibleSize` 来自 `gdk_monitor_get_workarea`，已含显示器
  /// 偏移与顶栏/Dock 让位；缺失时退回 `size` 与零偏移。
  @visibleForTesting
  static Rect workAreaOf(Display display) {
    final origin = display.visiblePosition ?? Offset.zero;
    final size = display.visibleSize ?? display.size;
    return Rect.fromLTWH(origin.dx, origin.dy, size.width, size.height);
  }

  Future<void> _applyPosition(Offset position) async {
    await _runProgrammaticGeometryChange(
      () => windowManager.setPosition(position),
      // 恢复/默认定位是权威动作：此刻挂起的坐标只可能是窗口刚 map 出来的
      // pre-map 伪值（实测 show() 时窗口先出现在 (58,0) 才被移到目标位置），
      // 落盘它会用伪值覆盖用户真实位置，必须丢弃
      pendingSave: _PendingSavePolicy.discard,
    );
  }

  /// 执行程序化几何变更，期间抑制位置保存
  Future<void> _runProgrammaticGeometryChange(
    Future<void> Function() action, {
    _PendingSavePolicy pendingSave = _PendingSavePolicy.flush,
  }) async {
    if (_programmaticDepth == 0) {
      if (pendingSave == _PendingSavePolicy.flush) {
        // 先把用户拖动的结果落盘，再进入抑制窗口，避免用户位置被随后的平移吞掉
        await flushPendingSave();
      } else {
        _saveDebounceTimer?.cancel();
        _saveDebounceTimer = null;
      }
    }
    _programmaticDepth++;
    try {
      await action();
    } finally {
      _programmaticDepth--;
      // 动作返回之后 configure-event 才陆续到达，留一段时间尾巴
      _suppressSaveUntil = DateTime.now().add(geometrySettleWindow);
    }
  }

  bool get _isSaveSuppressed {
    if (_programmaticDepth > 0) return true;
    final until = _suppressSaveUntil;
    return until != null && DateTime.now().isBefore(until);
  }

  Future<void> dispose() async {
    await flushPendingSave();
    windowManager.removeListener(this);
    if (!_onMovedController.isClosed) {
      await _onMovedController.close();
    }
    _isInitialized = false;
  }

  // WindowListener 实现
  @override
  void onWindowMove() {
    // Linux 上唯一会触发的移动事件（configure-event），拖动后的保存时机就在这里
    _schedulePositionSave();
  }

  @override
  void onWindowMoved() {
    // window_manager 的 Linux 端从不发射 `moved`，此处仅作其他平台/上游修复后的兜底
    _schedulePositionSave();
  }

  /// 防抖保存位置：一次拖动的连续 move 事件只落盘一次
  void _schedulePositionSave() {
    // 程序化几何变更引发的移动不是用户意图，直接丢弃
    if (_isSaveSuppressed) return;

    _saveDebounceTimer?.cancel();
    _saveDebounceTimer = Timer(savePositionDebounce, () {
      _saveDebounceTimer = null;
      savePosition().then((_) {
        if (!_onMovedController.isClosed) {
          _onMovedController.add(null);
        }
      });
    });
  }

  @override
  void onWindowClose() {
    // WindowListener 回调签名是 void，无法被框架 await；
    // dispose() 内部的 flush 仍会串行完成写入
    dispose();
  }

  @override
  void onWindowFocus() {}

  @override
  void onWindowBlur() {}

  @override
  void onWindowMaximize() {}

  @override
  void onWindowUnmaximize() {}

  @override
  void onWindowMinimize() {}

  @override
  void onWindowRestore() {}

  @override
  void onWindowResize() {}

  @override
  void onWindowResized() {}

  @override
  void onWindowEnterFullScreen() {}

  @override
  void onWindowLeaveFullScreen() {}

  @override
  void onWindowEvent(String eventName) {}

  @override
  void onWindowDocked() {}

  @override
  void onWindowUndocked() {}
}
