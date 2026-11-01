# IBus / Fcitx5 双框架上屏方案重新调研（2026-10）

> 日期：2026-10-31 · 范围：识别文本如何"直接上屏"，不涉及 ASR 本身
> 结论状态：IBus 主 Panel 路径已产品化为 `CommitText` 的首选通道，**随 v0.3.3 于 2026-11-01 发布**；Fedora 43 VM POC 与正式版回归通过（见 §8.1）。

## 1. 结论速览

| 环境 | 现状 | 本次结论 |
|---|---|---|
| 任意桌面 + Fcitx5 | ✅ 插件 socket 上屏，体验最好 | 保持不变 |
| GNOME + IBus（Fedora、Ubuntu 默认） | ✅ v0.3.3（2026-11-01）已发布：`CommitText` 优先调用主 Panel `commit_text()`，支持 Wayland 原生及 X11/XWayland 窗口 | 主 Panel 失败后尝试 `Main.inputMethod.commit`（仅 Wayland 原生）；两者均失败返回 ERR，由客户端回退剪贴板。纯 XIM、Qt-X11 / Electron 尚未验证，详见 §8.1 |
| KDE / XFCE 等 + IBus | ❌ 只能用剪贴板 | 🟡 只剩"临时切换全局引擎"这一条路，有副作用，需要 POC；短期仍建议改用 Fcitx5 |

因此，两大框架都"完美支持"的可行形态是：**Fcitx5 插件（现有）+ GNOME 扩展改走 IBus Panel 通道（新增）**。非 GNOME 桌面上的 IBus 用户量很小，建议继续引导他们改用 Fcitx5。

## 2. "完美支持"的判定标准

1. 中文能上屏到**任意获得焦点的可编辑控件**，包括终端，以及 Wayland 原生和 X11/XWayland 应用；
2. 正常情况下**不出现剪贴板回退**；回退只用于兜底，而且不能丢文本；
3. 不打断用户当前的输入法状态（拼音引擎不被切换、不丢预编辑）；
4. 安装后的一次性配置尽量少（现有 GNOME 扩展需要 `gnome-extensions enable` 加重新登录，这个成本暂时接受）。

## 3. 背景：此前的结论

- SCP-002（2025-12-28）：IBus Panel **Extension** 方案失败，原因是 *"IBus daemon 硬编码，只认识 Emoji 扩展"*。
- 规格 `spec-fix-fedora-inject-clipboard-fallback`（2026-07）：IBus 的三条路径（D-Bus 直连 / Engine / Panel Extension）"已被 ADR-001 论证并实测不可行"，于是改用 GNOME 扩展调用 `Main.inputMethod.commit`。
- ⚠️ ADR-001、SCP-001、`docs/research/wayland_text_injection.md` 在当前仓库和 git 历史中**都已找不到**，Engine 路径当时失败的具体原因无从复核。

**需要明确区分的一点**：此前失败的是"注册为 Panel **Extension**"，即 `PANEL_TYPE_EXTENSION_EMOJI` 这个槽位，daemon 只为 emoji 预留。本文提出的是由**已经存在的主 Panel**（`PANEL_TYPE_PANEL`）发起提交，这是另一套机制，此前没有被排除。

## 4. 核心发现：IBus 主 Panel 可以向焦点上下文提交文本

### 4.1 ibus 源码证据（本地 `achive/ibus`，1.5.34，2025-12）

`bus/panelproxy.c`：Panel 发出 `CommitText` D-Bus 信号后，daemon 把文本转发给**当前焦点输入上下文**：

```c
// panelproxy.c:476  收到 Panel 的 "CommitText" 信号 → emit COMMIT_TEXT
// panelproxy.c:747
bus_panel_proxy_commit_text (BusPanelProxy *panel, IBusText *text) {
    if (!panel->focused_context) return;          // 没有焦点上下文就静默丢弃
    if (panel->panel_type != PANEL_TYPE_PANEL) use_extension = FALSE;
    bus_input_context_commit_text_use_extension (panel->focused_context, text, use_extension);
}
```

`bus/inputcontext.c:3413`：只有当用户**正打开 emoji 选择器**（`context->emoji_extension` 不为空，见 `ibusimpl.c:347`）时，文本才会被分流到 emoji 扩展；其余情况下都会向客户端发出 `CommitText` 信号，也就是正常上屏。

- 客户端 API：`ibus_panel_service_commit_text()`（`src/ibuspanelservice.c:1721`），**自 ibus 1.5.15（2017）起提供**，所有在维护的发行版都满足这个版本要求。

### 4.2 gnome-shell 侧

`js/misc/ibusManager.js`（GNOME main 分支）：

- gnome-shell 以 `ibus-daemon --panel disable` 启动 daemon，**自己**用 `this._panelService = new IBus.PanelService({connection, object_path: IBus.PATH_PANEL})` 持有主 Panel；
- 它监听 `_panelService` 的 `focus-in(path)` 和 `focus-out` 信号，并通过 `getIBusManager()` 导出单例。

`js/misc/inputMethod.js`：`Main.inputMethod` 本身就是一个名为 `'gnome-shell'` 的 IBus InputContext，收到 `commit-text` 后经 text-input-v3 转发给 Wayland 客户端。

### 4.3 推论：一条调用覆盖两类窗口

扩展内调用：

```js
const ibusManager = IBusManager.getIBusManager();
ibusManager._panelService.commit_text(IBus.Text.new_from_string(text));
```

| 焦点窗口 | IBus 焦点上下文 | 文本流向 |
|---|---|---|
| Wayland 原生（GTK4、ptyxis 等） | gnome-shell 的 `'gnome-shell'` 上下文 | daemon → `Main.inputMethod` → text-input-v3 → 应用 |
| X11/XWayland（GTK/Qt 的 ibus im-module） | 应用自己的上下文 | daemon → 应用（**这正是现在会回退剪贴板的场景**） |
| 无可编辑焦点 | 空，或 fake_context | 静默丢弃 → 必须提前判定，见 4.4 |

### 4.4 风险与对策

| 风险 | 对策 |
|---|---|
| `focused_context` 为空，或是 fake_context 时提交被**静默丢弃**（违反"不丢文本"） | 扩展监听 `IBusManager` 的 `focus-in`/`focus-out`，记录当前上下文的 path；没有真实上下文时返回 ERR，客户端走剪贴板 |
| 用户恰好打开了 emoji 选择器 | 极少见；文本会进入 emoji 扩展，可以接受，或者同样视为 ERR |
| `_panelService` 是 gnome-shell 私有字段，大版本升级可能改名 | 与现在依赖 `Main.inputMethod` 的风险等级相同；字段不存在时自动退回现有的 `Main.inputMethod.commit` 路径 |
| 纯 XIM 应用（Java、Wine、老 X11 程序） | 取决于 gnome-shell 是否以 `--xim` 启动 daemon（main 分支源码中没有固定传入），列入 POC 验证 |
| Electron/Chromium（只支持 text-input-v1 或走 X11） | 走 X11 时属于上表第二行，可能反而**优于**现状；列入 POC |

## 5. 非 GNOME + IBus：临时切换全局引擎

适用环境：KDE、XFCE 等桌面上用 IBus 的用户，此时 Panel 被 `ibus-ui-gtk3` 或 Plasma 的 kimpanel 占用，无法借用。

做法：安装一个 `nextalk` IBus 引擎（component XML 放到 `/usr/share/ibus/component/`）；Nextalk 进程调用 `ibus_bus_set_global_engine("nextalk")` → 引擎在焦点上下文上 `commit_text()` → 再切回用户原来的引擎。daemon 的 `ibus-global-engine` 测试覆盖了这个切换流程，从机制上看可行。

| 问题 | 影响 |
|---|---|
| 切换引擎会重置用户引擎的状态（预编辑、中英文模式） | 违反判定标准 3，体验上有感知 |
| 托盘图标、输入法指示器会闪一下 | 体验瑕疵 |
| 需要 `ibus write-cache` / 重启 daemon 才能注册引擎 | 安装流程更复杂 |
| ADR-001 曾否定 "Engine" 路径，但具体原因已丢失 | 很可能就是上面几条，**重新投入前务必先做 POC** |

结论：技术上能做到"可用"，但做不到"完美"。这部分用户量小，**建议继续引导改用 Fcitx5**，暂不投入。

## 6. 其他已排除的方向（2026 年状态）

- **mutter 的 input-method-v1/v2**：GNOME 仍未实现 `zwp_input_method_v2`，本次检索也没有发现新进展。GNOME 48 只新增了 text-input-v1（为 Electron 服务），这是客户端一侧的协议，对注入没有帮助。
- **libei / RemoteDesktop portal**：只能发送 keycode/keysym，不能上传自定义 keymap，因此打不出中文。
- **wtype / ydotool**：GNOME 不支持 `zwp_virtual_keyboard_v1`；ydotool 打不出非 ASCII 字符（结论与 SCP-002 一致）。

## 7. 发行版默认输入法（⚠️ 大部分未经一手来源核实）

| 发行版 | 默认框架 | 来源 |
|---|---|---|
| Fedora Workstation（GNOME） | IBus | 项目内 2026-07 VM 实测（Fedora 43） |
| Ubuntu 26.04 | IBus 默认，Fcitx5 可选 | ubuntu.fan（第三方文档，未核实） |
| Debian 13（中文 task） | Fcitx5 | 项目内 VM 实测（规格文档） |
| KDE Plasma 6 | 官方推荐 Fcitx5（通过虚拟键盘设置选择） | 未核实 |
| Deepin / openKylin 等国产发行版 | Fcitx5 | 未核实 |

格局与 2025 年相比没有本质变化：**GNOME 系发行版用 IBus，其余以 Fcitx5 为主**。所以把 GNOME + IBus 做到完美，基本就覆盖了 IBus 用户的主体。

## 8. 建议的 POC（Fedora 43 VM，GNOME 49 + IBus，不运行 fcitx5）

1. 在 `addons/gnome` 扩展中新增实验方法 `CommitTextViaPanel(text)`，内部调用 `getIBusManager()._panelService.commit_text(...)`，并通过 `focus-in`/`focus-out` 记录当前上下文的 path。
2. 测试矩阵：每个场景都用 `stty -icanon; cat` 或在文本框中读回，确认文字逐字一致。

| # | 焦点 | 期望 |
|---|---|---|
| 1 | ptyxis（Wayland） | 上屏 |
| 2 | ptyxis（`GDK_BACKEND=x11`） | **上屏**（现状为 ERR → 剪贴板） |
| 3 | xterm（XIM） | 记录实际结果 |
| 4 | Qt X11 应用 / Electron（VS Code） | 记录实际结果 |
| 5 | 文件管理器（无可编辑焦点） | 返回 ERR，不能静默丢弃 |
| 6 | 拼音引擎中英文模式 / 预编辑中途 | 不改变引擎状态 |
| 7 | 打开 emoji 选择器（Super+.） | 记录实际行为 |

3. 如果第 1、2、5 项都通过：扩展的 `CommitText` 改为优先走 Panel 通道，失败时退回 `Main.inputMethod.commit`，再失败才回退剪贴板；同时可以去掉 `Meta.WindowClientType.X11` 这层防护。客户端协议和 Fcitx5 路径都不需要改动。

### 8.1 POC 实测结果（2026-11-01）

环境：Fedora 43、GNOME Shell 49.1、ibus 1.5.33~rc2，`ibus-daemon --panel disable`（**没有 `--xim`**），fcitx5 进程数为 0；扩展为实验版 `CommitTextViaPanel`（`addons/gnome/nextalk@gonewx.com/extension.js`）。终端场景用 `stty -icanon; cat > 文件` 读回比对。

| # | 焦点 | `CommitTextViaPanel` | 旧 `CommitText` | 结论 |
|---|---|---|---|---|
| 1 | ptyxis（Wayland） | OK，读回逐字一致 | OK | ✅ |
| 2 | ptyxis（`GDK_BACKEND=x11`，XWayland） | **OK，读回逐字一致** | ERR（X11 不可达）→ 剪贴板 | ✅ **核心收益** |
| 3 | xterm（XIM） | 未测：VM 没装 xterm，也没有 sudo；且 daemon 未带 `--xim`，预计到达不了 | — | ⏸ |
| 4 | Firefox 地址栏（Wayland 原生 GTK） | OK，截图确认上屏 | — | ✅ |
| 4' | Qt X11 / Electron | 未测（VM 中未安装） | — | ⏸ |
| 5 | Nautilus（无可编辑焦点） | ERR: no focused ibus input context | ERR | ✅ 不会静默丢字 |
| 5' | 所有窗口都关闭（只剩桌面） | ERR: no focused ibus input context | ERR | ✅ |
| 6 | libpinyin 中文模式，预编辑 "ni hao" 显示中 | OK；文本插在预编辑**之前**，预编辑和候选框保留，引擎仍为 libpinyin | — | ✅ 不破坏输入法状态 |
| 7 | emoji 选择器 | 未测（罕见场景） | — | ⏸ |

补充观察：

- 扩展启用（重新登录）后，在第一次焦点切换之前调用会返回 `ERR: focus state unknown`，符合设计（走剪贴板兜底）。
- 空字符串也会返回 OK；客户端本来就不会发送空文本，正式版可以顺手拦截。
- 焦点在"子进程已退出"的 XWayland 终端上时返回 OK，但文本被终端丢弃。这是应用层行为，与通过键盘输入时一致，不属于 IBus 通道的问题。
- 测试时发现：从 SSH 启动的窗口拿不到焦点（GNOME 的防焦点抢夺机制），所以测试窗口需要从会话内的终端启动。

**正式版回归（2026-11-01，同一 VM，重新登录后）**：`CommitText` 已改为"Panel → Main.inputMethod → ERR（剪贴板）"链。实测结果：
- Wayland 终端：OK，读回一致；
- XWayland 终端：OK，读回一致；
- Nautilus：返回 `ERR: panel(no focused ibus input context); im(no active text input in focused window)`；
- 空文本：返回 `ERR: empty text`。

**结论**：第 1、2、5、6 项全部通过，Panel 通道可以同时覆盖 Wayland 原生窗口和 XWayland 窗口，并且能正确识别"无焦点"。可以进入正式化：扩展的 `CommitText` 改为优先走 Panel，失败时依次退回 `Main.inputMethod.commit` 和剪贴板。

## 9. 参考

- ibus 源码：`bus/panelproxy.c`（`bus_panel_proxy_commit_text`）、`bus/inputcontext.c`（`bus_input_context_commit_text_use_extension`）、`bus/ibusimpl.c`、`src/ibuspanelservice.c`
- gnome-shell：`js/misc/ibusManager.js`、`js/misc/inputMethod.js`（https://gitlab.gnome.org/GNOME/gnome-shell）
- 项目内：`_bmad-output/sprint-change-proposals/scp-002-simplified-architecture.md`、`_bmad-output/implementation-artifacts/spec-fix-fedora-inject-clipboard-fallback.md`
- Ubuntu 26.04 输入法说明（第三方）：https://ubuntu.fan/docs/desktop-use/basics/input-method
- mutter text-input-v1 补丁：https://build.opensuse.org/projects/GNOME:STABLE:48/packages/mutter/files/mutter-implement-text-input-v1.patch?expand=0
