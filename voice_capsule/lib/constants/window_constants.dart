import 'dart:math' as math;
import 'dart:ui';

/// 窗口尺寸和位置常量
/// Story 3-1: 透明胶囊窗口基础
class WindowConstants {
  // 禁止实例化
  WindowConstants._();

  /// 窗口总尺寸 (包含阴影区域的画布) - AC3
  /// 基础高度用于正常胶囊状态，动态调整由 WindowService 处理
  static const double windowWidth = 400.0;
  static const double windowHeight = 120.0;

  /// 错误状态下的扩展高度 (包含操作按钮)
  static const double windowHeightExpanded = 180.0;

  /// 初始化向导窗口尺寸 (Story 3-7)
  /// 足够容纳最大的手动安装界面
  static const double initWizardWidth = 540.0;
  static const double initWizardHeight = 540.0;

  /// 胶囊内容区尺寸 (Story 3-2 使用)
  static const double capsuleWidth = 380.0; // Max
  static const double capsuleMinWidth = 280.0; // Min
  static const double capsuleHeight = 60.0;

  /// 圆角半径 (Story 3-2 使用)
  static const double capsuleRadius = 40.0;

  /// SharedPreferences 键名 (使用 nextalk_ 前缀避免与其他 Flutter 应用冲突)
  static const String positionXKey = 'nextalk_window_x';
  static const String positionYKey = 'nextalk_window_y';

  /// 默认位置的底部留白 (窗口下沿到工作区下边缘的距离)
  static const double defaultBottomMargin = 80.0;

  /// 胶囊默认尺寸 (位置计算的默认窗口尺寸)
  static const Size defaultWindowSize = Size(windowWidth, windowHeight);

  /// 位置边界校验的兜底矩形
  ///
  /// 仅在拿不到显示器工作区时使用 (见 [isValidPosition])。范围必须覆盖常见
  /// 多屏总跨度，且**正负对称**：
  /// - 上界：本机双屏总宽已达 5120、实测坐标 4600 合法，旧值 maxX=4000 /
  ///   maxY=2500 会把合法坐标误判为越界。
  /// - 下界：副屏在主屏左侧/上方时，合法坐标为负（如 -1500,300），旧值
  ///   minX=-200 / minY=-50 会在"显示器查询已经失败"这条本就退化的路径上
  ///   再误杀一次，把用户位置换成默认位置。
  static const double positionMinX = -16384.0;
  static const double positionMaxX = 16384.0;
  static const double positionMinY = -16384.0;
  static const double positionMaxY = 16384.0;

  /// 判定位置有效所需的最小可见面积比例
  ///
  /// 分子是窗口与**所有**工作区交集面积之和（累计面积，不是单屏面积）：
  /// 跨两台相邻显示器摆放时对任一单屏都不足半数，按单屏判定会误杀，
  /// 而多显示器正是本次的主场景。
  static const double minVisibleAreaRatio = 0.5;

  /// 是否为需要丢弃的脏值遗留坐标
  ///
  /// (0, 0) 是 Wayland 原生后端下 `gtk_window_get_position()` 的伪值签名。
  /// 胶囊默认贴近屏幕底部，且 y=0 会被 GNOME 顶栏遮挡，用户不可能有意
  /// 把窗口精确停在此处，因此可以安全地把它当作无效值。
  static bool isDirtyLegacyPosition(double x, double y) => x == 0.0 && y == 0.0;

  /// 该坐标是否值得写入 prefs
  ///
  /// 拒绝脏值哨兵与非有限值（NaN/Infinity 会污染持久化且无法恢复）。
  static bool shouldPersistPosition(double x, double y) {
    return x.isFinite && y.isFinite && !isDirtyLegacyPosition(x, y);
  }

  /// 验证位置是否落在有效屏幕范围内
  ///
  /// [workAreas] 为当前所有显示器的工作区矩形（绝对坐标，含显示器偏移）。
  /// 传入时按真实屏幕几何判定：窗口与各工作区的交集面积之和须达到窗口面积的
  /// [minVisibleAreaRatio]。传 null / 空列表时退回兜底矩形粗判，供显示器查询
  /// 失败的场景使用。
  static bool isValidPosition(
    double x,
    double y, {
    List<Rect>? workAreas,
    Size size = defaultWindowSize,
  }) {
    if (!shouldPersistPosition(x, y)) return false;

    if (workAreas != null && workAreas.isNotEmpty) {
      return visibleAreaRatio(x, y, workAreas, size: size) >=
          minVisibleAreaRatio;
    }

    return x >= positionMinX &&
        x < positionMaxX &&
        y >= positionMinY &&
        y < positionMaxY;
  }

  /// 窗口在所有工作区上的**可见面积并集**占窗口面积的比例
  ///
  /// 必须按并集算而不是把各屏交集面积直接相加：镜像显示器的工作区完全重叠，
  /// 相加会重复计数 —— 只有 25% 露在屏上的窗口能被算成 50% 而通过判定。
  /// 这里先对交集矩形去重再累加；去重后仍相互重叠的情形（部分重叠布局）
  /// 用扫描线求真并集面积。
  static double visibleAreaRatio(
    double x,
    double y,
    List<Rect> workAreas, {
    Size size = defaultWindowSize,
  }) {
    final windowArea = size.width * size.height;
    if (windowArea <= 0) return 0;

    final window = Rect.fromLTWH(x, y, size.width, size.height);
    final pieces = <Rect>[];
    for (final area in workAreas) {
      final overlap = window.intersect(area);
      if (overlap.width > 0 && overlap.height > 0) {
        pieces.add(overlap);
      }
    }
    return _unionArea(pieces) / windowArea;
  }

  /// 矩形集合的并集面积（扫描线：按 x 切条带，每条带内合并 y 区间）
  static double _unionArea(List<Rect> rects) {
    if (rects.isEmpty) return 0;
    if (rects.length == 1) return rects.first.width * rects.first.height;

    final xs = <double>{};
    for (final r in rects) {
      xs.add(r.left);
      xs.add(r.right);
    }
    final bounds = xs.toList()..sort();

    var total = 0.0;
    for (var i = 0; i < bounds.length - 1; i++) {
      final left = bounds[i];
      final right = bounds[i + 1];
      final stripWidth = right - left;
      if (stripWidth <= 0) continue;

      // 收集覆盖该条带的所有 y 区间并合并
      final spans = <(double, double)>[];
      for (final r in rects) {
        if (r.left <= left && r.right >= right) {
          spans.add((r.top, r.bottom));
        }
      }
      if (spans.isEmpty) continue;
      spans.sort((a, b) => a.$1.compareTo(b.$1));

      var covered = 0.0;
      var spanStart = spans.first.$1;
      var spanEnd = spans.first.$2;
      for (final span in spans.skip(1)) {
        if (span.$1 > spanEnd) {
          covered += spanEnd - spanStart;
          spanStart = span.$1;
          spanEnd = span.$2;
        } else if (span.$2 > spanEnd) {
          spanEnd = span.$2;
        }
      }
      covered += spanEnd - spanStart;

      total += stripWidth * covered;
    }
    return total;
  }

  /// 把越界坐标钳位到最近的工作区，尽量保留用户意图
  ///
  /// 选取与窗口交集面积最大的工作区；全都无交集时取中心距离最近的那个。
  /// [workAreas] 为 null / 空列表时返回 null（无从判断"最近"）。
  /// 目标工作区比窗口还小时钳位结果仍可能大部分在屏外，调用方需回校
  /// （见 [isValidPosition]）。
  static Offset? clampToWorkAreas(
    double x,
    double y,
    List<Rect>? workAreas, {
    Size size = defaultWindowSize,
  }) {
    if (workAreas == null || workAreas.isEmpty) return null;

    final window = Rect.fromLTWH(x, y, size.width, size.height);
    Rect? best;
    var bestOverlap = -1.0;
    var bestDistance = double.infinity;

    for (final area in workAreas) {
      if (area.width <= 0 || area.height <= 0) continue;
      final overlap = window.intersect(area);
      final overlapArea = (overlap.width > 0 && overlap.height > 0)
          ? overlap.width * overlap.height
          : 0.0;
      final distance = (area.center - window.center).distance;

      if (overlapArea > bestOverlap ||
          (overlapArea == bestOverlap && distance < bestDistance)) {
        best = area;
        bestOverlap = overlapArea;
        bestDistance = distance;
      }
    }
    if (best == null) return null;

    return Offset(
      _clampAxis(x, best.left, best.right, size.width),
      _clampAxis(y, best.top, best.bottom, size.height),
    );
  }

  /// 把窗口单轴起点钳进 [start, end) 区间，使窗口整体可见
  /// 区间比窗口还小时贴到起点（宁可溢出下边，也不要算出负坐标）
  static double _clampAxis(
    double value,
    double start,
    double end,
    double extent,
  ) {
    final maxStart = end - extent;
    if (maxStart <= start) return start;
    return value.clamp(start, maxStart);
  }

  /// 计算默认位置：显示器工作区底部居中
  ///
  /// [workArea] 必须是绝对坐标（含显示器偏移）。只用尺寸做居中会在多显示器
  /// 布局下把窗口丢到别的屏幕上 —— 这是本函数存在的主要原因。
  /// 工作区小于窗口时钳到工作区左上角，避免算出负坐标。
  static Offset defaultPosition(
    Rect workArea, {
    Size size = defaultWindowSize,
    double bottomMargin = defaultBottomMargin,
  }) {
    final x = workArea.left + math.max(0.0, (workArea.width - size.width) / 2);
    final y = workArea.top +
        math.max(0.0, workArea.height - size.height - bottomMargin);
    return Offset(x, y);
  }
}
