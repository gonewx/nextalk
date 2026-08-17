---
title: '修正胶囊窗口位置：默认屏幕底部居中 + 记忆用户调整后的位置'
type: 'bugfix'
created: '2026-08-17'
status: 'done'
baseline_commit: 'ec5f6e516a55169842a9ef36712173a88f446253'
review_loop_iteration: 1
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 胶囊每次都出现在屏幕左上角，用户拖动过后下次仍还原到左上角。根因是三重叠加故障：(1) `nextalk-toggle` 脚本冷启动时走 `exec nextalk --toggle`，绕过了 `.desktop` 里的 `GDK_BACKEND=x11`，应用以原生 Wayland 运行——实测该后端下 `gtk_window_move()` 完全 no-op、`gtk_window_get_position()` 恒返回 `(0,0)`，于是默认定位失效且 `savePosition()` 把 `(0,0)` 写进 prefs（已在 `~/.local/share/nextalk/shared_preferences.json` 中确认为 `0.0/0.0`）；(2) `isValidPosition(0,0)` 判定为 true，于是后续即便以 XWayland 启动也会忠实"恢复"到左上角；(3) window_manager 的 Linux 端只发射 `move` 事件、从不发射 `moved`，所以 `onWindowMoved()` 永不触发，拖动结束后没有任何保存时机。

**Approach:** 在 runner 层把 GDK 后端锁定为 x11（保留用户显式覆盖的逃逸阀），使定位 API 真实可用；默认位置改用显示器工作区（workarea）计算底部居中，修正多显示器下缺失屏幕偏移的算法缺陷；给位置保存加脏值守卫并把 `(0,0)` 视为无效遗留值；改用 `onWindowMove` + 防抖来落地拖动后的位置保存。

## Boundaries & Constraints

**Always:**
- 后端锁定必须是"仅在未显式设置时"生效（`setenv(..., overwrite=0)`），用户显式指定 `GDK_BACKEND` 时不覆盖。
- 默认位置必须基于 workarea 的**绝对坐标**（含显示器偏移），不得只用 `size` 做居中——实测主显示器 geometry 为 `2560,0`，workarea 为 `2618,32 2502x1408`，忽略偏移会把窗口丢到另一台显示器。
- 保存位置前必须确认窗口当前可见；不可见时读到的坐标不可信，直接跳过保存。
- 恢复位置时必须对存量值做有效性判定，无效则回退到默认位置计算。
- 保持现有透明/无边框/不抢焦点/skip-taskbar 行为不变。

**Ask First:**
- 若实现中发现锁定 x11 后端会破坏托盘图标、Portal 全局快捷键或 fcitx5 文本注入中任何一项，HALT 并向人确认，不要自行放弃后端锁定或改动那些子系统。

**Never:**
- 不引入 layer-shell、GNOME Shell 扩展或任何新的窗口定位依赖。
- 不改动胶囊视觉样式、尺寸常量语义或状态机。
- 不为了绕开问题而移除位置记忆功能。
- 不动 `addons/fcitx5` 与 ASR/音频链路。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 首次运行 | prefs 无位置键 | 窗口出现在主显示器 workarea 底部居中（含显示器偏移与顶栏/Dock 让位） | workarea 查询失败 → 退回 `windowManager.center()` |
| 存量脏值 | prefs 为 `x=0, y=0` | 视为无效，按默认底部居中显示，并清除该脏值 | 无 |
| 用户拖动后 | 拖动结束，窗口可见 | 新坐标写入 prefs（防抖后一次） | 读取坐标抛异常 → 静默跳过，不覆盖已有值 |
| 再次唤起 | prefs 存有有效坐标 | 窗口出现在该坐标 | 坐标已越出当前所有显示器 → 回退默认底部居中 |
| 窗口隐藏时触发保存 | `isVisible == false` | 不写入 prefs，保留上一次有效坐标 | 无 |
| 显示器拔除/分辨率变化 | 存量坐标落在已消失的显示器 | 回退默认底部居中 | 无 |

</frozen-after-approval>

## Code Map

- `voice_capsule/lib/services/flutter_window_backend.dart` -- **主战场**。`_setDefaultPosition()` (L146-162) 只用 `primaryDisplay.size` 居中、**丢了显示器 x/y 偏移**且底边距硬编码 80；`savePosition()` (L92-102) 无任何守卫、`_isVisible` 未参与判断；`_restorePosition()` (L130-144) 依赖 `WindowConstants.isValidPosition`；`onWindowMoved()` (L178-181) 在 Linux 永不触发；`onWindowMove()` (L175) 为空实现——保存时机应挂在此处。
- `voice_capsule/lib/constants/window_constants.dart` -- `isValidPosition()` (L40-45) 用固定矩形 `-200..4000 / -50..2500` 粗判，`(0,0)` 被判为有效；位置键名 `nextalk_window_x/y` (L29-30)。默认底边距需在此新增常量。
- `voice_capsule/linux/runner/main.cc` -- 仅 3 行，`g_application_run` 之前是设置 `GDK_BACKEND` 的唯一正确时机（必须早于 GTK/GDK 初始化）。
- `voice_capsule/linux/runner/my_application.cc` -- `my_application_activate()` 已含透明/无边框/不抢焦点配置与 `gtk_window_set_default_size(400,120)`；**只读参考**，本次不改。
- `scripts/nextalk-toggle.sh` -- L38-42 无实例时 `exec nextalk --toggle` / `exec /opt/nextalk/nextalk --toggle`，这是绕过 `.desktop` env 的实际入口。
- `packaging/deb/com.gonewx.nextalk.desktop` -- L10 已有 `Exec=env GDK_BACKEND=x11 ...`，证明 XWayland 是项目既定路线（story 3-1 亦有记载），本次只是让该路线在所有入口一致生效。
- `voice_capsule/lib/services/window_service.dart` -- 转发层。`savePosition()` (L138-141)、`startDragging()` (L144-147)、`onWindowMoved()` (L157-159)。注意：该类 `with WindowListener` 但**从未 `addListener` 注册**，其回调是死代码；真正生效的监听者是 `FlutterWindowBackend`。
- `voice_capsule/lib/ui/capsule_widget.dart` -- L60 `DragToMoveArea` 是唯一拖动入口（内部走 `windowManager.startDragging()`）。只读。
- **只读证据（无需重新验证）**：
  - `window_manager-0.5.1/linux/window_manager_plugin.cc` L1116 把 `configure-event` 绑到 `on_window_move`，L1003-1007 只 `_emit_event(plugin, "move")`；全文件无任何 `"moved"` 发射 → `onWindowMoved` 在 Linux 是死回调。
  - 同文件 L264-289：`getBounds` 用 `gtk_window_get_position`、`setBounds` 用 `gtk_window_move`；Dart 侧 `getPosition()`/`setPosition()` 分别转发到 `getBounds`/`setBounds`。
  - `screen_retriever_linux-0.2.0` plugin L49-70：`size` 来自 `gdk_monitor_get_geometry` 的 w/h，`visiblePosition`/`visibleSize` 来自 `gdk_monitor_get_workarea` 的 x,y / w,h → **`visiblePosition` 就是本次需要的绝对偏移**。

## Tasks & Acceptance

**Execution:**

- [x] `voice_capsule/linux/runner/main.cc` -- **改用 GDK 原生回退链** `setenv("GDK_BACKEND", "x11,wayland", 0)`，取代自研的 `getenv("DISPLAY")` 探测（`#include <stdlib.h>`）。实测对照：`x11,wayland` 在 X 可用时选 x11、无 DISPLAY 时回落 wayland、**`DISPLAY=:99` 不可达时也回落 wayland**；而"仅 x11 + DISPLAY 探测"在最后一种情形下 `gtk_init_check FAILED` —— 纯 Wayland 会话的残留 `DISPLAY=:0` 与失效的 SSH X 转发都会命中该盲区。加中文注释说明回退链语义与"可启动性优先"的取向。

- [x] `scripts/nextalk-toggle.sh` -- 冷启动回退路径注入 `GDK_BACKEND="${GDK_BACKEND:-x11,wayland}"`（与 runner 同一回退链语义），未显式设置才注入；`GDK_BACKEND=""` 视同未设置。注释标明这是过渡期双保险（兼容旧版二进制），runner 落地后可移除。

- [x] `voice_capsule/lib/constants/window_constants.dart` -- 新增 `defaultBottomMargin`；`isValidPosition` 改为可传显示器工作区列表判定，`(0,0)` 判为无效遗留值。三点约束：(a) 判定必须按**工作区并集/累计可见面积**，不可要求"在单个工作区内 ≥50%"——横跨两台相邻显示器时对任一屏都不足半数，而多显示器正是本次主场景；(b) 注释措辞必须与实现一致（逐轴阈值就写逐轴，别写"可见面积"）；(c) 兜底矩形 `positionMaxX=4000`/`positionMaxY=2500` 必须放宽到覆盖常见多屏总跨度（本机双屏总宽已达 5120，实测坐标 4600 合法），否则显示器查询失败时反而误判合法坐标。

- [x] `voice_capsule/lib/services/flutter_window_backend.dart` -- 位置逻辑落点，七项要求：(a) 默认位置用 `visiblePosition`+`visibleSize` 算工作区底部居中（缺失退回 `size` 与零偏移）；工作区尺寸非正、或算出的默认位置正好等于 `(0,0)` 时必须回退 `center()`，避免默认值撞上脏值哨兵而永远无法持久化。(b) `savePosition()` 守卫窗口可见性与 `(0,0)` 脏值。(c) `_restorePosition()` 校验存量坐标；**无效时不得一律删除 prefs 键**——只有 `(0,0)` 脏值签名才删，越界坐标本次不用即可（显示器热插拔/会话切换时 `getAllDisplays()` 可能返回不完整集合而不抛异常，删除会不可恢复地丢掉副屏位置）；更优做法是越界时**钳位到最近工作区**以保留用户意图。(d) 保存时机挂 `onWindowMove` + 防抖，但**必须在程序化改变窗口几何期间抑制保存**——`setSize()`/`setPosition()`/`setExpandedMode()`/`setInitWizardSize()` 都会触发 `configure-event`；**已实测：在 `4600,1300` 处 resize 后窗口被 WM 平移到 `4580,900`，该非用户意图坐标被当成"用户位置"写入 prefs**，导致向导/展开态之后胶囊永久停在错位处。(e) 保存需串行化（in-flight 标志或互斥），避免防抖回调与 `hide()` 的保存交叠后用旧读值覆盖新坐标。(f) 退出路径必须真正落盘：`dispose()`/`onWindowClose()` 原本是未 await 的 fire-and-forget，防抖引入后风险窗口放大（拖动后 400ms 内退出，唯一机会正是这条）——改为可等待的 flush，并在 timer 仍活跃时先立即保存再取消。(g) 校验/定位当前窗口时必须使用**当前实际窗口尺寸**，不能一律按胶囊 400×120——向导态 540×540 若按胶囊尺寸算底部对齐会溢出工作区、按钮点不到。

- [x] `voice_capsule/test/` -- 单元测试必须覆盖**真实接线**，不止纯谓词。**已实测：把 `onWindowMove()` 改回空实现（原样重现根因之三、主症状必然回归），全部 737 项测试依然通过**——纯谓词覆盖对本次修复零保护力。沿用仓库既有插件打桩方式（见 `test/utils/clipboard_helper_test.dart` 的 `TestDefaultBinaryMessengerBinding...setMockMethodCallHandler`）给 `window_manager` / `screen_retriever` 的 MethodChannel 打桩，配 `SharedPreferences.setMockInitialValues`，至少断言：连续多次 `onWindowMove()` 只落盘一次且为最后坐标；隐藏态调 `savePosition()` 后 prefs 不变；`hide()` 返回后 prefs 已含隐藏前最新坐标；存量 `(0,0)` 经恢复流程后键被清除且 `setPosition` 收到底部居中坐标；程序化 `setSize()` 不产生位置写入。期望值不要硬编码几何算术结果，应由被测常量推导，使常量变更时以"意图被违反"而非"数字不对"的形式失败。

- [x] `scripts/verify-transparent-window.sh` -- 补一条**会失败**的后端锁定检查：该脚本现用 `xdotool search voice_capsule` 找窗口，实测匹配 0 个（应用实际标识是 `com.gonewx.nextalk`），找不到时只 `SKIP=3` 不计 FAIL，等于永不报错。改为按 `com.gonewx.nextalk` 查找，查不到即 FAIL，并断言唤起后窗口几何非 `+0+0` -- 否则一次无关重构就能悄悄摘掉后端锁定而所有验证仍报通过。

- [x] `docs/development-pitfalls.md`（及 `_zh` 版本，含文首目录） -- 记录两件事：Wayland 原生 vs XWayland 的定位 API 实测对照（见 Design Notes 的探针输出），以及"应用进程强制 XWayland（且以存在 X display 为前提）"这一影响托盘、Portal 快捷键、fcitx5 注入的全局决策 -- 这是项目既定的踩坑归档地，本次是典型的环境级陷阱。

**Acceptance Criteria:**

- Given prefs 中 `nextalk_window_x/y` 为 `0.0/0.0`，when 唤起胶囊，then 窗口出现在主显示器工作区底部居中，且这两个键被清除或被覆盖为新的有效坐标。
- Given 应用经由 `nextalk-toggle` 在无运行实例时冷启动，when 进程启动完成，then 它运行在 x11/XWayland 后端上——判据为 X11 客户端（`xwininfo -root -tree`）能看到 `com.gonewx.nextalk` 窗口，且 `gtk_window_get_position` 返回非 `(0,0)` 的真实坐标。
  - **注意**：不要用 `/proc/<pid>/environ` 判定 runner 层的锁定。`/proc/<pid>/environ` 反映的是 `execve` 时的初始环境块，`setenv()` 在进程内的修改不会出现在其中（已实测确认）。该判据只对 `nextalk-toggle.sh` 的 `exec env GDK_BACKEND=...` 路径成立。
- Given 用户把胶囊拖到屏幕任意位置并松手，when 隐藏后再次唤起（含重启应用后），then 胶囊出现在用户拖动后的位置，误差不超过窗口边框级别的若干像素。
- Given 主显示器在多屏布局中带非零 x 偏移，when 首次运行计算默认位置，then 窗口完整落在主显示器内、水平居中、底部留出约 80px 且不被顶栏或 Dock 遮挡。
- Given 窗口处于隐藏状态，when 任何代码路径触发 `savePosition()`，then prefs 中已有的有效坐标不被覆盖。
- Given 现有透明胶囊、托盘图标、全局快捷键与 fcitx5 文本上屏功能，when 完成本次修改，then 这些功能行为与修改前一致。
- Given 一个没有 X display 的环境（`env -u DISPLAY`，模拟无 XWayland 的精简发行版/容器/远程会话），when 启动应用，then 应用**必须能正常启动**（不得出现 `cannot open display` 或非零退出）；此时位置功能允许降级，但可启动性优先。
- Given 用户把胶囊拖到某处后，程序因错误态展开或进入初始化向导而调用 `setSize()`，when 窗口被 WM 因改尺寸而平移，then prefs 中记录的仍是用户拖动的位置，不被程序化平移后的坐标覆盖。
- Given 用户拖动胶囊后在防抖窗口内（<400ms）立即退出应用，when 应用完成退出，then 拖动后的位置已落盘，下次启动出现在该位置。
- Given 存量坐标落在一台当前查询不到的显示器上（热插拔/会话切换），when 执行恢复流程，then 该坐标**不被从 prefs 删除**（本次可回退默认位置或钳位显示），显示器恢复后原位置仍可用。
- Given 把 `onWindowMove()` 改回空实现（原样重现根因之三），when 运行测试套件，then **必须有测试失败** —— 测试须真正保护拖动后位置记忆这条链路。
- Given 后端锁定被移除（`main.cc` 的 setenv 被删），when 运行 `scripts/verify-transparent-window.sh`，then 必须报 FAIL 而非"跳过"。

## Spec Change Log

### 迭代 2 — 2026-08-17（第二轮评审，定向修补，未回退代码）

**处置方式偏离说明：** 本轮存在 2 项 `bad_spec` 级发现，按严格级联规则应回退全部代码重新派生。经与人确认后改为**定向修补**：第二轮实现已通过全部端到端验证（默认底部居中 `+3669+1240`、拖动持久化、重启恢复、脏值清除、程序化 resize 不污染），推倒 840 行已验证正确的代码代价与收益不成比例。`review_loop_iteration` 保持 1。

**触发发现（两条均由 leader 实证）：**

1. **`GDK_BACKEND=x11,wayland` 回退链优于本 spec 指定的 DISPLAY 探测**。原 Tasks 把"探测 `getenv("DISPLAY")` 非空"写成了具体做法，它漏掉"DISPLAY 有值但 X server 不可达"（纯 Wayland 会话残留的 `DISPLAY=:0`、失效的 SSH X 转发）。实测对照：

   | 场景 | `x11,wayland` | 仅 `x11` + DISPLAY 探测 |
   |---|---|---|
   | X 可用 | ok, backend=x11 | ok, backend=x11 |
   | 无 DISPLAY | ok, backend=wayland | 跳过注入 → wayland |
   | `DISPLAY=:99`（不可达） | ok, backend=wayland | **gtk_init_check FAILED** |

   GDK 原生回退链把可用性判断交给 GDK，覆盖更全，并可删掉三处入口的自研探测逻辑。

2. **测试挡不住"事件从未被订阅"**。实测删除 `windowManager.addListener(this)` 后 752 项测试**全绿**，而该行缺失会让应用完全收不到 move 事件、位置永不保存。wiring 测试直接调 `backend.onWindowMove()`，绕过了插件分发注册；原 spec 只要求断言回调行为，未要求断言注册本身。

**同批修补的 patch 级发现：** 镜像/重叠工作区在累计可见面积中被重复计数（25% 可见可被算成 50% 通过）；兜底矩形上界放宽到 16384 但下界仍为 -200/-50，副屏在主屏左侧的合法负坐标会被误杀；`clampToWorkAreas()` 结果未回校 `isValidPosition`；`verify-transparent-window.sh` 在"无 X display 合法降级"场景必然 FAIL，与文档承诺矛盾，且缺 xwininfo/xdotool 时误报为后端回归；wiring 测试未在 tearDown 中 dispose，挂起 timer 跨用例泄漏；`_saveChain` 缺 `.catchError` 兜底（当前抛不出，但属脆弱设计）；`window_service.flushPendingSave()` 无调用方。

**避免的已知坏状态：** 在有残留/失效 `DISPLAY` 的环境里应用仍然启动失败；事件注册被误删而全套测试仍报通过；镜像屏或负坐标布局下用户位置被误判丢弃。

**KEEP —— 第二轮已验证正确，修补时必须存活：**

- `PositionRestoreDecision` 把"清脏值"与"钳位/恢复"分离的设计（精确实现"只清 `(0,0)`、越界不清键"）。
- 程序化抑制用 `_programmaticDepth` 深度计数 + 时间尾巴（自动过期，不会卡死），且进入抑制前先 `flushPendingSave()` 保住用户已拖动的位置。**已实测：resize 后紧接着拖动仍正确保存 `2700,600`，抑制窗不误伤用户操作。**
- `savePosition()` 经 `_saveChain` 串行化；`dispose()`/`flushPendingSave()` 改为可等待。
- 累计可见面积判定取代"单屏 ≥50%"（修跨屏误杀）—— 仅需叠加去重。
- wiring 测试的 MethodChannel 打桩骨架与"改回空 `onWindowMove` 必须失败"这条护栏（已实测生效，2 项失败）。
- `main.cc` / `nextalk-toggle.sh` 里对 Wayland 定位失效原因的解释性注释。

### 迭代 1 — 2026-08-17（三层对抗式评审后回退）

**触发发现（均已由 leader 独立实证，非评审推测）：**

1. **无 X display 时应用完全打不开**（最严重，纯回归）。原 spec 的 Tasks 只要求无条件 `setenv("GDK_BACKEND","x11",0)`，实现忠实照做。实测 `env -u DISPLAY ./voice_capsule` → 退出码 1 + `Gtk-WARNING: cannot open display:`。改动前该环境能启动（仅位置错），改动后启动失败——把"位置不对"升级为"完全打不开"。
2. **新增测试对主症状零保护力**。原 spec 的测试任务写了"纯函数化不可测的部分用薄封装或跳过并在测试里注明"，等于授权跳过接线验证。实测把 `onWindowMove()` 改回空实现（原样重现根因之三），737 项测试全绿。
3. **程序化 resize 污染位置记忆**。原 spec 只说"保存时机迁到 `onWindowMove` 并加防抖"，未要求抑制程序化几何变更。实测 `4600,1300` 处 resize 后 WM 平移到 `4580,900`，该坐标被写入 prefs。
4. **越界坐标被永久删除 + 兜底矩形与真实硬件矛盾**。原 spec 明确要求"无效时清除 prefs 键"，且沿用了 `positionMaxX=4000`（本机双屏总宽 5120，实测坐标 4600 合法）。显示器查询返回不完整集合时会不可恢复地删掉副屏位置。
5. 保存/恢复判定不对称（保存只拒 `(0,0)`，恢复要求 ≥50% 可见且不满足即删键）；退出路径 fire-and-forget 不保证落盘；并发保存未串行化；向导 540×540 按胶囊 400×120 尺寸校验；跨屏摆放被误判无效；默认位置可能算出 `(0,0)` 与脏值哨兵冲突。

**已修订内容（仅非冻结区）：** Tasks 由 5 项扩为 7 项，逐条写入上述约束与实测证据；新增 7 条验收标准，其中三条是**可失败性判据**（无 DISPLAY 必须能启动、改回空 `onWindowMove` 必须有测试失败、摘掉后端锁定必须 FAIL 而非跳过）。冻结区（Intent / Boundaries / I/O 矩阵）未改动。

**避免的已知坏状态：** 为修位置 bug 而让应用在无 XWayland 环境下无法启动；测试全绿但主症状可整条静默回归；向导/展开态后胶囊永久错位；显示器热插拔导致用户位置被不可恢复删除。

**KEEP —— 以下在重新派生时必须存活：**

- `workAreaOf()` 用 `visiblePosition`/`visibleSize` 提取工作区绝对坐标、缺失时退回 `size` 与零偏移的分层降级思路。
- 默认位置公式 `x = workArea.left + (workArea.width - w)/2`、`y = workArea.top + workArea.height - h - bottomMargin`，本机实测应得 `(3669, 1240)`（已端到端验证正确）。
- `(0,0)` 作为 Wayland 伪值签名予以拒绝的判断（阻断脏值复活）—— 但删除策略要按新约束收窄。
- 把决策逻辑抽成可测静态谓词（`resolveRestorePosition` / `shouldPersistPosition` / `defaultPosition` / `workAreaOf`）的做法很好，保留；本次是在其**之上**补真实接线测试，不是替换它们。
- `defaultBottomMargin` 常量化取代硬编码 80。
- 已验证正确的端到端行为：默认底部居中落在 `+3669+1240`、拖动后落盘、重启后恢复、隐藏后不被覆盖。
- 代码注释里对"Linux 只发 `move` 不发 `moved`"的解释性说明（这是非显然的上游行为，值得留在代码里）。
- 修正后的 `/proc/<pid>/environ` 判据说明（`setenv` 不出现在其中，只适用于 `nextalk-toggle.sh` 的 `exec env` 路径）。


## Design Notes

**为什么锁 x11 而不是在 Wayland 原生下想办法**：Wayland 协议不允许客户端定位自己的 toplevel。本机实测（GNOME/Ubuntu，`XDG_SESSION_TYPE=wayland`，GTK3 无边框 UTILITY 窗口）：

```
=== NATIVE WAYLAND ===        === FORCED X11 (XWayland) ===
T1_INITIAL=(0,0)              T1_INITIAL=(58,0)
T2_MOVE_CALLED(700,900)       T2_MOVE_CALLED(700,900)
T3_AFTER_MOVE_SETTLED=(0,0)   T3_AFTER_MOVE_SETTLED=(700,900)
```

Wayland 下 move 无效、position 恒 `(0,0)`；XWayland 下两者均正常。项目 `.desktop` 早已选定 x11 路线，本次只是把它执行彻底。

**默认位置计算（实测数值代入）**：主显示器 X11 下 workarea = `2618,32 2502x1408`，故 `x = 2618 + (2502-400)/2 = 3669`、`y = 32 + 1408 - 120 - 80 = 1240`。与历史 prefs 中曾正常工作的 `(3297, 1036)` 同一量级，可作为合理性参照。若只用 `size` 居中会得到 `x = (2560-400)/2 = 1080`，落到左侧那台显示器——这正是现有代码的第二个缺陷。

**为什么 `(0,0)` 可以安全地当作无效值**：胶囊默认贴近屏幕底部，且 `y=0` 会被 GNOME 顶栏遮挡，用户不可能有意把窗口精确停在 `(0,0)`；而它恰是 Wayland 下的伪值签名。

## Verification

**Commands:**
- `cd voice_capsule && flutter analyze` -- expected: 无 error（既有 warning/info 数量不增加）
- `cd voice_capsule && flutter test` -- expected: 全部通过，含新增的位置计算测试
- `cd voice_capsule && flutter build linux --release` -- expected: 构建成功
- `grep -c 'GDK_BACKEND' scripts/nextalk-toggle.sh` -- expected: ≥1
- `tr '\0' '\n' < /proc/$(pgrep -f '/opt/nextalk/nextalk|voice_capsule' | head -1)/environ | grep GDK_BACKEND` -- expected: 输出 `GDK_BACKEND=x11`（**仅适用于经 `nextalk-toggle` 启动的进程**；runner 层 `setenv` 不会出现在 `/proc/.../environ` 里，见验收标准下的注意事项）
- `xwininfo -root -tree | grep com.gonewx.nextalk` -- expected: 能列出窗口（证明跑在 x11/XWayland 后端上）；唤起胶囊后其几何应为 `400x120+<x>+<y>` 且 `<x>,<y>` 非 `0,0`

**Manual checks (if no CLI):**
- 删除 prefs 中的 `nextalk_window_x/y` 后启动并唤起胶囊：应位于主显示器底部居中、不被顶栏/Dock 遮挡。
- 把 prefs 手工改成 `0.0/0.0` 再唤起：应忽略脏值、回到底部居中。
- 拖动胶囊 → 隐藏 → 重新唤起 → 完全退出应用 → 再启动唤起：两次都应停在拖动后的位置；同时 `cat ~/.local/share/nextalk/shared_preferences.json` 应显示非零坐标。
- 确认托盘图标、全局快捷键唤起、语音识别文本上屏三项功能仍正常。

## Suggested Review Order

**后端选择（一切定位能力的前提）**

- 入口点：一行回退链取代自研探测，让 GDK 自己判定 X 可用性
  [`main.cc:27`](../../voice_capsule/linux/runner/main.cc#L27)

- 冷启动回退路径同一语义，兼容尚未更新的旧二进制
  [`nextalk-toggle.sh:57`](../../scripts/nextalk-toggle.sh#L57)

**位置几何计算**

- 默认位置：按工作区绝对坐标底部居中，修正多屏偏移丢失
  [`window_constants.dart:235`](../../voice_capsule/lib/constants/window_constants.dart#L235)

- 累计可见面积判定，取代会误杀跨屏摆放的单屏阈值
  [`window_constants.dart:107`](../../voice_capsule/lib/constants/window_constants.dart#L107)

- 越界坐标钳位到最近工作区，保留用户意图而非丢弃
  [`window_constants.dart:181`](../../voice_capsule/lib/constants/window_constants.dart#L181)

**保存时机与污染防护**

- 保存挂在 Linux 唯一会触发的 move 事件上（`moved` 是死回调）
  [`flutter_window_backend.dart:488`](../../voice_capsule/lib/services/flutter_window_backend.dart#L488)

- 防抖合并一次拖动的连续事件，并在抑制期内直接丢弃
  [`flutter_window_backend.dart:500`](../../voice_capsule/lib/services/flutter_window_backend.dart#L500)

- 程序化几何变更的抑制包装：深度计数 + 自动过期时间尾巴
  [`flutter_window_backend.dart:448`](../../voice_capsule/lib/services/flutter_window_backend.dart#L448)

- 抑制判定同时看深度与时间窗，避免标志卡死
  [`flutter_window_backend.dart:471`](../../voice_capsule/lib/services/flutter_window_backend.dart#L471)

**恢复决策与退出落盘**

- 清脏值与钳位/恢复分离，只有 `(0,0)` 才删键
  [`flutter_window_backend.dart:342`](../../voice_capsule/lib/services/flutter_window_backend.dart#L342)

- 可等待的 flush，保证拖动后立即退出仍能落盘
  [`flutter_window_backend.dart:297`](../../voice_capsule/lib/services/flutter_window_backend.dart#L297)

- 事件监听注册点：缺此行则位置永不保存，现已有测试守卫
  [`flutter_window_backend.dart:117`](../../voice_capsule/lib/services/flutter_window_backend.dart#L117)

- 退出链改为 await，等窗口服务把位置写完再退进程
  [`tray_service.dart:544`](../../voice_capsule/lib/services/tray_service.dart#L544)

**测试与验证脚本**

- 真接线测试：MethodChannel 打桩驱动完整保存链路
  [`flutter_window_backend_wiring_test.dart:1`](../../voice_capsule/test/services/flutter_window_backend_wiring_test.dart#L1)

- 几何计算的纯函数用例，含多屏偏移与边界钳位
  [`window_position_test.dart:1`](../../voice_capsule/test/constants/window_position_test.dart#L1)

- 后端锁定的静态检查，摘掉即 FAIL
  [`verify-transparent-window.sh:78`](../../scripts/verify-transparent-window.sh#L78)

- 按真实标识查找窗口，取代永不匹配的旧字符串
  [`verify-transparent-window.sh:123`](../../scripts/verify-transparent-window.sh#L123)

- 环境级陷阱归档：Wayland vs XWayland 定位 API 实测对照
  [`development-pitfalls_zh.md:383`](../../docs/development-pitfalls_zh.md#L383)
