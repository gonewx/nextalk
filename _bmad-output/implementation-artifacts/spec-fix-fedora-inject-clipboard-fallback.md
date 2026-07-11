---
title: 'GNOME Shell 扩展注入后端：修复 Fedora/ibus 环境回退剪贴板'
type: 'feature'
created: '2026-07-10'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'b59ed3a42cb94192c8d87b8b75342c5447e0841b'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Fedora 43 等以 ibus 为默认输入法框架的发行版上，fcitx5 未作为会话输入法运行，`nextalk-fcitx5.sock` 不存在，文本注入总是回退剪贴板；ibus 侧三条注入路径（D-Bus 直连/Engine/Panel Extension）已被 ADR-001 论证并实测不可行。

**Approach:** 新增 GNOME Shell 扩展注入后端：扩展在 shell 进程内导出 D-Bus 方法 `CommitText`，内部调用 `Main.inputMethod.commit(text)`（GNOME 屏幕键盘 OSK 的上屏通道，与输入法框架无关，中文直接提交）。注入链变为 **fcitx5 socket → GNOME 扩展 → 剪贴板**。已于 2026-07-10 在 Fedora 43 VM（GNOME 49.1 + ibus，无 fcitx5 进程）POC 验证：中文完整注入 ptyxis 终端。

## Boundaries & Constraints

**Always:**
- fcitx5 socket 存在时行为与现状完全一致（Debian 路径零回归）。
- GNOME 后端提交前必须复用现有的"隐藏窗口 → 等待焦点恢复"流程（焦点不在目标应用时 commit 无效）。
- GNOME 后端任何失败（D-Bus 超时/异常/扩展未启用）→ 恢复窗口并走剪贴板 fallback，不得丢文本。
- 扩展 metadata 声明 shell-version 45–49；非 GNOME 桌面检测不到 D-Bus 接口时静默跳过。
- 扩展代码保持最小：仅 D-Bus 导出 + commit，无 UI、无定时器。

**Ask First:**
- 若要改动首启向导或托盘菜单来引导用户启用扩展（本 spec 只做 README + postinst 提示）。
- 若 D-Bus 可用性探测需要引入新的常驻连接/轮询机制。

**Never:**
- 不重试任何 ibus 机制（D-Bus 直连/Engine/Panel Extension）。
- 不用 ydotool/wtype（GNOME Wayland 下打不了中文或协议不支持）。
- 不做扩展的自动启用（需用户 `gnome-extensions enable` + 重登）。
- 不改 fcitx5 插件与协议。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| fcitx5 可用 | socket 存在 | 走 fcitx5 提交（现状不变） | 现有 FcitxError 处理链 |
| Fedora/ibus + 扩展已启用 | socket 不存在，D-Bus 接口可达 | 隐藏窗口→等焦点→CommitText 上屏，无剪贴板提示 | N/A |
| 扩展未装/未启用 | socket 不存在，D-Bus 不可达 | 剪贴板模式（现状） | 探测超时 ≤500ms，静默降级 |
| CommitText 调用失败 | D-Bus 异常/超时 | 恢复窗口，复制剪贴板并提示 | 文本保留至剪贴板，不丢失 |
| 非 GNOME 桌面（KDE 等） | org.gnome.Shell 名字不存在 | 剪贴板模式（现状） | 探测失败即降级 |
| 空文本 | text.isEmpty | 不调用后端，直接收尾 | N/A |

</frozen-after-approval>

## Code Map

- `voice_capsule/lib/services/hotkey_controller.dart:327-405` -- 注入决策点（isAvailable 分支）与 `_submitTextToFcitx` fallback；新增 GNOME 分支
- `voice_capsule/lib/services/fcitx_client.dart:107-120` -- `isAvailable`/`checkClipboardMode`；剪贴板模式语义需涵盖 GNOME 后端
- `voice_capsule/lib/services/portal_hotkey_service.dart` -- 现有 dbus 包用法参考（DBusClient.session、超时模式）
- `addons/gnome/nextalk@gonewx.com/` -- 新增扩展目录（metadata.json + extension.js），POC 已验证的实现为蓝本
- `scripts/build-pkg.sh:257-330` -- 共享 staging 函数，追加扩展文件到 `/usr/share/gnome-shell/extensions/`
- `packaging/rpm/nextalk.spec.template`、`packaging/deb/control.template` -- %files/包描述与 postinst 提示
- `voice_capsule/test/services/` -- 后端选择逻辑单测（fake 注入后端）

## Tasks & Acceptance

**Execution:**
- [x] `addons/gnome/nextalk@gonewx.com/extension.js` + `metadata.json` -- 新建扩展：导出 `com.gonewx.nextalk.Inject` 接口（路径 `/com/gonewx/nextalk/Inject`，方法 `CommitText(s)→(s)`），内部 `Main.inputMethod.commit`；enable/disable 正确 export/unexport -- POC 蓝本已验证
- [x] `voice_capsule/lib/services/gnome_inject_client.dart` -- 新建：D-Bus 客户端（dest `org.gnome.Shell`），`isAvailable()`（短超时探测）与 `commitText()`；复用 portal 服务的 DBusClient 模式
- [x] `voice_capsule/lib/services/hotkey_controller.dart` -- 注入决策改为三级链：fcitx5 → GNOME 扩展 → 剪贴板；GNOME 路径复用隐藏窗口/等焦点/中断检查流程；失败恢复窗口走剪贴板
- [x] `voice_capsule/lib/services/fcitx_client.dart` 或调用方 -- `checkClipboardMode` 语义更新：任一直接注入后端可用即非剪贴板模式（FcitxClient 保持职责单一，组合语义在 hotkey_controller 的 decideInjectBackend 体现，已加注释说明）
- [x] `voice_capsule/test/services/gnome_inject_client_test.dart` + 决策链单测 -- 覆盖 I/O 矩阵各行
- [x] `scripts/build-pkg.sh` + `packaging/` 模板 -- deb/rpm 打包扩展到 `/usr/share/gnome-shell/extensions/nextalk@gonewx.com/`；postinst 输出启用指引
- [x] `README.md` / `README_zh.md` -- 新增 GNOME(ibus) 发行版说明：启用扩展 + 重登

**Acceptance Criteria:**
- Given Fedora 43 VM（ibus，无 fcitx5 运行）且扩展已启用并重登，when 语音识别完成提交，then 文本直接上屏到焦点终端且无剪贴板提示。
- Given Debian 13 VM（fcitx5 运行中），when 提交文本，then 仍走 fcitx5 socket 上屏，行为与 v0.2.13 一致。
- Given 扩展未启用的 GNOME 环境，when 提交文本，then 与现状相同进入剪贴板模式，无异常/卡顿（探测 ≤500ms）。
- Given `flutter test`，then 全部通过。

## Design Notes

- POC 实测（2026-07-10，Fedora 43 GNOME 49.1）：`Main.inputMethod.commit("你好世界，Nextalk 注入测试 OK")` 经 mutter text-input-v3 完整注入 ptyxis 终端（`stty -icanon; cat` 读回逐字一致），当时 ibus-daemon 运行、fcitx5 进程数为 0。
- 扩展方法挂在 gnome-shell 自身的 bus 连接上，客户端 dest 用 `org.gnome.Shell`，无需扩展自持 bus name。
- 探测策略：每次提交时短超时（500ms）调用 `CommitText` 前先 introspect/缓存可用性，避免常驻连接；正结果长期缓存、负结果 60s TTL（应对登录时应用早于 gnome-shell 加载扩展的竞态），commit 失败时缓存失效重探。
- 评审补丁（2026-07-11 对抗评审后）：扩展在 commit 前检查 `Main.inputMethod.currentFocus`——无活动文本输入上下文（焦点在非可编辑控件、或应用未实现 text-input 协议如部分 Electron）时 `im.commit` 是静默 no-op，须返回 ERR 触发剪贴板兜底。Fedora 43 VM 实测：终端焦点 OK 上屏、文件管理器焦点返回 ERR。另修复 `_submitFromVad` 缺中断标志复位、README 死锚点，文档补"仅 Wayland 原生窗口"限制。
- 适用边界：仅 GNOME Shell 45+（KDE/XFCE/wlroots 无此通道，仍靠 fcitx5/剪贴板）；与内核版本无关；`Main.inputMethod` 是 shell 内部 API 但 OSK 依赖它，随 GNOME 大版本升级需维护 shell-version 声明。
- XWayland 实测结论（2026-07-10 Fedora 43）：焦点在 XWayland 窗口（`GDK_BACKEND=x11` ptyxis）时 commit 静默无效且无报错——违反"不丢文本"约束。已在扩展 CommitText 内加防护：焦点窗口 `get_client_type() == Meta.WindowClientType.X11` 或无焦点窗口时返回 ERR，客户端据此走剪贴板 fallback。补丁后三场景 VM 实测：Wayland 终端 OK 上屏、XWayland 返回 ERR、无焦点返回 ERR。

## Verification

**Commands:**
- `cd voice_capsule && flutter test` -- expected: 全部通过
- `./scripts/build-pkg.sh --rebuild --deb --rpm` -- expected: 包内含 `usr/share/gnome-shell/extensions/nextalk@gonewx.com/`（rpm 用 `rpm2cpio | cpio -t` 验证）

**Manual checks (if no CLI):**
- Fedora VM：装 rpm → `gnome-extensions enable nextalk@gonewx.com` → 重登 → Super+Z 说话 → 文本上屏 ptyxis，无"已复制"提示。
- Debian VM：装 deb → 提交文本仍经 fcitx5 上屏（回归）。
- ~~Fedora VM：对 XWayland 应用测一次注入，记录结论。~~ 已完成（2026-07-10）：XWayland 收不到 commit，扩展已加 X11/无焦点防护返回 ERR，剪贴板兜底（见 Design Notes）。

## Suggested Review Order

**注入链决策（入口）**

- 三级链纯函数：fcitx5 短路优先保证 Debian 零回归，空文本不探测 GNOME
  [`hotkey_controller.dart:36`](../../voice_capsule/lib/services/hotkey_controller.dart#L36)

- GNOME/剪贴板提交编排：复用隐藏窗口→100ms 等焦点→中断检查，失败恢复窗口走剪贴板
  [`hotkey_controller.dart:410`](../../voice_capsule/lib/services/hotkey_controller.dart#L410)

- fcitx socket 类错误 fallback：剪贴板前先试 GNOME（窗口此时已隐藏、焦点已回归）
  [`hotkey_controller.dart:460`](../../voice_capsule/lib/services/hotkey_controller.dart#L460)

**GNOME Shell 扩展（注入通道）**

- CommitText 三重防护：无焦点窗口 / X11 目标 / 无活动文本输入 → ERR 触发剪贴板兜底
  [`extension.js:42`](../../addons/gnome/nextalk@gonewx.com/extension.js#L42)

- 挂在 gnome-shell 自身 bus 连接导出，客户端 dest 用 org.gnome.Shell
  [`extension.js:32`](../../addons/gnome/nextalk@gonewx.com/extension.js#L32)

**D-Bus 客户端**

- 可用性缓存策略：正结果长期、负结果 60s TTL 自愈登录竞态
  [`gnome_inject_client.dart:124`](../../voice_capsule/lib/services/gnome_inject_client.dart#L124)

- commit 失败使缓存失效、返回 false 交调用方兜底
  [`gnome_inject_client.dart:156`](../../voice_capsule/lib/services/gnome_inject_client.dart#L156)

- 500ms Introspect 探测 + 2s commit 超时（对齐 portal 服务模式）
  [`gnome_inject_client.dart:47`](../../voice_capsule/lib/services/gnome_inject_client.dart#L47)

**打包与文档**

- deb/rpm 共用 staging 拷贝扩展到系统扩展目录
  [`build-pkg.sh:312`](../../scripts/build-pkg.sh#L312)

- rpm %files 显式列出扩展文件
  [`nextalk.spec.template:180`](../../packaging/rpm/nextalk.spec.template#L180)

- 安装指引与 Wayland 原生窗口限制说明（deb postinst 同步）
  [`README_zh.md:44`](../../README_zh.md#L44)

**测试**

- 决策链覆盖 I/O 矩阵 + 客户端探测/缓存/TTL/失效语义
  [`gnome_inject_client_test.dart:9`](../../voice_capsule/test/services/gnome_inject_client_test.dart#L9)
