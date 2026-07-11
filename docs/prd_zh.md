# Product Requirements Document (PRD): Nextalk

简体中文 | [English](prd.md)

## 1. 目标与背景 (Goals and Background Context)

### 目标 (Goals)
*   **打造 Linux 标杆级语音输入体验**：填补 Linux 桌面端缺乏高质量、现代化语音输入工具的空白。
*   **实现“极致透明”的视觉效果**：利用 Flutter 渲染特性，提供无边框、无背景伪影、带呼吸灯动画的现代化悬浮窗 UI。
*   **保障隐私与高性能**：集成 Sherpa-onnx 离线模型，确保语音数据不出本地；文本上屏链路延迟 < 20ms，流式识别实时率 RTF < 1。
*   **实现“即说即打”的流畅交互**：通过 VAD（端点检测）实现自动断句和文本上屏。
*   **无缝集成 Fcitx5**：通过轻量级 C++ 插件和 Unix Domain Socket，实现与输入法框架的稳定通信；Fcitx5 不可用时降级为剪贴板方案。

### 背景 (Background Context)
Linux 用户缺乏美观且实用的语音输入工具。本项目 **Nextalk** 利用 Sherpa-onnx 的离线能力和 Flutter 的优秀渲染能力，构建一个生产力工具。项目采用 Monorepo 结构，包含 Fcitx5 C++ 插件（后端）和 Flutter 客户端（前端）。

### 变更日志 (Change Log)
| 日期 | 版本 | 说明 | 作者 |
| :--- | :--- | :--- | :--- |
| 2025-12-21 | 1.0 | 正式版：锁定 Flutter+Sherpa 方案，确认 C++ 插件已就绪 | PM (John) |
| 2025-12-28 | 1.1 | SCP-002: 快捷键方案改为系统原生快捷键，新增剪贴板 fallback | PM (John) |
| 2026-07-09 | 1.2 | 与 v0.2.8 代码库对齐：双引擎 ASR（SenseVoice 默认）、silero VAD、libpulse-simple 音频栈、新增模型管理/错误处理/i18n/设备选择/打包需求（FR8–FR12）、NFR1/NFR2 修正、Epic 清单同步至 epics.md | PM (John) |
| 2026-07-09 | 1.3 | FR6 全局快捷键补充第四代 Portal 方案（Story 3-10）：XDG Desktop Portal `GlobalShortcuts` 应用内自动注册 + 系统快捷键静默降级（渐进增强，回退命令统一为 `nextalk-toggle`） | PM (John) |

## 2. 需求 (Requirements)

### 2.1 功能性需求 (Functional Requirements)

*   **FR1 [UI/交互]: 悬浮胶囊窗口**
    *   应用启动后默认隐藏，托盘显示图标。
    *   激活时显示无边框、真透明胶囊窗口。
    *   **实时反馈**：识别文本在预览区实时显示（流式引擎逐字出现；离线引擎按 VAD 分段出现）。
*   **FR2 [核心]: 语音识别 (ASR) — 双引擎架构** *(v1.2 更新，Story 2-7)*
    *   **SenseVoice 离线引擎（默认）**：VAD 分段后整段识别，精度高，多语言，支持 ITN（逆文本正则化）。
    *   **Zipformer 流式引擎（可选）**：`sherpa-onnx-streaming-zipformer-bilingual-zh-en`，边听边识别，低延迟；提供 `int8`（快）/`standard`（准）两个版本。
    *   引擎与模型版本可通过托盘菜单**热切换**，无需重启应用。
    *   **音频采集**：16k 单声道；主路径 `libpulse-simple`（设备名与系统设置一致，自动重采样，适配 PipeWire/PulseAudio），回退路径 PortAudio（非 PulseAudio 系统）。
*   **FR3 [核心]: 智能端点检测** *(v1.2 更新)*
    *   **SenseVoice 路径（默认）**：使用独立的 **silero VAD 模型**（`silero_vad.onnx`，经 sherpa-onnx VAD API 加载）做语音分段，分段识别依赖 VAD 输出的语音段。
    *   **Zipformer 路径**：使用 sherpa-onnx 内置端点规则（rule1/2/3），不加载 silero VAD。
    *   两条路径行为一致：检测到静音停顿后，自动提交预览区文本。
*   **FR4 [集成]: 文本上屏**
    *   客户端通过 Unix Domain Socket 连接 `$XDG_RUNTIME_DIR/nextalk-fcitx5.sock`。
    *   协议：`[4字节长度 (LE)] + [UTF-8 文本]`。
    *   文本提交到 Fcitx5 当前最近的输入上下文（`mostRecentInputContext`）；原"焦点锁定"机制已随 SCP-002 移除。
    *   **文本保护**：提交失败时保留已识别文本，支持复制/重试（Story 3-7）。
    *   直接调用 Fcitx5 接口提交，不需要 ydotool 回退机制。
*   **FR5 [系统]: 托盘管理** *(v1.2 扩展)*
    *   窗口显示/隐藏/退出。
    *   引擎与模型版本切换、音频输入设备选择、界面语言切换、打开配置目录。
*   **FR6 [系统]: 全局快捷键** *(v1.3 更新，Story 3-10)*
    *   **逻辑**：按下唤醒/开始录音；再次按下停止/上屏/隐藏。
    *   **实现方式（渐进增强，两条路径叠加不取代）**：
        *   **第四代 — Portal 自动注册（首选）**：支持的桌面环境（KDE 5.27+、GNOME 48+、Hyprland）下，应用首次启动经 XDG Desktop Portal `org.freedesktop.portal.GlobalShortcuts` 自动注册全局快捷键（默认 Super+Z），系统弹一次授权对话框，确认后立即生效——**开箱即用，无需进入系统设置手动配置**。
        *   **第三代 — 系统快捷键（回退，硬需求）**：Portal 不支持时（GNOME <48、wlroots、Ubuntu 22.04/24.04 默认会话）静默降级，用户在系统设置绑定 `nextalk-toggle` 命令触发；应用另提供 `--show`/`--hide` 命令。
    *   单实例机制：新进程将命令经内部 Unix Socket 转发给运行中的实例。
    *   降级对用户无感：不弹错误、不阻塞启动，降级原因写入诊断日志，托盘只读项显示当前快捷键模式（Portal / 系统）。
    *   > **变更史**：原 Fcitx5 插件侧快捷键监听（第二代）已随 SCP-002 移除；应用自身不做客户端全局按键抓取（Wayland 架构禁止）。Portal 方案是 Wayland 官方演进方向，系统快捷键回退因 NFR3 基线（Ubuntu 22.04+）不支持 Portal 而始终保留。
*   **FR7 [系统]: 剪贴板 Fallback** *(SCP-002 新增)*
    *   当 Fcitx5 插件不可用（socket 不存在或提交失败）时，自动将识别文本复制到系统剪贴板。
    *   UI 显示提示："已复制到剪贴板，请粘贴"，2 秒后自动隐藏窗口。
*   **FR8 [核心]: 模型管理** *(v1.2 新增)*
    *   模型采用**首次运行下载**策略，存储于 `$XDG_DATA_HOME/nextalk/models`（默认 `~/.local/share/nextalk/models`）。
    *   管理三类模型：Zipformer（int8/standard）、SenseVoice、silero VAD。
    *   默认下载源为 GitHub Releases（k2-fsa/sherpa-onnx），支持通过配置文件自定义下载 URL。
    *   下载需展示进度、支持取消；下载完成后校验完整性，损坏文件不得进入加载流程。
*   **FR9 [系统]: 初始化向导与错误处理** *(v1.2 新增，Story 3-7)*
    *   首次运行提供初始化向导（模型下载、Fcitx5 插件检测、快捷键配置指引）。
    *   须以可视化方式处理以下故障：麦克风不存在/被占用、模型缺失或损坏、模型下载中断、Fcitx5 插件未加载、socket 断连。
    *   致命错误弹出错误对话框并给出恢复指引；非致命错误在胶囊 UI 上以状态指示表达。
*   **FR10 [系统]: 国际化** *(v1.2 新增，Story 3-8)*
    *   UI 支持简体中文与英文，可通过托盘菜单切换，即时生效。
*   **FR11 [系统]: 音频输入设备选择** *(v1.2 新增，Story 3-9)*
    *   通过托盘菜单选择音频输入设备，设备列表与系统设置一致（libpulse 枚举）。
    *   提供 `nextalk audio` CLI 子命令（交互式选择、`--list` 机读列表、按序号直接设置）。
*   **FR12 [发布]: 打包与分发** *(v1.2 新增，Epic 4)*
    *   提供 DEB/RPM 打包脚本、安装/卸载脚本、桌面集成（.desktop、图标、自启动）。
    *   提供 Docker 跨发行版兼容编译环境。

### 2.2 非功能性需求 (Non-Functional Requirements)
*   **NFR1 [性能]** *(v1.2 修正)*：
    *   文本上屏链路（socket 提交 → Fcitx5 `commitString`）延迟 < 20ms。
    *   流式识别实时率 RTF < 1（处理 100ms 音频块耗时须 < 100ms，参考硬件上目标 < 10ms）。
    *   录音期间 UI 动画保持流畅（无可感知掉帧）。
*   **NFR2 [隐私]** *(v1.2 修正)*：识别推理全程离线，语音数据不出本地。仅模型**首次下载**需要一次性网络访问；支持自定义 URL 或手动放置模型文件以实现完全离线部署。
*   **NFR3 [兼容]**：兼容 Ubuntu 22.04+（X11/Wayland 原生支持，快捷键和文本提交均支持 Wayland）。
*   **NFR4 [体验]**：窗口启动无黑框闪烁（基于 C++ Runner 改造）。

## 3. 用户界面设计目标 (UI Goals)

> UI 规范的唯一事实来源为 [front-end-spec_zh.md](front-end-spec_zh.md)，本节仅为摘要。

*   **视觉**：极简胶囊，深色半透明背景，白色内发光描边。
*   **尺寸**：400x120（逻辑像素），胶囊高度 60px。
*   **动画**：波纹（EaseOutQuad 曲线扩散）、呼吸（红点随波纹律动）、光标（1s 周期闪烁）。

## 4. 技术假设 (Technical Assumptions)

*   **仓库结构**: Monorepo
    *   `/addons`: Fcitx5 C++ 插件源码。
    *   `/voice_capsule`: Flutter 客户端源码。
    *   `/libs`: 预编译动态库（sherpa-onnx、onnxruntime）。
*   **核心栈**:
    *   Flutter (Dart) + Linux C++ Runner (Modified)
    *   Sherpa-onnx C-API（流式 / 离线 / VAD 三组接口）via Dart FFI
    *   libpulse / libpulse-simple（主）+ PortAudio（回退）via Dart FFI
    *   Unix Domain Socket IPC

## 5. Epic 列表 (Epics)

> **唯一事实来源**：[`_bmad-output/epics.md`](../_bmad-output/epics.md)（4 个 Epic，Story 明细与验收标准见该文件）。本节仅为摘要，状态截至 v0.2.8。
> 注：Story 3-7（初始化向导与错误处理）的正式条目待回填至 epics.md，目前仅存在于 implementation-artifacts。

### Epic 1: IPC 桥梁 (The Bridge) — ✅ 已完成
建立核心通信通道：Fcitx5 插件集成、插件安装脚本、Dart Socket Client、Flutter 项目初始化。

### Epic 2: 语音识别引擎 (The Brain) — ✅ 已完成
原生库链接、PortAudio/Sherpa FFI 绑定、模型管理器、音频-推理流水线、VAD 端点检测、多模型 ASR 支持（SenseVoice 集成）。

### Epic 3: 完整产品体验 (The Product) — 🟡 收尾中
透明胶囊窗口、胶囊 UI 组件、状态机与动画、系统托盘、全局快捷键、完整业务流、初始化向导与错误处理、中英国际化、音频设备选择（3-9 待评审）。

### Epic 4: 打包发布 (Distribution) — ✅ 已完成
DEB/RPM 打包脚本、安装/卸载脚本、桌面集成、Docker 跨发行版编译环境。
