import 'package:flutter/services.dart';

/// 剪贴板工具类
/// Story 3-7: AC15 提交失败时保护用户文本，提供"复制文本"按钮
class ClipboardHelper {
  /// 复制文本到剪贴板
  ///
  /// 返回 true 表示复制成功，false 表示失败
  static Future<bool> copyText(String text) async {
    if (text.isEmpty) return false;

    try {
      await Clipboard.setData(ClipboardData(text: text));
      return true;
    } catch (_) {
      return false;
    }
  }

  /// 从剪贴板获取文本
  ///
  /// 返回 null 表示剪贴板为空或获取失败
  static Future<String?> getText() async {
    try {
      final data = await Clipboard.getData(Clipboard.kTextPlain);
      return data?.text;
    } catch (_) {
      return null;
    }
  }
}
