# 开发踩坑记录

简体中文 | [English](development-pitfalls.md)

本文档记录 Nextalk 开发过程中遇到的技术问题、根因分析及解决方案，供后续维护参考。

---

## 目录

- [Flutter system_tray 库 Linux Checkbox 状态 Bug](#flutter-system_tray-库-linux-checkbox-状态-bug)
- [xdg-desktop-portal-gnome 48.0 BindShortcuts 假失败 Bug](#xdg-desktop-portal-gnome-480-bindshortcuts-假失败-bug)
- [GNOME 全局快捷键授权对话框"不弹框"的两种正常机制](#gnome-全局快捷键授权对话框不弹框的两种正常机制)
- [Portal 授权对话框 60s 交互超时导致慢速用户绑定失效](#portal-授权对话框-60s-交互超时导致慢速用户绑定失效)
- [Fedora 启动即段错误：system_tray 上游 dlopen 旧版 libappindicator](#fedora-启动即段错误system_tray-上游-dlopen-旧版-libappindicator)

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

## xdg-desktop-portal-gnome 48.0 BindShortcuts 假失败 Bug

### 问题描述

Debian 13/GNOME 48 上,Portal `BindShortcuts` 绑定**实际完全成功**(gnome-shell 完成 GrabAccelerators、`ShortcutsChanged` 信号已发出、快捷键真实可用),但应用收到的 `Request::Response` 状态码是 2(失败)。应用误判失败后关闭 session,导致快捷键被解绑,永远降级到系统快捷键模式。

### 复现场景

Debian 13(xdg-desktop-portal-gnome 48.0-2)上启动应用,diagnostic.log 每次都出现:

```
[PortalHotkey] ⚠️ 降级到系统快捷键: Portal 注册失败: (response=2)
```

`dbus-monitor` 抓包可见:provider(gnome-control-center)对 `BindShortcuts` 的 method return 携带成功绑定的 `<Super>z`,但 1.5ms 后 portal-gnome 给应用的 `Response` 信号是 `uint32 2`——且 results 里带着已绑定的 shortcuts 数组。

### 根因分析

xdg-desktop-portal-gnome 48.0 `src/globalshortcuts.c` 的 `shell_grab_accelerators_done()`:`int response;` 声明后只有失败路径赋值 `response = 2`,**成功路径从未赋值**就走到 `out:` 标签把未初始化的栈值(恰为 2)回给应用。上游 commit `27511907`("globalshortcuts: Fix BindShortcut success response",2025-08-02)在成功路径末尾补了 `response = 0;`,但 Debian 13 的 48.0-2 未收录,且作为稳定发行版将长期停留在此版本。

### 解决方案

应用侧识别"假失败":`_sendRequest` 失败时抛出携带 results 的 `PortalRequestFailedException`;`bindShortcuts` 捕获后用 `shortcutsActuallyBound()` 判定——response=2 但 results 携带覆盖全部请求 id 的非空 shortcuts 数组时按成功处理。安全性:该 bug 的真失败路径(provider 报错、grab 失败)results 均为空 vardict,不会误判。

```dart
} on PortalRequestFailedException catch (e) {
  if (!shortcutsActuallyBound(e.results, shortcuts)) rethrow;
}
```

### 相关文件

- `voice_capsule/lib/services/portal_hotkey_service.dart`(`PortalRequestFailedException`、`shortcutsActuallyBound`)
- `voice_capsule/test/services/portal_hotkey_service_test.dart`("GNOME 48.0 假失败识别" 测试组)

### 备选方案（未采用）

- 绑定后调 `ListShortcuts` 验证实际状态:多一次 D-Bus 往返,且 48.0 的 ListShortcuts 行为未验证
- 等 Debian 打补丁:不可控,发行版稳定分支极少回传此类修复

---

## GNOME 全局快捷键授权对话框"不弹框"的两种正常机制

### 问题描述

测试"首次安装弹授权框"流程时,启动应用后授权对话框不出现;清空 `gsettings` 的 `applications` 授权列表后重装重启,依然不弹框,且该 app id 被自动写回列表。

### 复现场景

```bash
gsettings set org.gnome.settings-daemon.global-shortcuts applications "[]"
# 重启应用 → 仍不弹框,列表里又出现了 com.gonewx.nextalk
```

### 根因分析

两层机制叠加:

1. **授权记忆**:GNOME 把每个应用的快捷键授权存在 dconf `/org/gnome/settings-daemon/global-shortcuts/` 下——`applications` 键只是**索引**,快捷键本体存在 per-app 子路径(如 `[com.gonewx.nextalk] shortcuts=...`)。
2. **静默批准**:gnome-control-center 48.4 `cc_global_shortcut_dialog_present()` 开头即 `if (!self->has_new_shortcuts) { emit_done(self, TRUE); return; }`——请求的快捷键与已存储的一致(没有"新"快捷键)时,直接批准并把 app 写回索引,不显示任何对话框。只清索引不清 per-app 子路径,请求永远命中"已存储"。

### 解决方案

想重看授权框必须清掉**整个子树**(索引 + per-app 存储):

```bash
dconf reset -f /org/gnome/settings-daemon/global-shortcuts/
```

之后重启应用(应用单次运行只尝试一次注册),对话框即弹出。注意这两种"不弹框"对用户都是良性的——绑定静默成功,快捷键可用。

### 相关文件

- gnome-control-center `global-shortcuts-provider/cc-global-shortcut-dialog.c`(上游行为)
- `docs/architecture_zh.md` §2.1 第四代快捷键"生命周期"

### 备选方案（未采用）

无——这是 GNOME 的预期设计,应用侧无需也不应绕过。

---

## Portal 授权对话框 60s 交互超时导致慢速用户绑定失效

### 问题描述

首次启动弹出授权对话框后,用户若未在 60 秒内点击"添加",应用侧等待超时(`TimeoutException after 0:01:00`)、锁定注册尝试并降级到系统快捷键;**用户之后点击"添加"只写入 GNOME 侧存储,当前会话的快捷键不生效**(应用已关闭 session、停止监听),表现为"点了添加但按快捷键没反应"。

### 复现场景

1. `dconf reset -f /org/gnome/settings-daemon/global-shortcuts/` 后启动应用,弹出授权框
2. 放置超过 60 秒再点"添加"
3. 按 Super+Z 无反应;diagnostic.log 可见超时降级记录;重启应用后恢复(授权已存,启动时静默注册成功)

### 根因分析

`DBusGlobalShortcutsBackend` 的交互超时(`_interactiveTimeout`)原为 60s。真实首启用户经常不会立刻处理弹出的系统对话框(阅读内容、切走窗口、暂时离开),60s 一个很容易越过的阈值;超时走 `catch` 分支后 `_registerAttempted = true` 锁定 + `closeSession`,本次会话无法再绑定。而 GNOME 的对话框独立于 portal session 存活,用户稍后点击仍会写入 dconf——造成"系统侧已授权、应用侧已放弃"的割裂状态。

### 解决方案

交互超时放宽到 **10 分钟**。依据:授权对话框会一直挂着等用户操作,`Response` 在用户点按钮(添加/取消)时必然发出——超时唯一需要兜底的是"backend 既不弹框也不回复"的异常平台,10 分钟足够宽裕且仍能收敛。实测放置 8 分钟后点击"添加",应用立即注册成功。

```dart
_interactiveTimeout =
    interactiveTimeout ?? timeout ?? const Duration(minutes: 10)
```

### 相关文件

- `voice_capsule/lib/services/portal_hotkey_service.dart`(`DBusGlobalShortcutsBackend` 构造函数)

### 备选方案（未采用）

- 完全去掉超时:异常 backend 上 Future 永久挂起,托盘模式永远停在"系统快捷键"且资源不释放
- 超时后不锁定 `_registerAttempted`:当前架构无自动重试触发点,锁不锁行为一致,治标不治本
- 超时后保持 session 继续后台监听 Response:改动大,10 分钟超时已覆盖真实场景

---

## Fedora 启动即段错误：system_tray 上游 dlopen 旧版 libappindicator

### 问题描述

Fedora 43 上启动应用,`method call InitSystemTray` 后立即段错误（核心已转储）;同一 0.2.13 包在 Debian 13 上完全正常。

### 复现场景

Fedora 43 (GNOME 49/Wayland) + 系统装有旧版 `libappindicator-12.10.1`（孤儿包,无任何包依赖它）时,运行 `nextalk` 必崩。coredumpctl 栈:

```
#0 app_indicator_set_status (libappindicator3.so.1)   ← 已废弃的旧版库
#1 Tray::init_tray (libsystem_tray_plugin.so)
```

### 根因分析

上游 `system_tray 2.0.3` 的 `linux/tray.cc` 在 CMake 层检测并链接 ayatana,但运行时**硬编码 `dlopen("libappindicator3.so.1")`**（旧版库名）,再 dlsym 取全部函数指针:

- **Debian 13**: `libayatana-appindicator3-1` 包自带兼容 symlink `libappindicator3.so.1 -> libayatana-appindicator3.so.1`,dlopen 旧名字实际拿到健康的 ayatana → 正常（上游 bug 被发行版 symlink 掩盖）
- **Fedora 43**: 无兼容 symlink,`libappindicator3.so.1` 由真正的旧版 `libappindicator-12.10.1` 提供,该废弃库在 GNOME 49/Wayland 下 `app_indicator_set_status` 段错误

Dart 层 try/catch 接不住 native 段错误,整个进程崩溃。

### 解决方案

vendor 插件源码到 `third_party/system_tray/` 并打补丁——优先 dlopen ayatana,失败再回退旧版:

```c
void* handle = dlopen("libayatana-appindicator3.so.1", RTLD_LAZY);
if (!handle) {
  handle = dlopen("libappindicator3.so.1", RTLD_LAZY);
}
```

`pubspec.yaml` 用 `dependency_overrides` 指向 vendored 副本。Fedora 43 实测:InitSystemTray 通过、顶栏图标正常显示（需 `gnome-shell-extension-appindicator` 扩展已启用）。

### 相关文件

- `third_party/system_tray/linux/tray.cc`（补丁位置,含 Nextalk patch 注释）
- `voice_capsule/pubspec.yaml`（dependency_overrides）

### 备选方案（未采用）

- rpm 加 `Conflicts: libappindicator`: 干涉用户系统包,其他应用可能需要旧库
- 提示用户 `dnf remove libappindicator`: 治标,新装环境仍会踩坑
- 向上游提 PR: 应该做（补丁可直接贡献）,但上游更新节奏不可控,vendored 先行

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
