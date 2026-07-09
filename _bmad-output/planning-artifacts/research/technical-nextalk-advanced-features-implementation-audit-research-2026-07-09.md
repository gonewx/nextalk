---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/prd_zh.md
  - docs/architecture_zh.md
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Nextalk 产品定义的高级特性：当前实现是"花架子"还是真能达成产品效果'
research_goals: '对照 PRD 定义的高级特性（真透明胶囊窗、<20ms 延迟、零拷贝 FFI 音频流水线、智能 VAD、流式双语 ASR、Fcitx5 上屏、剪贴板 fallback、系统快捷键、无黑框启动），逐项审计代码实现的真实性与完成度，并以最新公开资料验证各项技术声明的可行性，给出逐项裁决与改进建议'
user_name: 'Decker'
date: '2026-07-09'
web_research_enabled: true
source_verification: true
---

# 花架子还是真功夫？Nextalk 高级特性实现真实性技术研究报告

**Date:** 2026-07-09
**Author:** Decker（研究执行：Claude / BMAD Technical Research Workflow）
**Research Type:** technical

---

## Executive Summary（执行摘要）

**总体裁决：Nextalk 不是花架子——它是一个工程质量高于平均水位的真实产品，但 PRD 中有两处关键承诺与实现现实脱节：其一是性能指标（"<20ms 端到端延迟"经指标偷换得出，真实量级为 150–500ms）；其二是交互模式（"VAD 静音自动上屏"的能力已实现但在产品形态中被主动关闭，实际为按键 toggle 上屏）。**

逐特性裁决（详细证据见正文各节）：

| # | PRD 承诺 | 裁决 | 一句话依据 |
| :-- | :--- | :--- | :--- |
| FR1 | 真透明无边框胶囊窗 | ✅ **真实现**（X11 完整；Wayland 定位受限） | Runner 有完整 RGBA/防抢焦点/防黑框改造 |
| FR2 | 流式双语 ASR | ✅ **真实现，超出承诺** | 完整手写 FFI 绑定 + 双引擎架构 |
| FR3 | VAD 静音自动上屏 | ⚠️ **能力真实、产品未启用** | 生产配置 `autoStopOnEndpoint:false`，自动提交函数是死代码 |
| FR4 | Socket 文本上屏 | ✅ **真实现，质量高** | 协议/线程/权限/IME 周期均严谨；ack 未被消费是小瑕疵 |
| FR5 | 托盘管理 | ✅ 真实现（带 `NEXTALK_NO_TRAY` 稳定性逃生口） | |
| FR6 | 系统原生快捷键 | ✅ 真实现，**开箱即用打折** | 应用不监听快捷键，依赖用户手动配置系统绑定 |
| FR7 | 剪贴板 Fallback | ✅ **真实现**，与 PRD 逐字吻合 | 三级降级 + 文本保护 |
| NFR1 | 端到端延迟 <20ms | ❌ **不成立（指标偷换）** | 代码自身 AC 为 200ms；采集块 100ms；上屏路径含固定 100ms 等待 |
| NFR2 | 纯离线 | ✅ 真实现 | 推理全本地；网络仅用于模型首次下载 |
| NFR3 | X11/Wayland 原生支持 | ⚠️ **部分成立** | X11 完整；Wayland 靠 hack 补偿，窗口定位不可控 |
| NFR4 | 无黑框启动 | ✅ 真实现 | 透明配置前置于 fl_view_new + show→hide 序列 |

**给产品的三条核心建议**：
1. 把对外性能口径改为可辩护的真实指标（如"预览延迟 <300ms、按键到上屏 <500ms"），或改讲"纯离线、隐私、即按即说"叙事——当前 20ms 声明一测便穿。
2. 对 FR3 做产品决策：要么启用已实现的 VAD 自动上屏模式（能力已在，配置一行），要么修订 PRD 承认 toggle-to-talk 交互，消除 FR3/FR6 的自相矛盾。
3. Wayland 支持如实分级声明（透明✅/上屏✅带补偿/窗口定位❌），避免"原生支持"的过度承诺。

---

## Research Overview

**研究问题**：产品定义（PRD/架构文档）的高级特性，当前实现是"花架子"还是真能达成产品效果？

**研究方法**：
1. 以 PRD FR1–FR7、NFR1–NFR4 为审计清单，逐项读取实现源码（Flutter 前端 60+ 文件、Fcitx5 C++ 插件、改造版 GTK Runner），建立"承诺→代码证据→裁决"链
2. 对关键技术声明（sherpa-onnx 端点检测、流式 ASR 延迟物理下限、Flutter Linux Wayland 透明窗、Fcitx5 commitString、系统快捷键方案、音频缓冲延迟）做 Web 多源验证
3. 所有代码结论标注 `文件:行号`，外部结论标注来源 URL 与置信度

---

## Technical Research Scope Confirmation

**Research Topic:** Nextalk 产品定义的高级特性：当前实现是"花架子"还是真能达成产品效果
**Research Goals:** 对照 PRD 定义的高级特性，逐项审计代码实现的真实性与完成度，并验证技术声明可行性，给出逐项裁决

**Technical Research Scope:**

- Architecture Analysis - PRD/架构文档承诺的系统设计 vs 代码中的真实架构
- Implementation Approaches - 各高级特性（透明窗、零拷贝 FFI、VAD、IPC 上屏等）的实现方式审计
- Technology Stack - Flutter Linux / Sherpa-onnx / PortAudio / Fcitx5 技术栈的能力边界验证
- Integration Patterns - Unix Domain Socket 协议、Fcitx5 插件集成、剪贴板 fallback 的健壮性
- Performance Considerations - "<20ms 端到端延迟"等性能声明的真实性与可测量性

**Research Methodology:**

- 代码库逐特性审计（以 PRD FR1–FR7 / NFR1–NFR4 为审计清单）
- Current web data with rigorous source verification（验证 sherpa-onnx、Flutter Linux、Fcitx5 的能力声明）
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information

**Scope Confirmed:** 2026-07-09（研究范围由用户调用参数直接给定，视为已确认）

---

## Technology Stack Analysis（step-02：技术栈现实审计）

> 方法：以 PRD/架构文档声明的技术栈为清单，逐项核对代码库中的真实使用情况。所有行号引用均来自 2026-07-09 的 main 分支工作区。

### 声明栈 vs 实际栈

| 组件 | PRD/文档声明 | 代码现实 | 一致性 |
| :--- | :--- | :--- | :--- |
| 前端 UI | Flutter 3.x (Dart) | 真实：完整 Flutter Linux 工程，60+ Dart 源文件，`window_manager`/`system_tray`/`screen_retriever` 等插件 | ✅ |
| ASR 引擎 | Sherpa-onnx C-API via dart:ffi | 真实：`ffi/sherpa_onnx_bindings.dart` 手写绑定完整映射 OnlineRecognizer；**且超出 PRD**——额外实现了 SenseVoice 离线引擎 + Silero VAD 双引擎架构（`services/asr/`） | ✅+ |
| 音频采集 | PortAudio v19 via dart:ffi | **已演进**：实际为 libpulse-simple 优先、PortAudio 回退的混合策略（`audio_capture.dart:38-41`），PRD 未更新 | ⚠️ 文档滞后 |
| 后端插件 | C++17 Fcitx5 插件 | 真实：`addons/fcitx5/src/nextalk.cpp`，270 行，SCP-002 极简架构 | ✅ |
| IPC | Unix Domain Socket | 真实：协议 `[4字节LE长度]+[UTF-8]` 双端一致实现 | ✅ |
| Runner | "基于 C++ Runner 改造" | 真实：`my_application.cc` 有实质性透明化改造（RGBA visual、无边框、防抢焦点、show→hide 防黑框） | ✅ |

### 关键技术栈事实

1. **FFI 绑定是手写且完整的**：`sherpa_onnx_bindings.dart` 覆盖 OnlineRecognizer 全生命周期（create/acceptWaveform/decode/isReady/isEndpoint/reset/inputFinished/destroy），配置结构体逐字段映射（含 endpoint rule1/2/3、hotwords、CTC FST 等），内存管理有配对的 `_freeConfigStrings`（`sherpa_service.dart:359-380`）。不是 stub。
2. **双引擎超出 PRD 范围**：Zipformer（流式）+ SenseVoice（离线+外置 Silero VAD），带 `EngineInitializer` 回退逻辑与托盘热切换。
3. **测试覆盖真实**：`voice_capsule/test/` 下 40 个测试文件，含 integration/e2e/ffi 分层。
4. **工程细节可信**：预初始化引擎规避 onnxruntime JIT 冷启动（`main.dart:154-178`）、首帧 20ms 快速缓冲（`AudioConfig.firstFrameBuffer=320`）、PipeWire 底层 hw: 设备过滤（`audio_capture.dart:72-138`）。

**结论**：技术栈层面不是花架子——声明的每一项技术都有真实、有深度的实现，且多处超出 PRD 承诺。主要问题是文档滞后于实现（PortAudio→Pulse 优先）。

---

## Integration Patterns Analysis（step-03：集成模式审计）

### IPC 上屏链路（FR4）——真实现，质量高

**C++ 侧**（`addons/fcitx5/src/nextalk.cpp`）：
- Socket 文件 0600 权限（`nextalk.cpp:112`）、EINTR 重试、`MSG_WAITALL` 完整读取、1MB 消息上限、30s recv 超时+探活
- 跨线程正确性：socket 监听线程通过 `dispatcher_.schedule()` 把 `commitText` 调度回 Fcitx5 主事件循环（`nextalk.cpp:200-202`）
- IME 周期模拟：setClientPreedit → commitString → 清空 preedit（`nextalk.cpp:250-266`），兼容终端类应用
- 输入上下文回退链：mostRecentInputContext → 有焦点的 IC → 任意 IC（`nextalk.cpp:216-244`）

**Dart 侧**（`services/fcitx_client.dart`）：连接超时/3 次重试/降级模式/发送互斥锁/剪贴板模式检测，协议编码与 C++ 侧逐字节一致。

**发现的瑕疵**：
- C++ 发送 1 字节 ack（`nextalk.cpp:205-206`），但 Dart 客户端 `listen((_) {})` 直接丢弃——**上屏成功与否客户端不可知**，"发送成功"只代表写入 socket 缓冲成功。
- 无焦点时提交到"任意输入上下文"可能把文本上屏到非预期应用（代码自己也以 `Using fallback input context (no focus)` 日志承认）。

### 剪贴板 Fallback（FR7）——与 PRD 逐字吻合

`hotkey_controller.dart:407-448`：检测 socket 不存在 → 复制剪贴板 → UI 显示提示 → 2 秒后自动隐藏。三级降级完整：Fcitx5 → 剪贴板 → 剪贴板也失败时保留文本+错误 UI+托盘警告。**真实现**。

### 系统快捷键集成（FR6）——真实现，但"开箱即用"打折

- `--toggle/--show/--hide` 经 `$XDG_RUNTIME_DIR/nextalk.sock` 单实例 IPC 转发（`single_instance.dart`、`main.dart:77-102`），协议同为 4 字节 LE 长度前缀。
- `HotkeyController` 状态机（idle/recording/submitting）有防抖、`_isProcessing` 竞态防护、提交中断保护（快速重按打断提交并保文本）。
- **代价**：应用内完全没有全局快捷键监听（`HotkeyService` 仅读配置用于显示，`hotkey_service.dart:73` 自注释"不再同步到输入法插件"）。用户必须手动去 GNOME/KDE 设置里创建自定义快捷键绑定 `nextalk --toggle`，否则快捷键功能不存在。

### Wayland 焦点补偿——存在真实的平台对策

提交前先隐藏窗口并等待 100ms 让原应用恢复焦点（`hotkey_controller.dart:338-344`），注释明确这是 Wayland 下 commitString 生效的前提。这说明团队踩过真实的 Wayland 坑，不是纸面设计；但也意味着上屏路径上有一段**固定 100ms 的人为延迟**——与 "<20ms 端到端" 声明直接矛盾。

---

## Architectural Patterns Analysis（step-04：架构声明 vs 架构现实）

### "零拷贝 FFI 流水线"——工程上真实，宣传上夸大

代码现实（`audio_inference_pipeline.dart:557-587`）：
```
final buffer = _audioCapture.buffer;                    // 堆外 Pointer<Float>
final samplesRead = _audioCapture.read(buffer, ...);    // pa_simple_read 直写该地址
_asrEngine.acceptWaveform(AudioConfig.sampleRate, buffer, samplesRead);  // 同一指针
```
- **成立的部分**：Dart 托管堆与 C 边界之间确实没有额外拷贝，`SherpaService.acceptWaveform` 注释与实现一致（"直接使用传入的指针，不进行内存分配或拷贝"）。
- **不成立的部分**：sherpa-onnx 的 `AcceptWaveform` 在 C++ 内部必然把样本拷入其特征提取环形缓冲（流式识别器必须持有历史上下文），所以"端到端零拷贝"在整条链路上不成立——成立的只是"Dart 层零额外拷贝"。
- **因果错位**：架构文档用零拷贝论证 NFR1（<20ms），但省掉的一次 6.4KB memcpy 只值几微秒；真正的延迟由 100ms 采集块、推理耗时和 100ms 焦点等待构成。零拷贝是好工程，但它与 20ms 目标之间没有因果关系。

### 并发模型——文档承认的妥协

架构文档 4.2.2 自述：MVP 阶段音频读取和推理**运行在主 Isolate**，"如果低端硬件掉帧再移到 Isolate.spawn"。这意味着推理阻塞会直接抢 UI 帧预算——在低端 CPU 上呼吸灯/波纹动画掉帧是结构性风险。这是被文档记录的已知妥协，不算隐瞒，但与"标杆级体验"目标存在张力。

### VAD 架构——能力真实，产品形态与 PRD 相反

这是本次审计**最重要的发现**：

- **能力层（真）**：Zipformer 路径完整配置了 sherpa 内置端点检测（rule1=2.4s / rule2=1.2s 可配 / rule3=20s，`audio_inference_pipeline.dart:331-340`），`isEndpoint()` 每 chunk 轮询，`EndpointEvent` 事件流、`VadConfig` 三种模式（自动停止/连续/PTT 累积）都实现了。SenseVoice 路径另有独立 Silero VAD。
- **产品层（未启用）**：生产入口 `main.dart:331-340` 以 `VadConfig(autoStopOnEndpoint: false, autoReset: false)` 创建流水线——即 **PTT 累积模式**。`hotkey_controller.dart:450-468` 的注释直白承认："PTT 模式：VAD 端点只作为视觉反馈，不触发自动提交"。为 VAD 自动提交准备的 `_submitFromVad()`（`hotkey_controller.dart:491-518`）**没有任何调用方，是死代码**。
- **与 PRD 的矛盾**：PRD FR3 承诺"检测到静音后，自动提交预览区文本"、目标是"即说即打"；PRD FR6 又承诺"再次按下停止/上屏/隐藏"。两者本身冲突，实现选择了 FR6（toggle-to-talk），FR3 的自动上屏被静默放弃。PRD 还写着"默认停顿 ~1.5s 触发"，代码默认是 1.2s。

### 窗口架构——X11 完整，Wayland 打折

- Runner 改造（`my_application.cc:26-75`）：无边框、UTILITY 类型、skip taskbar/pager、`accept_focus(FALSE)`、RGBA visual + `gdk_screen_is_composited` 检查、`fl_view_set_background_color` 透明背景、show→hide 防黑框——这是完整、正确的 X11 真透明方案，NFR4（无黑框闪烁）有真实对策。
- 窗口显隐/定位走 `window_manager` 插件（`flutter_window_backend.dart`），位置记忆依赖 `setPosition`/`getPosition`——**在 Wayland 下 GTK3 客户端无法自主定位窗口**，位置记忆与"屏幕底部居中"的默认定位在 Wayland 会话中不可靠（待 Web 验证条目 3 确认程度）。
- 代码中的 Wayland 意识（焦点补偿 hack、`#ifdef GDK_WINDOWING_WAYLAND`）表明团队知情，但 NFR3 声称的"X11/Wayland 原生支持"实际是"X11 完整支持，Wayland 尽力而为"。

---

## Implementation Research（step-05：性能声明与工程质量审计）

### NFR1 "<20ms 端到端延迟"——指标偷换，不成立

四条独立证据链：

1. **代码自己的验收标准是 200ms**：`audio_inference_pipeline.dart:27` 注释 `AC5: 端到端延迟 < 200ms`，`_latencyThresholdMs = 200`。开发过程中的真实工程目标从来不是 20ms。
2. **采集粒度就是 100ms**：`AudioConfig.framesPerBuffer = 1600`（100ms @16kHz），主循环目标周期 100ms（`targetDurationMs = 100`）。一个音频样本从进入麦克风到有机会被推理，平均排队 50ms、最坏 100ms——物理上不可能 <20ms。
3. **上屏路径含固定 100ms 延迟**：Wayland 焦点补偿 `Future.delayed(100ms)`（`hotkey_controller.dart:344`）。
4. **文档内部自洽性破裂**：架构文档 4.2.2 写"处理 100ms 音频块通常 <10ms"——这是"单块处理耗时"，被 PRD/CLAUDE.md 包装成"端到端延迟 <20ms"。指标定义被偷换。

**真实的延迟画像**（基于代码结构推算）：
- 说话→预览文字出现：约 100ms（块累积）+ 推理耗时 + UI 帧 ≈ **150–300ms**（这与代码内 200ms AC 吻合，也是流式 ASR 的正常水平）
- 按键停止→文字上屏：stop 轮询(≤300ms) + 最终解码 + 隐藏窗口 + 100ms 焦点等待 + socket 传输 ≈ **200–500ms**
- 就产品体验而言这些数字完全够用，但与对外声称的 "<20ms" 相差一个数量级以上。

### 内部延迟测量本身也在自我美化

`_processSingleChunk` 的"延迟测量"起点是 `read()` 调用前（`chunkStartTime`），测的是"读取+推理+发事件"的处理耗时，**不含音频在缓冲区里排队的 100ms**，也不含上屏路径。即便如此测得的数字仍以 200ms 为阈值告警——侧面印证 20ms 从未是工程现实。

### 工程质量整体评价（防止"一票否决"式误判）

尽管指标有水分，代码质量本身处于高水位：
- 错误处理体系完整：设备丢失保文本（Story 3-7 AC13）、提交失败三级降级、提交中断保护、全局 runZonedGuarded + 诊断日志
- 资源管理严谨：FFI 内存配对释放、StreamController 关闭防护（`_isDisposed` 检查遍布）、dispose 链完整
- 平台兼容做了脏活：PipeWire hw: 设备过滤、WirePlumber 节点休眠唤醒、设备回退桌面通知、`NEXTALK_NO_TRAY` 逃生口
- 40 个测试文件分层覆盖（unit/integration/e2e/ffi）

### 杂项发现

- `main.dart:134` 帮助文本中的项目主页是 `https://github.com/anthropics/nextalk`——AI 生成残留占位符，对外发布前需修正。
- PRD 停顿阈值 "~1.5s" vs 代码默认 1.2s（`kDefaultRule2Silence = 1.2`）。
- 托盘服务存在段错误逃生口（`NEXTALK_NO_TRAY=1`），暗示 system_tray 插件在部分环境不稳定。

---

## External Source Verification（step-06a：关键技术声明的外部验证）

> 以下由并行 Web 研究验证（2026-07-09），与代码审计结论交叉互证。

| # | 声明 | 外部裁决 | 置信度 | 与代码审计的互证 |
|---|---|---|---|---|
| 1 | sherpa 内置端点检测可实现停顿断句 | **成立** | 高 | 代码配置的 rule1=2.4/rule2=1.2/rule3=20 与上游默认值逐一吻合；能力真实，只是产品层未启用自动上屏 |
| 2 | 端到端延迟 <20ms | **不成立/误导** | 高 | 与代码内 200ms AC、100ms 采集块的发现一致；业界流式 ASR 端到端为数百毫秒级 |
| 3 | Flutter Linux 真透明无边框窗 | **部分成立** | 高 | X11 方案与 Runner 改造逐点吻合；Wayland 全局定位是硬约束 |
| 4 | Fcitx5 commitString 上屏 | **成立(X11)/部分(Wayland)** | 中 | 印证插件实现走官方机制；Wayland 需 fcitx5 较新版本 |
| 5 | 系统快捷键 + --toggle | **成立，Wayland 唯一可行** | 高 | **为 SCP-002 设计决策正名**：应用内抓键在 Wayland 无路可走 |
| 6 | 采集缓冲 10-50ms 量级 | **成立（有前提）** | 中 | 本项目用 100ms 块（1600 帧），走 Pulse 路径，符合"实际更高"的判断 |

**外部验证的关键增量事实**：

1. **端点检测机制确认**（来源：deepwiki k2-fsa/sherpa-onnx）：`enable_endpoint` C API 默认关闭、rule1/2/3 默认值 2.4s/1.2s/20s 与本项目代码完全一致；PRD 想要的"~1.5s 停顿"只需把 rule2 从 1.2 调到 1.5。内置端点检测与 Silero VAD 是两套机制，前者对"说完停顿上屏"更直接。
2. **流式 ASR 延迟物理下限**（来源：apxml.com 流式 ASR 部署教程、arxiv 2604.14493）：流式 zipformer 必须先累积 chunk（sherpa 各模型 80ms–1120ms）才能解码，算法延迟=帧长+lookahead，业界 TTFT 数百毫秒、对话基准 <500ms。**"<20ms" 只能描述单 chunk 推理耗时或 IPC 传输延迟**——这正是本审计发现的指标偷换。
3. **Wayland 窗口定位硬约束**（来源：flutter/flutter#57932、pub.dev wayland_layer_shell）：Wayland 不允许客户端绝对定位；layer-shell 方案仅 wlroots 系合成器（Sway/Hyprland）可用，**GNOME Mutter 不支持**。本项目 `window_manager.setPosition` 的位置记忆在 GNOME Wayland 会话中无法生效，属平台限制而非实现缺陷。
4. **Flutter 透明窗回归风险**（来源：flutter/flutter#152154）：Flutter 3.22/3.24 存在透明背景渲染成黑色的回归，升级 Flutter 版本时需回归测试透明效果。
5. **Fcitx5 Wayland 上屏边界**（来源：fcitx-im.org wiki、deepwiki fcitx/fcitx5）：`commitString` 是官方支持机制；纯 Wayland 下建议 fcitx5 ≥5.24，V2 协议单次 commit 有 4096 字节上限（fcitx5 的 `commitStringWrapper` 会自动拆分）；GNOME 原生 Wayland 应用对第三方输入法支持薄弱，XWayland 应用更稳。长语音识别文本（中文 UTF-8 3 字节/字，约 1300 字触发拆分）在 Wayland 有额外行为边界。
6. **SCP-002 快捷键方案获正面裁决**（来源：Ulauncher/albert 等项目的 Wayland 热键实践）：Wayland 架构禁止客户端全局抓键，"系统快捷键 + CLI toggle"是标准且唯一可靠做法。**这不是偷懒，是正确的工程决策**——代价是首次配置的引导体验需要产品补位。

---

## Strategic Technical Recommendations（step-06b：综合结论与建议）

### 最终裁决：真功夫为主，两处"纸面承诺"需要产品层面处理

以"花架子"定义为"有 UI 无实现、或实现无法支撑宣称效果"来衡量：

- **不是花架子的证据**（占绝对多数）：全部 7 项功能性需求都有真实、可运行、带测试的实现；错误处理/降级/资源管理达到生产水位；多处实现超出 PRD（双引擎、设备热切换、诊断日志、i18n）；踩过真实平台坑的痕迹（Wayland 焦点补偿、PipeWire 设备过滤、onnxruntime JIT 预热）遍布代码。
- **"花架子"成分**（集中在承诺层而非代码层）：
  1. **NFR1 "<20ms"** 是唯一被证伪的硬指标——它不是实现不行，而是指标本身不诚实（真实 150–500ms 对语音输入完全够用且属业界正常水平）。
  2. **FR3 "VAD 自动上屏"** 是"能力已建成、开关被关闭"——PRD 的宣传语（"即说即打"）描述的交互在当前产品中不存在。

### 行动建议（按优先级）

1. **【P0·文档】修正性能叙事**：将 PRD/CLAUDE.md/README 中 "<20ms 端到端延迟" 改为可辩护口径，建议："单块推理耗时 <10ms（100ms 音频块），预览延迟 <300ms，按键到上屏 <500ms，纯离线零网络"。隐私+离线才是差异化卖点，20ms 是自曝弱点。
2. **【P0·产品决策】解决 FR3/FR6 矛盾**：二选一——(a) 在设置中暴露"自动上屏模式"（`VadConfig(autoStopOnEndpoint:true)` 已实现，接通 `_submitFromVad` 即可，改动极小）；(b) 修订 PRD，正式承认 toggle-to-talk 交互并删除 FR3 的自动提交承诺。同时统一 1.2s vs 1.5s 的停顿阈值口径。
3. **【P1·文档】Wayland 支持分级声明**：透明✅ / 上屏✅（需 fcitx5 版本说明，建议 ≥5.24）/ 全局快捷键✅（需手动配置，附各 DE 引导）/ 窗口位置记忆❌（GNOME Wayland，平台限制）。
4. **【P1·工程】补齐上屏确认**：C++ 端已发 ack，Dart 端消费它（`fcitx_client.dart` 的 listen 回调），把"写入 socket 成功"升级为"插件确认收到"，为"上屏失败→剪贴板"降级提供真实判据。
5. **【P2·工程】低端机防掉帧预案落地**：架构文档已承诺"掉帧则迁移 Isolate"，建议在诊断日志中加帧率采样，给该预案一个可触发的量化条件。
6. **【P2·清理】**：修正 `main.dart:134` 的 `github.com/anthropics/nextalk` 占位符链接；升级 Flutter 前回归测试透明窗（#152154 回归风险）；关注 Wayland 下 >4096 字节长文本 commit 的拆分行为。

### 研究局限

- 未做真机延迟实测（结论基于代码结构推算 + 业界基准），建议后续用 `LatencyStats` 已有埋点做一次实测标定。
- Wayland 行为矩阵（GNOME/KDE/Sway × fcitx5 版本）未逐一实测，外部来源置信度标注为中的条目（#4、#6）建议抽样验证。

---

## 引用来源（外部）

- sherpa-onnx 端点检测/OnlineRecognizer：https://deepwiki.com/k2-fsa/sherpa-onnx
- 流式 ASR 延迟基准：https://apxml.com/courses/speech-recognition-synthesis-asr-tts/chapter-6-optimization-deployment-toolkits/streaming-asr-deployment ；https://arxiv.org/html/2604.14493v1
- Flutter Linux 透明窗：https://github.com/flutter/flutter/issues/152154 ；https://github.com/flutter/flutter/issues/66751 ；https://github.com/flutter/flutter/issues/57932 ；https://github.com/flutter/engine/pull/20629 ；https://pub.dev/packages/wayland_layer_shell
- Fcitx5 Wayland：https://fcitx-im.org/wiki/Using_Fcitx_5_on_Wayland ；https://deepwiki.com/fcitx/fcitx5/4.2-wayland-integration ；https://deepwiki.com/fcitx/fcitx5/2.2-addon-management
- Wayland 全局热键：https://github.com/Ulauncher/Ulauncher/wiki/Hotkey-In-Wayland ；https://github.com/albertlauncher/albert/issues/309
- PortAudio 延迟：https://portaudio.com/docs/latency.html ；https://github.com/PortAudio/portaudio/wiki/BufferingLatencyAndTimingImplementationGuidelines
