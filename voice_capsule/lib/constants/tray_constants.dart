/// 系统托盘常量
/// Story 3-4: 系统托盘集成
/// Story 3-7: 新增状态图标和重连菜单
class TrayConstants {
  TrayConstants._();

  // ===== 托盘配置 =====

  /// 应用名称 (显示在托盘 tooltip)
  static const String appName = 'Nextalk';

  /// 托盘图标相对路径 (正常状态)
  static const String iconPath = 'assets/icons/tray_icon.png';

  /// Story 3-7: 警告状态图标 (AC19)
  static const String iconWarningPath = 'assets/icons/tray_icon_warning.png';

  /// Story 3-7: 错误状态图标 (AC19)
  static const String iconErrorPath = 'assets/icons/tray_icon_error.png';

  // ===== 菜单项标签 =====

  /// 标题项 (禁用)
  static const String menuTitle = 'Nextalk';

  /// 显示/隐藏
  static const String menuShowHide = '显示 / 隐藏';

  /// Story 3-7: 重新连接 Fcitx5 (AC16)
  static const String menuReconnectFcitx = '重新连接 Fcitx5';

  /// 设置 (Post MVP - 灰色禁用)
  static const String menuSettings = '设置...';

  /// 退出
  static const String menuExit = '退出';
}



