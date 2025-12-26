# 开发踩坑记录

本文档记录 Nextalk 开发过程中遇到的技术问题、根因分析及解决方案，供后续维护参考。

---

## 目录

- [Flutter system_tray 库 Linux Checkbox 状态 Bug](#flutter-system_tray-库-linux-checkbox-状态-bug)

---

## Flutter system_tray 库 Linux Checkbox 状态 Bug

### 问题描述

在 Linux 环境下使用 `system_tray` 包（v2.0.3）时，托盘菜单中的 `MenuItemCheckbox` 组件无法正确更新选中状态。

**表现**：
- 代码逻辑正确传入 `checked: false`，但 UI 上仍显示为选中（打勾）状态
- 多个互斥的 checkbox 项同时显示为选中状态
- 重建菜单后问题依然存在

### 复现场景

```dart
// 代码逻辑正确
final senseChecked = actualEngine == EngineType.sensevoice;  // false
final zipStdChecked = actualEngine == EngineType.zipformer;  // true

MenuItemCheckbox(
  label: 'SenseVoice',
  checked: senseChecked,  // 传入 false
  onClicked: (_) => _switchEngine(EngineType.sensevoice),
),
```

日志输出确认值正确：
```
[TrayService._buildMenu] zipInt8=false, zipStd=true, sense=false
```

但托盘菜单中 SenseVoice 和 Zipformer 子项**同时显示勾选**。

### 根因分析

通过分析 `system_tray` 库的 Linux 原生实现（`~/.pub-cache/hosted/pub.dev/system_tray-2.0.3/linux/`）发现：

1. **菜单缓存未清理**：`MenuManager::menus_map_` 静态 Map 会累积旧菜单，旧菜单的 GTK widget 可能仍被引用
2. **GTK checkbox 状态残留**：`tray.cc` 的 `set_context_menu()` 方法只是简单调用 `app_indicator_set_menu_()`，没有正确销毁旧的 GTK 菜单或重置 checkbox 状态
3. **menu_id 递增但旧菜单未删除**：每次 `buildFrom()` 时 `_menuId` 递增，但 `menus_map_` 中的旧条目未被清理

关键代码位置：
- `tray.cc:set_context_menu()` - 未清理旧菜单
- `menu_manager.cc:add_menu()` - 使用 `emplace` 只添加不替换
- `menu.cc:value_to_menu_item()` - checkbox 创建逻辑本身正确

### 解决方案

**采用方案**：用 `MenuItemLabel` + 标记符号代替 `MenuItemCheckbox`，避开库的 bug。

```dart
// 修改前（有 bug）
MenuItemCheckbox(
  label: lang.tr('tray_engine_sensevoice'),
  checked: actualEngine == EngineType.sensevoice,
  onClicked: (_) => _switchEngine(EngineType.sensevoice),
),

// 修改后（workaround）
MenuItemLabel(
  label: '${senseChecked ? "● " : ""}${lang.tr('tray_engine_sensevoice')}',
  onClicked: (_) => _switchEngine(EngineType.sensevoice),
),
```

**效果**：
- 选中项显示 `● SenseVoice (离线)`
- 未选中项显示 `SenseVoice (离线)`
- 状态更新可靠

### 相关文件

- `voice_capsule/lib/services/tray_service.dart` - 托盘服务实现
- 库源码：`~/.pub-cache/hosted/pub.dev/system_tray-2.0.3/linux/`

### 备选方案（未采用）

1. **销毁并重建整个托盘**：调用 `SystemTray.destroy()` 后重新 `initSystemTray()`，但会造成托盘图标闪烁
2. **换用 tray_manager 库**：另一个托盘库，有明确的 checkbox 支持，但需要评估迁移成本
3. **提交 PR 修复上游**：修复 `system_tray` 库的 Linux 实现，长期方案

---

## 文档维护

遇到新的踩坑问题时，请按以下模板添加：

```markdown
## [问题标题]

### 问题描述
[简要描述问题表现]

### 复现场景
[代码示例或操作步骤]

### 根因分析
[技术层面的原因分析]

### 解决方案
[采用的解决方案及代码示例]

### 相关文件
[涉及的源码文件路径]

### 备选方案（未采用）
[其他考虑过的方案]
```
