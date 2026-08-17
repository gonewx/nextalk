import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:voice_capsule/constants/window_constants.dart';
import 'package:voice_capsule/services/flutter_window_backend.dart';
import 'package:voice_capsule/services/window_service.dart';
import 'package:window_manager/window_manager.dart';

/// FlutterWindowBackend 真实接线测试
///
/// 与纯谓词测试的区别：这里把 `window_manager` / `screen_retriever` 的
/// MethodChannel 打桩成一个有状态的假窗口管理器，走 [FlutterWindowBackend] 的
/// 真实代码路径（initialize / show / hide / onWindowMove / setSize / dispose），
/// 断言 SharedPreferences 里的最终内容。
///
/// 可失败性：把 `onWindowMove()` 改回空实现，本文件的
/// "连续多次 onWindowMove 只落盘一次且为最后坐标" 与
/// "防抖窗口内退出仍落盘" 两组测试会失败。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const wmChannel = MethodChannel('window_manager');
  const srChannel = MethodChannel('dev.leanflutter.plugins/screen_retriever');

  // 实测的双屏布局：左屏 0,0 2560x1440(workarea 0,32 2560x1408)、
  // 主屏 2560,0 2560x1440(workarea 2618,32 2502x1408)
  const secondaryWorkArea = Rect.fromLTWH(0, 32, 2560, 1408);
  const primaryWorkArea = Rect.fromLTWH(2618, 32, 2502, 1408);

  /// 由常量推导期望值，而不是硬编码几何算术结果：
  /// 常量变更时以"意图被违反"而非"数字不对"的形式失败
  final expectedDefaultPosition = WindowConstants.defaultPosition(
    primaryWorkArea,
  );

  Map<String, dynamic> displayJson(String id, Rect geometry, Rect workArea) => {
        'id': id,
        'name': id,
        'size': {'width': geometry.width, 'height': geometry.height},
        'visiblePosition': {'dx': workArea.left, 'dy': workArea.top},
        'visibleSize': {'width': workArea.width, 'height': workArea.height},
        'scaleFactor': 1.0,
      };

  /// 有状态的假窗口管理器
  late Rect bounds;
  late bool nativeVisible;
  late List<String> calls;

  /// 模拟 WM 在 resize 时顺带平移窗口（实测 4600,1300 → 4580,900）
  late Offset? resizeInducedShift;

  /// 模拟窗口 map 时先出现在 pre-map 伪坐标并发出 configure-event（实测 (58,0)）
  late Offset? mapPseudoPosition;

  /// map 时发出的 configure-event 回调（由测试接到 backend.onWindowMove）
  void Function()? onMapConfigureEvent;

  void installStubs() {
    bounds = const Rect.fromLTWH(
      0,
      0,
      WindowConstants.windowWidth,
      WindowConstants.windowHeight,
    );
    nativeVisible = false;
    calls = <String>[];
    resizeInducedShift = null;
    mapPseudoPosition = null;

    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(wmChannel, (MethodCall call) async {
      calls.add(call.method);
      switch (call.method) {
        case 'getBounds':
          return <String, dynamic>{
            'x': bounds.left,
            'y': bounds.top,
            'width': bounds.width,
            'height': bounds.height,
          };
        case 'setBounds':
          final args = (call.arguments as Map).cast<String, dynamic>();
          final width = (args['width'] as num?)?.toDouble() ?? bounds.width;
          final height = (args['height'] as num?)?.toDouble() ?? bounds.height;
          var left = (args['x'] as num?)?.toDouble() ?? bounds.left;
          var top = (args['y'] as num?)?.toDouble() ?? bounds.top;
          final isResize = args['width'] != null || args['height'] != null;
          if (isResize && resizeInducedShift != null) {
            left = resizeInducedShift!.dx;
            top = resizeInducedShift!.dy;
          }
          bounds = Rect.fromLTWH(left, top, width, height);
          return null;
        case 'isVisible':
          return nativeVisible;
        case 'show':
          nativeVisible = true;
          // 真实行为：窗口 map 时先落在 pre-map 伪坐标，并发出 configure-event
          if (mapPseudoPosition != null) {
            bounds = Rect.fromLTWH(
              mapPseudoPosition!.dx,
              mapPseudoPosition!.dy,
              bounds.width,
              bounds.height,
            );
            onMapConfigureEvent?.call();
          }
          return null;
        case 'hide':
          nativeVisible = false;
          return null;
        case 'isFullScreen':
        case 'isMaximized':
        case 'isMinimized':
        case 'isPreventClose':
          return false;
        default:
          // ensureInitialized / waitUntilReadyToShow / setAsFrameless /
          // setTitleBarStyle / setAlignment / setAlwaysOnTop / setSkipTaskbar /
          // startDragging ... 一律成功
          return null;
      }
    });

    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(srChannel, (MethodCall call) async {
      switch (call.method) {
        case 'getPrimaryDisplay':
          return displayJson(
            'primary',
            const Rect.fromLTWH(2560, 0, 2560, 1440),
            primaryWorkArea,
          );
        case 'getAllDisplays':
          return <String, dynamic>{
            'displays': [
              displayJson(
                'secondary',
                const Rect.fromLTWH(0, 0, 2560, 1440),
                secondaryWorkArea,
              ),
              displayJson(
                'primary',
                const Rect.fromLTWH(2560, 0, 2560, 1440),
                primaryWorkArea,
              ),
            ],
          };
        case 'getCursorScreenPoint':
          return <String, dynamic>{'dx': 3000.0, 'dy': 700.0};
        default:
          return null;
      }
    });
  }

  void removeStubs() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      ..setMockMethodCallHandler(wmChannel, null)
      ..setMockMethodCallHandler(srChannel, null);
  }

  /// 读取 prefs 中的位置键
  Future<(double?, double?)> readStored() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.reload();
    return (
      prefs.getDouble(WindowConstants.positionXKey),
      prefs.getDouble(WindowConstants.positionYKey),
    );
  }

  /// 模拟用户拖动：WM 把窗口移到新位置，随后发来 configure-event
  void simulateUserDrag(FlutterWindowBackend backend, Offset to) {
    bounds = Rect.fromLTWH(to.dx, to.dy, bounds.width, bounds.height);
    backend.onWindowMove();
  }

  /// 模拟用户拖动，但事件**经 window_manager 插件的真实分发路径**投递
  ///
  /// 走 `window_manager` 通道的入站 `onEvent`，由插件自己遍历已注册监听者。
  /// 这条路径能捕获 `windowManager.addListener(this)` 被删除的回归 ——
  /// 直接调 `backend.onWindowMove()` 会绕过注册，测不出来。
  Future<void> simulateUserDragViaPlugin(Offset to) async {
    bounds = Rect.fromLTWH(to.dx, to.dy, bounds.width, bounds.height);
    await TestDefaultBinaryMessengerBinding
        .instance.defaultBinaryMessenger
        .handlePlatformMessage(
      wmChannel.name,
      wmChannel.codec.encodeMethodCall(
        const MethodCall('onEvent', {'eventName': 'move'}),
      ),
      (_) {},
    );
  }

  /// 等到防抖必然已经触发
  Future<void> settleDebounce() => Future<void>.delayed(
        FlutterWindowBackend.savePositionDebounce +
            const Duration(milliseconds: 150),
      );

  /// 等到程序化几何变更的抑制窗口结束
  Future<void> settleSuppression() => Future<void>.delayed(
        FlutterWindowBackend.geometrySettleWindow +
            const Duration(milliseconds: 100),
      );

  late FlutterWindowBackend backend;
  FlutterWindowBackend? activeBackend;

  Future<FlutterWindowBackend> createBackend(
    Map<String, Object> initialPrefs,
  ) async {
    SharedPreferences.setMockInitialValues(initialPrefs);
    installStubs();
    backend = FlutterWindowBackend();
    activeBackend = backend;
    await backend.initialize();
    return backend;
  }

  tearDown(() async {
    // 必须 dispose：否则挂起的防抖 timer 会跨用例存活，
    // 在打桩已被移除后触发 MethodChannel 调用
    final pending = activeBackend;
    activeBackend = null;
    if (pending != null && pending.isInitialized) {
      await pending.dispose();
    }
    onMapConfigureEvent = null;
    removeStubs();
  });

  group('事件订阅注册 (真实接线)', () {
    test('initialize() 必须把自己注册为 window_manager 监听者', () async {
      final before = windowManager.listeners.length;
      await createBackend({});

      expect(
        windowManager.listeners, contains(backend),
        reason: '缺少 windowManager.addListener(this) 时应用收不到任何 move 事件，'
            '位置永不保存',
      );
      expect(windowManager.listeners.length, before + 1);
    });

    test('dispose() 必须注销监听者，避免跨实例泄漏', () async {
      await createBackend({});
      expect(windowManager.listeners, contains(backend));

      await backend.dispose();
      expect(windowManager.listeners, isNot(contains(backend)));
    });

    test('经插件真实分发的 move 事件能落盘（覆盖注册链路）', () async {
      await createBackend({});
      await backend.show();
      await settleSuppression();

      // 不直接调 backend.onWindowMove()，而是从通道投递 onEvent，
      // 由 window_manager 自己分发给已注册的监听者
      await simulateUserDragViaPlugin(const Offset(3800, 1180));
      await settleDebounce();

      expect(
        await readStored(),
        (3800.0, 1180.0),
        reason: '事件必须经由 addListener 注册的分发路径抵达 backend',
      );
    });
  });

  group('拖动后位置记忆 (真实接线)', () {
    test('连续多次 onWindowMove 只落盘一次，且为最后坐标', () async {
      await createBackend({
        'flutter.${WindowConstants.positionXKey}': 3000.0,
        'flutter.${WindowConstants.positionYKey}': 1000.0,
      });
      await backend.show();
      await settleSuppression();

      // 只统计这段窗口内的 getBounds —— savePosition 是此刻唯一的调用方
      calls.clear();

      simulateUserDrag(backend, const Offset(3100, 1100));
      simulateUserDrag(backend, const Offset(3200, 1200));
      simulateUserDrag(backend, const Offset(3297, 1036));
      await settleDebounce();

      final saveReads = calls.where((c) => c == 'getBounds').length;
      expect(saveReads, 1, reason: '一次拖动的连续 move 事件必须合并为一次写入');

      expect(await readStored(), (3297.0, 1036.0));
    });

    test('防抖窗口内退出应用，拖动后的位置仍然落盘', () async {
      await createBackend({});
      await backend.show();
      await settleSuppression();

      simulateUserDrag(backend, const Offset(3400, 1150));
      // 不等防抖，立刻退出
      await backend.dispose();

      expect(await readStored(), (3400.0, 1150.0));
    });

    test('hide() 返回后 prefs 已含隐藏前的最新坐标', () async {
      await createBackend({});
      await backend.show();
      await settleSuppression();

      simulateUserDrag(backend, const Offset(3500, 1240));
      // 不等防抖直接隐藏
      await backend.hide();

      expect(await readStored(), (3500.0, 1240.0));
      expect(backend.isVisible, isFalse);
    });
  });

  group('保存守卫 (真实接线)', () {
    test('隐藏态调用 savePosition() 不改动 prefs', () async {
      await createBackend({});
      await backend.show();
      await settleSuppression();
      simulateUserDrag(backend, const Offset(3600, 1300));
      await backend.hide();
      final saved = await readStored();

      // 隐藏后窗口坐标读数不可信（Wayland 下会退化为 0,0）
      bounds = const Rect.fromLTWH(
        0,
        0,
        WindowConstants.windowWidth,
        WindowConstants.windowHeight,
      );
      await backend.savePosition();

      expect(await readStored(), saved);
      expect(saved, (3600.0, 1300.0));
    });

    test('隐藏态的移动事件也不会写入', () async {
      await createBackend({});
      await backend.show();
      await settleSuppression();
      simulateUserDrag(backend, const Offset(3700, 1200));
      await backend.hide();

      simulateUserDrag(backend, const Offset(0, 0));
      await settleDebounce();

      expect(await readStored(), (3700.0, 1200.0));
    });
  });

  group('程序化几何变更不污染位置记忆 (真实接线)', () {    test('setSize() 引发的 WM 平移不被当成用户位置', () async {
      await createBackend({});
      await backend.show();
      await settleSuppression();

      simulateUserDrag(backend, const Offset(4600, 1300));
      await settleDebounce();
      expect(await readStored(), (4600.0, 1300.0), reason: '前置条件：用户位置已落盘');

      // 实测行为：resize 后 WM 把窗口平移到 4580,900
      resizeInducedShift = const Offset(4580, 900);
      await backend.setSize(
        WindowConstants.initWizardWidth,
        WindowConstants.initWizardHeight,
      );
      // 真实环境里 resize 之后 configure-event 才到达
      backend.onWindowMove();
      await settleDebounce();

      expect(
        await readStored(),
        (4600.0, 1300.0),
        reason: '程序化 resize 造成的平移不是用户意图，不得覆盖已记录的位置',
      );
    });

    test('setSize() 后窗口尺寸参与后续位置计算', () async {
      await createBackend({});
      await backend.setSize(
        WindowConstants.initWizardWidth,
        WindowConstants.initWizardHeight,
      );

      expect(
        backend.windowSize,
        const Size(
          WindowConstants.initWizardWidth,
          WindowConstants.initWizardHeight,
        ),
      );
    });

    test('show() 时窗口 map 到 pre-map 伪坐标，该伪坐标不得写入 prefs', () async {
      // 实测缺陷：show() 时窗口先出现在 (58,0) 并触发 configure-event，
      // 若把它当用户位置落盘，prefs 会被伪值覆盖（窗口在 3669,1240、prefs 却是 58,0）
      await createBackend({
        'flutter.${WindowConstants.positionXKey}': 3297.0,
        'flutter.${WindowConstants.positionYKey}': 1036.0,
      });

      mapPseudoPosition = const Offset(58, 0);
      onMapConfigureEvent = () => backend.onWindowMove();

      await backend.show();
      await settleDebounce();

      expect(
        await readStored(),
        (3297.0, 1036.0),
        reason: 'pre-map 伪坐标 (58,0) 绝不能覆盖用户位置',
      );
      expect(bounds.topLeft, const Offset(3297, 1036));
    });

    test('存量脏值 + pre-map 伪坐标：不得把伪坐标写回 prefs', () async {
      await createBackend({
        'flutter.${WindowConstants.positionXKey}': 0.0,
        'flutter.${WindowConstants.positionYKey}': 0.0,
      });

      mapPseudoPosition = const Offset(58, 0);
      onMapConfigureEvent = () => backend.onWindowMove();

      await backend.show();
      await settleDebounce();

      // 脏值键被清除，且没有被 (58,0) 顶替
      expect(await readStored(), (null, null));
      expect(bounds.topLeft, expectedDefaultPosition);
    });

    test('setSize() 后在静置窗内 hide()：WM 平移后的伪坐标不得落盘', () async {
      await createBackend({});
      await backend.show();
      await settleSuppression();

      simulateUserDrag(backend, const Offset(4600, 1300));
      await settleDebounce();
      expect(await readStored(), (4600.0, 1300.0), reason: '前置条件：用户位置已落盘');

      // 程序化 resize，WM 顺带把窗口平移到 4580,900
      resizeInducedShift = const Offset(4580, 900);
      await backend.setSize(
        WindowConstants.windowWidth,
        WindowConstants.windowHeightExpanded,
      );

      // 关键：不等静置窗结束就 hide() —— 这条路径完全绕过防抖，
      // 直达 flushPendingSave() → savePosition() → 写入
      await backend.hide();

      expect(
        await readStored(),
        (4600.0, 1300.0),
        reason: '抑制守卫必须在写入路径上，否则 hide() 会把 WM 平移坐标当用户位置',
      );
    });

    test('拖动后立刻 setSize()：用户位置仍被保住（抑制不误伤真实拖动）', () async {
      await createBackend({});
      await backend.show();
      await settleSuppression();

      // 拖动后不等防抖就触发程序化 resize
      simulateUserDrag(backend, const Offset(2700, 600));
      resizeInducedShift = const Offset(2680, 400);
      await backend.setSize(
        WindowConstants.windowWidth,
        WindowConstants.windowHeightExpanded,
      );

      expect(
        await readStored(),
        (2700.0, 600.0),
        reason: '进入抑制前必须先落盘挂起的用户拖动，这个顺序不能被守卫破坏',
      );
    });

    test('setSize() 变大后溢出工作区时按新尺寸回钳', () async {
      await createBackend({});
      await backend.show();
      await settleSuppression();

      // 贴近主屏工作区下沿：400x120 合法，540x540 会越过下边缘
      final nearBottom = Offset(
        primaryWorkArea.left + 100,
        primaryWorkArea.bottom - WindowConstants.windowHeight - 10,
      );
      simulateUserDrag(backend, nearBottom);
      await settleDebounce();

      await backend.setSize(
        WindowConstants.initWizardWidth,
        WindowConstants.initWizardHeight,
      );

      // 回钳后向导窗口必须完整落在工作区内，按钮可点
      expect(
        bounds.bottom,
        lessThanOrEqualTo(primaryWorkArea.bottom),
        reason: '向导窗口下沿不得越过工作区下边缘，否则按钮点不到',
      );
      expect(
        WindowConstants.isValidPosition(
          bounds.left,
          bounds.top,
          workAreas: [secondaryWorkArea, primaryWorkArea],
          size: backend.windowSize,
        ),
        isTrue,
      );
      // 用户原位置不被回钳动作覆盖
      expect(await readStored(), (nearBottom.dx, nearBottom.dy));
    });
  });

  group('存量脏值恢复 (真实接线)', () {    test('(0,0) 被清键，并把窗口移到工作区底部居中', () async {
      await createBackend({
        'flutter.${WindowConstants.positionXKey}': 0.0,
        'flutter.${WindowConstants.positionYKey}': 0.0,
      });

      // initialize() 内部已跑过一次恢复流程
      expect(await readStored(), (null, null), reason: '(0,0) 脏值必须被清除');
      expect(bounds.topLeft, expectedDefaultPosition);
    });

    test('有效存量坐标被原样恢复，键不被动', () async {
      await createBackend({
        'flutter.${WindowConstants.positionXKey}': 3297.0,
        'flutter.${WindowConstants.positionYKey}': 1036.0,
      });

      expect(bounds.topLeft, const Offset(3297, 1036));
      expect(await readStored(), (3297.0, 1036.0));
    });

    test('越界坐标被钳位到最近工作区，且不删键', () async {
      // 远在所有显示器右下方
      await createBackend({
        'flutter.${WindowConstants.positionXKey}': 9000.0,
        'flutter.${WindowConstants.positionYKey}': 5000.0,
      });

      final stored = await readStored();
      expect(stored, (9000.0, 5000.0), reason: '越界坐标不得从 prefs 删除');

      final clamped = WindowConstants.clampToWorkAreas(
        9000,
        5000,
        [secondaryWorkArea, primaryWorkArea],
      );
      expect(bounds.topLeft, clamped);
      expect(
        WindowConstants.isValidPosition(
          bounds.left,
          bounds.top,
          workAreas: [secondaryWorkArea, primaryWorkArea],
        ),
        isTrue,
      );
    });

    test('prefs 无位置键时落到工作区底部居中', () async {
      await createBackend({});

      expect(bounds.topLeft, expectedDefaultPosition);
      // 底部居中必须落在主显示器内，而不是相邻显示器
      expect(
        WindowConstants.isValidPosition(
          bounds.left,
          bounds.top,
          workAreas: [primaryWorkArea],
        ),
        isTrue,
      );
    });

    test('prefs 存有 NaN 时视为脏值清键，不被钳到任意角落', () async {
      await createBackend({
        'flutter.${WindowConstants.positionXKey}': double.nan,
        'flutter.${WindowConstants.positionYKey}': 500.0,
      });

      expect(await readStored(), (null, null), reason: '非有限值必须与 (0,0) 同样清键');
      expect(
        bounds.topLeft,
        expectedDefaultPosition,
        reason: 'NaN 让所有比较为 false，若不早拦会被钳到第一个工作区的角落',
      );
    });

    test('prefs 存有 Infinity 时同样视为脏值清键', () async {
      await createBackend({
        'flutter.${WindowConstants.positionXKey}': double.infinity,
        'flutter.${WindowConstants.positionYKey}': double.negativeInfinity,
      });

      expect(await readStored(), (null, null));
      expect(bounds.topLeft, expectedDefaultPosition);
    });
  });

  group('退出链落盘 (WindowService 层)', () {
    // ⚠️ 真正保证退出前落盘的是两处 await：
    //   tray_service.dart  → await WindowService.instance.dispose()
    //   window_service.dart→ Future<void> dispose() { await _backend?.dispose(); }
    // 直接调 backend.dispose() 的测试覆盖不到这一层 —— 任一处 await 被去掉，
    // "拖动后立刻退出丢位置"会静默复现而全部测试仍绿。
    tearDown(() async {
      if (WindowService.instance.isInitialized) {
        await WindowService.instance.dispose();
      }
    });

    test('WindowService.dispose() 必须 await 后端 flush，落盘拖动后的位置', () async {
      SharedPreferences.setMockInitialValues({});
      installStubs();
      activeBackend = null; // 本组由 WindowService 持有后端

      await WindowService.instance.initialize();
      await WindowService.instance.show();
      await settleSuppression();

      // 拖动（经插件真实分发），不等防抖直接退出
      await simulateUserDragViaPlugin(const Offset(3900, 1210));
      await WindowService.instance.dispose();

      expect(
        await readStored(),
        (3900.0, 1210.0),
        reason: 'dispose() 未 await 后端 flush 时，防抖窗口内退出会丢掉位置',
      );
      expect(WindowService.instance.isInitialized, isFalse);
    });

    test('WindowService.dispose() 返回的 Future 完成后写入已确定', () async {
      SharedPreferences.setMockInitialValues({});
      installStubs();
      activeBackend = null;

      await WindowService.instance.initialize();
      await WindowService.instance.show();
      await settleSuppression();
      await simulateUserDragViaPlugin(const Offset(3100, 980));

      // 模拟 tray_service._exitApp() 的调用形态：await 之后立即 exit(0)，
      // 因此 await 返回时写入必须已经完成，不能只是"已发起"
      final disposal = WindowService.instance.dispose();
      expect(disposal, isA<Future<void>>());
      await disposal;

      expect(await readStored(), (3100.0, 980.0));
    });
  });
}
