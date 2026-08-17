import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:screen_retriever/screen_retriever.dart';
import 'package:voice_capsule/constants/window_constants.dart';
import 'package:voice_capsule/services/flutter_window_backend.dart';

/// 位置算法的纯谓词测试
///
/// ⚠️ 这些测试只覆盖决策函数，对"拖动后位置记忆"这条链路**没有**保护力
/// （实测：把 onWindowMove() 改回空实现，纯谓词测试全绿）。
/// 接线保护在 test/services/flutter_window_backend_wiring_test.dart。
void main() {
  // 实测几何：主屏 geometry = 2560,0 2560x1440，workarea = 2618,32 2502x1408
  const primaryWorkArea = Rect.fromLTWH(2618, 32, 2502, 1408);
  const secondaryWorkArea = Rect.fromLTWH(0, 32, 2560, 1408);
  const bothWorkAreas = [secondaryWorkArea, primaryWorkArea];
  const wizardSize = Size(
    WindowConstants.initWizardWidth,
    WindowConstants.initWizardHeight,
  );

  group('WindowConstants.defaultPosition', () {
    test('按工作区绝对坐标算底部居中（含显示器偏移）', () {
      final position = WindowConstants.defaultPosition(primaryWorkArea);

      // x = 2618 + (2502-400)/2 = 3669、y = 32 + 1408 - 120 - 80 = 1240
      expect(position.dx, 3669.0);
      expect(position.dy, 1240.0);
    });

    test('结果落在主显示器内，而不是相邻显示器上', () {
      final position = WindowConstants.defaultPosition(primaryWorkArea);

      expect(
        WindowConstants.isValidPosition(
          position.dx,
          position.dy,
          workAreas: [primaryWorkArea],
        ),
        isTrue,
      );
      expect(
        WindowConstants.isValidPosition(
          position.dx,
          position.dy,
          workAreas: [secondaryWorkArea],
        ),
        isFalse,
      );
    });

    test('忽略显示器偏移的旧算法会落到左侧显示器（回归护栏）', () {
      const legacyX = (2560.0 - WindowConstants.windowWidth) / 2;
      expect(legacyX, 1080.0);
      expect(
        WindowConstants.isValidPosition(
          legacyX,
          1240,
          workAreas: [primaryWorkArea],
        ),
        isFalse,
      );
    });

    test('窗口下沿距工作区底部恰为 defaultBottomMargin', () {
      final position = WindowConstants.defaultPosition(primaryWorkArea);

      expect(
        primaryWorkArea.bottom -
            (position.dy + WindowConstants.windowHeight),
        WindowConstants.defaultBottomMargin,
      );
      expect(position.dy, greaterThanOrEqualTo(primaryWorkArea.top));
    });

    test('向导尺寸 540x540 按自身尺寸计算，不溢出工作区', () {
      final position = WindowConstants.defaultPosition(
        primaryWorkArea,
        size: wizardSize,
      );

      expect(position.dx, 2618 + (2502 - 540) / 2);
      expect(position.dy, 32 + 1408 - 540 - 80);
      // 完整落在工作区内
      expect(position.dx, greaterThanOrEqualTo(primaryWorkArea.left));
      expect(
        position.dx + wizardSize.width,
        lessThanOrEqualTo(primaryWorkArea.right),
      );
      expect(
        position.dy + wizardSize.height,
        lessThanOrEqualTo(primaryWorkArea.bottom),
      );
    });

    test('按胶囊尺寸给向导定位会溢出工作区（(g) 的回归护栏）', () {
      // 用错尺寸的后果：底部对齐按 120 高算，540 高的窗口会越过工作区下沿
      final wrong = WindowConstants.defaultPosition(primaryWorkArea);
      expect(
        wrong.dy + wizardSize.height,
        greaterThan(primaryWorkArea.bottom),
      );
    });

    test('工作区小于窗口时钳到左上角，不产生负坐标', () {
      const tiny = Rect.fromLTWH(100, 50, 320, 100);
      final position = WindowConstants.defaultPosition(tiny);

      expect(position.dx, 100.0);
      expect(position.dy, 50.0);
    });
  });

  group('WindowConstants.shouldPersistPosition', () {
    test('拒绝 (0,0) 脏值签名', () {
      expect(WindowConstants.isDirtyLegacyPosition(0, 0), isTrue);
      expect(WindowConstants.shouldPersistPosition(0, 0), isFalse);
    });

    test('单轴为 0 不是脏值', () {
      expect(WindowConstants.shouldPersistPosition(0, 1), isTrue);
      expect(WindowConstants.shouldPersistPosition(1, 0), isTrue);
    });

    test('拒绝非有限值', () {
      expect(WindowConstants.shouldPersistPosition(double.nan, 1), isFalse);
      expect(WindowConstants.shouldPersistPosition(1, double.infinity), isFalse);
    });
  });

  group('WindowConstants.isValidPosition', () {
    test('(0,0) 一律无效，阻断存量脏值复活', () {
      expect(WindowConstants.isValidPosition(0, 0), isFalse);
      expect(
        WindowConstants.isValidPosition(0, 0, workAreas: bothWorkAreas),
        isFalse,
      );
    });

    test('落在任一显示器工作区内的坐标有效', () {
      expect(
        WindowConstants.isValidPosition(3297, 1036, workAreas: bothWorkAreas),
        isTrue,
      );
      expect(
        WindowConstants.isValidPosition(500, 200, workAreas: bothWorkAreas),
        isTrue,
      );
    });

    test('跨两台相邻显示器摆放仍有效（累计面积，不是单屏面积）', () {
      // 窗口 400 宽跨在 x=2400..2800：左屏占 160(40%)、主屏占 182(45.5%)，
      // 任一单屏都不足半数，累计 85.5% 达标
      const x = 2400.0;
      expect(
        WindowConstants.visibleAreaRatio(x, 700, [secondaryWorkArea]),
        lessThan(WindowConstants.minVisibleAreaRatio),
      );
      expect(
        WindowConstants.visibleAreaRatio(x, 700, [primaryWorkArea]),
        lessThan(WindowConstants.minVisibleAreaRatio),
      );
      // 累计可见面积达标 → 必须判为有效
      expect(
        WindowConstants.visibleAreaRatio(x, 700, bothWorkAreas),
        greaterThanOrEqualTo(WindowConstants.minVisibleAreaRatio),
      );
      expect(
        WindowConstants.isValidPosition(x, 700, workAreas: bothWorkAreas),
        isTrue,
      );
      // 按"单屏 ≥50%"判定会误杀这个位置（(a) 的回归护栏）
      expect(
        bothWorkAreas.any(
          (area) =>
              WindowConstants.visibleAreaRatio(x, 700, [area]) >=
              WindowConstants.minVisibleAreaRatio,
        ),
        isFalse,
      );
    });

    test('越出当前所有显示器的坐标无效', () {
      expect(
        WindowConstants.isValidPosition(9000, 1240, workAreas: bothWorkAreas),
        isFalse,
      );
      expect(
        WindowConstants.isValidPosition(3669, 5000, workAreas: bothWorkAreas),
        isFalse,
      );
      // 显示器拔除：坐标落在已消失的左屏上
      expect(
        WindowConstants.isValidPosition(500, 200, workAreas: [primaryWorkArea]),
        isFalse,
      );
    });

    test('兜底矩形覆盖多屏总跨度：4600 合法（旧上界 4000 会误杀）', () {
      expect(WindowConstants.positionMaxX, greaterThan(5120));
      expect(WindowConstants.isValidPosition(4600, 1300), isTrue);
    });

    test('兜底矩形正负对称：副屏在左/上的合法负坐标不被误杀', () {
      // 副屏在主屏左侧时坐标为负，旧下界 minX=-200 / minY=-50 会误杀
      expect(WindowConstants.positionMinX, lessThan(-2560));
      expect(WindowConstants.positionMinY, lessThan(-1440));
      expect(WindowConstants.isValidPosition(-1500, 300), isTrue);
      expect(WindowConstants.isValidPosition(-2000, -900), isTrue);
      // 上下界对称
      expect(WindowConstants.positionMinX, -WindowConstants.positionMaxX);
      expect(WindowConstants.positionMinY, -WindowConstants.positionMaxY);
    });

    test('workAreas 为 null 或空时退回兜底矩形粗判', () {
      expect(WindowConstants.isValidPosition(100, 200), isTrue);
      expect(WindowConstants.isValidPosition(100, 200, workAreas: []), isTrue);
      expect(
        WindowConstants.isValidPosition(WindowConstants.positionMaxX, 0),
        isFalse,
      );
      expect(
        WindowConstants.isValidPosition(WindowConstants.positionMinX - 1, 0),
        isFalse,
      );
    });
  });

  group('WindowConstants.visibleAreaRatio 并集语义', () {
    test('镜像显示器（工作区完全重叠）不重复计数', () {
      // 窗口 400x120 只有 100 宽露在屏上 → 真实可见 25%
      const mirrored = [secondaryWorkArea, secondaryWorkArea];
      const x = 2460.0; // 2460..2860，屏右边界 2560 → 露出 100

      expect(
        WindowConstants.visibleAreaRatio(x, 700, [secondaryWorkArea]),
        closeTo(0.25, 1e-9),
      );
      // 相加会得到 50% 并错误通过；并集必须仍是 25%
      expect(
        WindowConstants.visibleAreaRatio(x, 700, mirrored),
        closeTo(0.25, 1e-9),
      );
      expect(
        WindowConstants.isValidPosition(x, 700, workAreas: mirrored),
        isFalse,
        reason: '只有 25% 可见的窗口不得因镜像屏重复计数而通过判定',
      );
    });

    test('部分重叠的工作区也只算一次', () {
      const a = Rect.fromLTWH(0, 0, 300, 300);
      const b = Rect.fromLTWH(200, 0, 300, 300); // 与 a 在 200..300 重叠
      // 窗口 400x120 落在 0,0：a 贡献 300x120、b 贡献 100..? → 并集应为 400x120 全覆盖
      expect(
        WindowConstants.visibleAreaRatio(0, 0, [a, b], size: const Size(400, 120)),
        closeTo(1.0, 1e-9),
      );
    });

    test('相邻不重叠的工作区正常累加（跨屏摆放）', () {
      const x = 2400.0;
      final ratio = WindowConstants.visibleAreaRatio(x, 700, bothWorkAreas);
      // 左屏 160 + 主屏 182 = 342 / 400
      expect(ratio, closeTo(342 / 400, 1e-9));
    });
  });

  group('WindowConstants.clampToWorkAreas', () {
    test('越界坐标被钳进最近工作区，且整窗可见', () {
      final clamped = WindowConstants.clampToWorkAreas(
        9000,
        5000,
        bothWorkAreas,
      );

      expect(clamped, isNotNull);
      expect(
        WindowConstants.isValidPosition(
          clamped!.dx,
          clamped.dy,
          workAreas: bothWorkAreas,
        ),
        isTrue,
      );
      // 右下方越界 → 贴到主屏右下角
      expect(clamped.dx, primaryWorkArea.right - WindowConstants.windowWidth);
      expect(clamped.dy, primaryWorkArea.bottom - WindowConstants.windowHeight);
    });

    test('按当前窗口尺寸钳位（向导态 540x540）', () {
      final clamped = WindowConstants.clampToWorkAreas(
        9000,
        5000,
        bothWorkAreas,
        size: wizardSize,
      );

      expect(clamped!.dx, primaryWorkArea.right - wizardSize.width);
      expect(clamped.dy, primaryWorkArea.bottom - wizardSize.height);
    });

    test('拿不到工作区集合时返回 null', () {
      expect(WindowConstants.clampToWorkAreas(9000, 5000, null), isNull);
      expect(WindowConstants.clampToWorkAreas(9000, 5000, []), isNull);
    });

    test('工作区比窗口还小时钳位结果仍不合格 → 恢复决策必须拒绝它', () {
      // 工作区 200x80 小于胶囊 400x120：_clampAxis 只能贴到区间起点，
      // 窗口大部分仍在屏外
      const tiny = [Rect.fromLTWH(500, 400, 200, 80)];
      final clamped = WindowConstants.clampToWorkAreas(9000, 5000, tiny);

      expect(clamped, const Offset(500, 400));
      expect(
        WindowConstants.isValidPosition(
          clamped!.dx,
          clamped.dy,
          workAreas: tiny,
        ),
        isFalse,
        reason: '200x80 工作区最多容纳 400x120 窗口面积的 1/3',
      );
      // 决策层必须回校钳位结果，不能把它当最终位置
      final decision = FlutterWindowBackend.resolveRestorePosition(
        9000,
        5000,
        tiny,
      );
      expect(decision.position, isNull, reason: '钳位结果不合格时应走默认位置');
      expect(decision.clearDirty, isFalse, reason: '仍然不许删键');
    });
  });

  group('FlutterWindowBackend.workAreaOf', () {
    test('优先用 workarea (visiblePosition + visibleSize)，保留显示器偏移', () {
      const display = Display(
        id: 'primary',
        size: Size(2560, 1440),
        visiblePosition: Offset(2618, 32),
        visibleSize: Size(2502, 1408),
      );

      expect(FlutterWindowBackend.workAreaOf(display), primaryWorkArea);
    });

    test('workarea 缺失时退回 size 与零偏移', () {
      const display = Display(id: 'primary', size: Size(1920, 1080));

      expect(
        FlutterWindowBackend.workAreaOf(display),
        const Rect.fromLTWH(0, 0, 1920, 1080),
      );
    });

    test('只有 visibleSize 缺失时仍保留 visiblePosition 偏移', () {
      const display = Display(
        id: 'primary',
        size: Size(2560, 1440),
        visiblePosition: Offset(2560, 0),
      );

      expect(
        FlutterWindowBackend.workAreaOf(display),
        const Rect.fromLTWH(2560, 0, 2560, 1440),
      );
    });
  });

  group('FlutterWindowBackend.resolveRestorePosition', () {
    test('prefs 无位置键 → 走默认位置，不清键', () {
      const expected = PositionRestoreDecision();

      expect(
        FlutterWindowBackend.resolveRestorePosition(null, null, bothWorkAreas),
        expected,
      );
      expect(
        FlutterWindowBackend.resolveRestorePosition(3669, null, bothWorkAreas),
        expected,
      );
    });

    test('(0,0) 脏值 → 清键 + 走默认位置', () {
      const expected = PositionRestoreDecision(clearDirty: true);

      expect(
        FlutterWindowBackend.resolveRestorePosition(0, 0, bothWorkAreas),
        expected,
      );
      // 拿不到显示器集合也必须识别脏值
      expect(
        FlutterWindowBackend.resolveRestorePosition(0, 0, null),
        expected,
      );
    });

    test('有效坐标原样恢复', () {
      final decision = FlutterWindowBackend.resolveRestorePosition(
        3297,
        1036,
        bothWorkAreas,
      );

      expect(decision.position, const Offset(3297, 1036));
      expect(decision.clearDirty, isFalse);
    });

    test('越界坐标钳位保留用户意图，绝不清键', () {
      final decision = FlutterWindowBackend.resolveRestorePosition(
        9000,
        5000,
        bothWorkAreas,
      );

      expect(decision.clearDirty, isFalse, reason: '只有 (0,0) 才允许清键');
      expect(
        decision.position,
        WindowConstants.clampToWorkAreas(9000, 5000, bothWorkAreas),
      );
    });

    test('显示器热插拔：坐标落在查询不到的显示器上时不清键', () {
      // 用户位置在左屏，当前只查到主屏
      final decision = FlutterWindowBackend.resolveRestorePosition(
        500,
        200,
        [primaryWorkArea],
      );

      expect(decision.clearDirty, isFalse);
      // 钳到主屏显示，原 prefs 值保持不动，副屏回来后仍可用
      expect(decision.position, isNotNull);
    });

    test('显示器查询失败 → 退回粗判，不丢掉用户位置', () {
      final decision = FlutterWindowBackend.resolveRestorePosition(
        4600,
        1300,
        null,
      );

      expect(decision.position, const Offset(4600, 1300));
      expect(decision.clearDirty, isFalse);
    });

    test('非有限值在钳位之前就被拦掉，按脏值清键', () {
      for (final bad in <(double, double)>[
        (double.nan, 500),
        (500, double.nan),
        (double.infinity, 500),
        (500, double.negativeInfinity),
        (double.nan, double.nan),
      ]) {
        final decision = FlutterWindowBackend.resolveRestorePosition(
          bad.$1,
          bad.$2,
          bothWorkAreas,
        );
        expect(
          decision,
          const PositionRestoreDecision(clearDirty: true),
          reason: '(${bad.$1}, ${bad.$2}) 必须清键并走默认位置',
        );
      }
    });

    test('NaN 若不早拦，钳位会静默给出一个任意角落坐标（回归护栏）', () {
      // 证明"为什么必须早拦"：NaN 让 clampToWorkAreas 里的比较全为 false，
      // 它会静默选中第一个工作区（这里是左屏）并把窗口贴到角落，而不是报错。
      // num.clamp 对 NaN 接收者返回上限，故落点是该屏的右下角。
      final clamped = WindowConstants.clampToWorkAreas(
        double.nan,
        double.nan,
        bothWorkAreas,
      );

      expect(clamped, isNotNull, reason: 'NaN 不会让钳位失败，这正是危险之处');
      expect(clamped!.dx.isFinite && clamped.dy.isFinite, isTrue);
      expect(
        clamped,
        Offset(
          secondaryWorkArea.right - WindowConstants.windowWidth,
          secondaryWorkArea.bottom - WindowConstants.windowHeight,
        ),
        reason: '与用户真实意图毫无关系的坐标 —— 决策层必须在此之前拦掉',
      );

      // 决策层已经不会走到这一步
      expect(
        FlutterWindowBackend.resolveRestorePosition(
          double.nan,
          double.nan,
          bothWorkAreas,
        ).position,
        isNull,
      );
    });

    test('向导尺寸下的校验用向导尺寸，不用胶囊尺寸', () {
      // 贴着主屏右下角、对 400x120 合法但对 540x540 越界的坐标
      final x = primaryWorkArea.right - 420;
      final y = primaryWorkArea.bottom - 130;

      expect(
        FlutterWindowBackend.resolveRestorePosition(x, y, [primaryWorkArea])
            .position,
        Offset(x, y),
      );
      // 按向导尺寸判定时会被钳位回工作区内
      final wizardDecision = FlutterWindowBackend.resolveRestorePosition(
        x,
        y,
        [primaryWorkArea],
        windowSize: wizardSize,
      );
      expect(wizardDecision.position, isNot(Offset(x, y)));
      expect(
        wizardDecision.position!.dy + wizardSize.height,
        lessThanOrEqualTo(primaryWorkArea.bottom),
      );
    });
  });

  group('时序常量', () {
    test('防抖时长在 spec 要求的 300-500ms 区间', () {
      expect(
        FlutterWindowBackend.savePositionDebounce.inMilliseconds,
        inInclusiveRange(300, 500),
      );
    });

    test('程序化几何变更的抑制窗口不短于一帧余量', () {
      expect(
        FlutterWindowBackend.geometrySettleWindow.inMilliseconds,
        greaterThanOrEqualTo(200),
      );
    });
  });
}
