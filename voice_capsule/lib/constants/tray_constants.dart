/// 系统托盘常量
/// Story 3-4: 系统托盘集成
class TrayConstants {
  TrayConstants._();

  // ===== 托盘配置 =====

  /// 应用名称 (显示在托盘 tooltip)
  static const String appName = 'Nextalk';

  /// 托盘图标相对路径
  static const String iconPath = 'assets/icons/tray_icon.png';

  // ===== 菜单项标签 =====

  /// 标题项 (禁用)
  static const String menuTitle = 'Nextalk';

  /// 显示/隐藏
  static const String menuShowHide = '显示 / 隐藏';

  /// 设置 (Post MVP - 灰色禁用)
  static const String menuSettings = '设置...';

  /// 退出
  static const String menuExit = '退出';
}
