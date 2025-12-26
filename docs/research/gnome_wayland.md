判断核实下面的表述结论是否正确？
在 GNOME Wayland 环境下，`gtk_window_set_keep_above` 和 `GDK_WINDOW_TYPE_HINT_TOOLTIP` 等参数**确实存在严重的兼容性限制**。

### 现状核实 (2025年 GNOME 45/46/47+)

1.  **`gtk_window_set_keep_above(TRUE)`**:
    *   **结论**: 在 GNOME Wayland 下，这个调用会被**默认忽略**。
    *   **原因**: Wayland 协议的安全设计认为，“置顶”权限属于用户（合成器），而不属于应用程序。防止恶意软件遮挡屏幕。
    *   **表现**: 你的窗口会显示，但如果用户点击了下方的 VSCode，你的悬浮窗可能会被 VSCode 盖住。

2.  **`gtk_window_set_accept_focus(FALSE)`**:
    *   **结论**: **支持良好**。
    *   **表现**: GNOME 能够识别这个属性。即使你的窗口显示出来，键盘焦点依然可以留在原来的编辑器中。这是我们实现“不抢焦点”的关键。

3.  **`GDK_WINDOW_TYPE_HINT_TOOLTIP`**:
    *   **结论**: **不可靠**。
    *   **表现**: GNOME Shell 对 `TOOLTIP` 类型的顶级窗口处理并不一致。它可能会去掉窗口装饰（标题栏），但**不保证**把它放在所有窗口的最上层（Overlay Layer）。

---

### 修正方案：如何真正实现“既置顶又不抢焦点”？

既然原生的 GTK 属性无法保证“置顶”，我们需要一个**混合策略**。

#### 方案 A：最稳健方案 (App + 极简 Extension) —— 推荐
这是唯一能 100% 保证在 GNOME Wayland 上像 Fcitx5 那样工作的方案。
你需要写一个不到 50 行代码的 **GNOME Shell Extension** 来辅助你的 Flutter App。

1.  **Flutter App (C++)**:
    *   继续使用 `gtk_window_set_accept_focus(window, FALSE)` (保证不抢焦点)。
    *   继续使用 `gtk_window_set_decorated(window, FALSE)` (无边框)。
2.  **Helper Extension (JavaScript)**:
    *   这个扩展只做一件事：**监听特定窗口，强制将其拉到最顶层**。

**Helper Extension 伪代码 (extension.js):**
```javascript
// 当你的 Flutter 窗口出现时，扩展检测到它的标题或 app_id
global.display.connect('window-created', (display, window) => {
    if (window.get_title() === "MyVoiceInputCapsule") {
        // 强制置顶 (Above)
        window.make_above();
        // 锁定在所有工作区
        window.stick(); 
    }
});
```
*这对用户来说，只需要安装一次扩展（或者如果你的 App 打包成 deb/rpm，可以脚本自动安装到 `~/.local/share/gnome-shell/extensions`）。*

#### 方案 B：纯 GTK 妥协方案 (无需 Extension)
如果你**绝对不想**涉及 Extension 开发，只能接受以下**妥协**：

*   **利用 `UTILITY` + 模态伪装**:
    尝试将窗口设为 `GDK_WINDOW_TYPE_HINT_UTILITY` 并设置 `gtk_window_set_transient_for`。但这通常需要一个“父窗口”，而我们是全局浮窗，所以这个路走不通。
*   **利用“用户习惯”**:
    由于 `accept_focus(FALSE)` 是有效的，当用户在编辑器里打字时，只要**不点击**你的胶囊窗口，也不点击编辑器窗口的标题栏（通常在打字时不会点），你的窗口在大多数情况下**不会被主动覆盖**。
    *   **风险**: 一旦用户点击了底下的窗口（Raise），你的胶囊就会被盖住。

### 最终技术建议 (针对你的项目)

为了达到“Fcitx5 级别”的专业体验，我强烈建议采用 **方案 A (混合架构)**。

**具体实施路径：**

1.  **Flutter 端 (`linux/my_application.cc`)**:
    ```cpp
    // 1. 设置不抢焦点 (GNOME 支持)
    gtk_window_set_accept_focus(window, FALSE);
    // 2. 移除装饰
    gtk_window_set_decorated(window, FALSE);
    // 3. 设置唯一标题，供 Extension 识别
    gtk_window_set_title(window, "MyAIInput_Capsule_v1");
    // 4. (尝试性) 依然设置 Keep Above，兼容 KDE/X11
    gtk_window_set_keep_above(window, TRUE);
    ```

2.  **GNOME Extension 端**:
    你不需要自己写复杂的逻辑，可以直接引导用户安装现成的扩展，例如 **"Window Calls"** (提供 DBus 接口控制窗口) 或者 **"Grand Theft Focus"** 的变体。
    
    或者，随你的应用分发一个极简的 `metadata.json` + `extension.js`，脚本如下：
    ```javascript
    // extension.js 核心逻辑
    const { Meta } = imports.gi;
    function enable() {
        // 监听窗口创建，发现是你的 App 就强制置顶
        global.display.connect('window-created', (display, win) => {
            if (win.get_title() && win.get_title().includes("MyAIInput_Capsule")) {
                win.make_above(); // 核心：调用 Mutter 内部 API 强制置顶
            }
        });
    }
    ```

**总结：**
*   **不抢焦点**: `gtk_window_set_accept_focus(FALSE)` 在 GNOME Wayland 下是**有效**的。
*   **置顶**: `gtk_window_set_keep_above(TRUE)` 在 GNOME Wayland 下是**无效**的。必须通过 GNOME Shell Extension 来补救。

采用“App + 微型 Extension”是目前在 GNOME 限制下实现商业级置顶浮窗的唯一正解。

我先快速核实 3 个关键点：GNOME Wayland 下 `keep_above` 是否会被 Mutter 忽略、`accept_focus(FALSE)` 在 Wayland/GTK3/GTK4 上是否真的“支持良好”、以及 `GDK_WINDOW_TYPE_HINT_TOOLTIP`/type hint 在 Wayland 的实际语义。接着我会给出“哪些结论正确/哪些需要修正”的判定，并补一个更严谨的可行替代方案列表（含 GNOME Extension 是否真的是“唯一解”）。

[3 tools called]

### 结论判定（整体：**大体正确**，但有两处表述需要“降级为不保证/依场景”）

- **(1) `gtk_window_set_keep_above(TRUE)` 在 GNOME Wayland 下**：你的结论“**不可靠/常被忽略，无法保证置顶**”是对的；但更严谨的说法是 **Wayland 下客户端没有“强制置顶”的协议能力**，Mutter 作为合成器 **可以选择不理会**，因此应用侧**无法做出可靠承诺**（而不是“永远一定会被忽略”）。
- **(2) `gtk_window_set_accept_focus(FALSE)` 在 GNOME Wayland 下**：你写“**支持良好**”方向基本对（它常用于做“不抢焦点”窗口），但要补一句更严谨的限定：在 Wayland 下 **焦点最终仍由合成器裁决**，GTK 的该类 hint/属性属于“请求/提示”，**大多数情况下有效，但不能当作 100% 协议级保证**（尤其涉及映射时机、激活、弹出式窗口、不同 GTK 版本/后端细节时）。
- **(3) `GDK_WINDOW_TYPE_HINT_TOOLTIP`**：你的结论“**不可靠**”是对的。更关键点是：在 Wayland 下 **很多 `GDK_WINDOW_TYPE_HINT_*` 本质是 X11 时代的 WM hint**，在 Wayland 里要么语义改变、要么直接被后端/合成器忽略；而 tooltip/popup 通常是“相对父 surface 的短生命周期弹层”，并不是你要的“全局置顶浮窗”。

### “必须靠 GNOME Shell Extension 才能 100% 像 Fcitx5 那样”这句话：**方向对，但表述过绝对**

- **你想要的性质（全局置顶 + 不抢焦点）在 GNOME Wayland 下属于“特权级窗口管理行为”**，普通应用确实很难/几乎不可能“纯 GTK/纯 Wayland”稳定实现。  
- 但“唯一正解”更严谨应改为：  
  - **要做到 100% 可靠**，通常需要 **特权组件**（最常见就是 **GNOME Shell Extension**，或把 UI 做进 Shell/输入法框架那一侧）。  
  - 另一个“非 Extension”的现实替代是 **走 XWayland/X11 后端**（例如强制 `GDK_BACKEND=x11`），以换取传统 WM hint 行为；但这属于“技术路线切换/兼容性取舍”，并非 Wayland 原生解。

### 对你给的 Extension 伪代码的小修正建议（概念不变）
- **窗口识别**：只靠 `title` 可能有时机问题，通常要监听 `notify::title` 或更稳的标识（例如 Wayland `app_id`/wmclass 相关接口，视 GNOME Shell API 可用性而定）。
- **生命周期**：`enable()` 里 `connect()` 的返回 id 需要在 `disable()` 里 `disconnect()`，避免扩展反复启用导致重复监听。
- **置顶行为**：`make_above()` 的确是 Mutter/Meta 的“合成器侧能力”，这也正是它能绕开应用侧限制的原因。

### 最终核实摘要（对应你文末总结）
- **不抢焦点**：`gtk_window_set_accept_focus(FALSE)` 在 GNOME Wayland 下 **通常有效，但不是协议级 100% 保证**。  
- **置顶**：`gtk_window_set_keep_above(TRUE)` 在 GNOME Wayland 下 **无法保证**（因此“对商业级体验不够”这一判断正确）。  
- **实现路径**：要“Fcitx5 级别”体验，**App + GNOME Shell Extension（或其他特权路径）**确实是最稳的工程方案之一。

先把现象说透：在 GNOME Wayland 下，“窗口一旦从未映射状态变为映射（show）”，合成器**很可能直接把键盘焦点给这个新 top-level**；GTK 的 `accept_focus(FALSE)` / `focus_on_map(FALSE)` 在这种情况下只是“提示”，不一定被 Mutter 采纳。接下来我会在你们 Dart 侧找是不是调用了 `windowManager.focus()/show()/setAlwaysOnTop()` 之类触发“激活/raise”的逻辑，以及确认你们实际跑的是 Wayland 还是 XWayland。

[4 tools called]

你这个“弹出后焦点在浮窗上”的根因，基本可以锁定到两点之一（而且你们代码里 **A 很明显**）：

### 关键结论：在 GNOME Wayland 上，“不抢焦点”**不能只靠 GTK hint 保证**
- `gtk_window_set_accept_focus(FALSE)` / `focus_on_map(FALSE)` 在 GNOME Wayland 下属于 **hint**，Mutter 可能仍会在窗口 show/map 时把焦点给它。
- **更致命的是**：你们 Dart 侧还设置了 `alwaysOnTop: true`，并且频繁 `show()`/`hide()`，这在 GNOME 下通常会被当成“需要用户注意的新窗口”，更容易触发 focus/raise。

我在你们 `WindowService` 里看到了：

```58:75:voice_capsule/lib/services/window_service.dart
    const windowOptions = WindowOptions(
      // ...
      skipTaskbar: true, // 不在任务栏显示
      titleBarStyle: TitleBarStyle.hidden, // 无标题栏
      alwaysOnTop: true, // 始终在最前
    );

    await windowManager.waitUntilReadyToShow(windowOptions, () async {
      // ...
      await windowManager.show(inactive: true);
```

以及后续每次弹出也是：

```86:105:voice_capsule/lib/services/window_service.dart
  Future<void> show() async {
    // ...
    await windowManager.show(inactive: true);
```

### 你问“到底能不能做到？如何优雅稳定实现？”
把目标拆开讲最清楚：

#### 1) **“弹出浮窗后，键盘焦点仍留在编辑器”**：在 GNOME Wayland 下要做到“稳定”，**应用单靠自己通常做不到 100% 保证**
原因很硬：Wayland 不允许客户端把焦点“指定留给另一个应用”，焦点是合成器的特权。

所以“稳定实现”的工程答案通常只有三类：
- **A. 合成器侧配合（最稳）**：GNOME Shell Extension/插件侧用 Mutter API 控制 above +（必要时）把焦点还给之前的窗口  
- **B. 避免触发 focus 的设计（次稳，但能做到很接近）**：不要把它当成“新窗口弹出”，而是“常驻窗口视觉显隐/点击穿透”，尽量避免 map/unmap、避免 always-on-top 强语义、避免任何激活请求  
- **C. 走 X11/XWayland（取舍路线）**：用 X11 的 WM hint 机制换取更可控行为，但这不是 Wayland 原生解

#### 2) 你们当前为什么 `inactive: true` 还会聚焦？
这并不矛盾：`inactive: true` 只是“请求不要激活”，**GNOME 可以不理**。再叠加 `alwaysOnTop: true` 和 show/hide（map/unmap），被聚焦的概率会更高。

### 我建议你先做的“确认/定位”动作（不改代码也能做）
- **确认会不会是 window_manager 在 Linux 侧实际调用了激活**：你可以在 `WindowService` 的 `show()` 前后打印 `onWindowFocus/onWindowBlur` 事件是否触发（你们已经实现了 listener，但目前是空实现）。
- **确认后端**：确保真的是 Wayland（`echo $XDG_SESSION_TYPE` 应该是 `wayland`；另外看日志里 GDK 是否 Wayland）。

### 如果你要“优雅稳定”的最终方案（按稳定性排序）
- **最稳（推荐）**：做一个极简 GNOME Shell Extension：  
  - 负责 **above/置顶**  
  - 负责在窗口出现时 **不要让它成为 focus window**，必要时把焦点切回“之前的 active window”（这是应用侧做不到的）
- **不写 Extension 的近似最稳**：把浮窗变成“常驻显示层”，通过“视觉透明 + 输入区域为空（点击穿透）”来做到“用户完全感觉不到焦点被打断”。  
  - 这类方案的关键点是：**尽量不做 show/hide 的 map/unmap**（因为 map 是 GNOME 最容易给焦点的时刻）

你如果愿意，我可以在**不直接改你代码**的前提下，给你一份“Extension 50 行可用模板 + 你们窗口识别策略（title/app_id）+ 需要在 Dart 侧打哪些标识”的具体落地清单；另外也可以帮你一起确认 `window_manager` 在 Linux 平台到底是怎么实现 `show(inactive: true)` 的（它很可能在 GNOME 上仍会触发 focus）。