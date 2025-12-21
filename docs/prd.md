# Product Requirements Document (PRD): Nextalk

## 1. 目标与背景 (Goals and Background Context)

### 目标 (Goals)
*   **打造 Linux 标杆级语音输入体验**：填补 Linux 桌面端缺乏高质量、现代化语音输入工具的空白。
*   **实现“极致透明”的视觉效果**：利用 Flutter 渲染特性，提供无边框、无背景伪影、带呼吸灯动画的现代化悬浮窗 UI。
*   **保障隐私与高性能**：集成 Sherpa-onnx 离线模型，确保数据不出本地，并实现 <200ms 的上屏延迟。
*   **实现“即说即打”的流畅交互**：通过智能 VAD（端点检测）实现自动断句和文本上屏。
*   **无缝集成 Fcitx5**：通过现有的轻量级 C++ 插件和 Unix Domain Socket，实现与输入法框架的稳定通信。

### 背景 (Background Context)
Linux 用户缺乏美观且实用的语音输入工具。本项目 **Nextalk** 利用 Sherpa-onnx 的离线能力和 Flutter 的优秀渲染能力，构建一个生产力工具。项目采用 Monorepo 结构，包含现有的 Fcitx5 C++ 插件（后端）和全新的 Flutter 客户端（前端）。

### 变更日志 (Change Log)
| 日期 | 版本 | 说明 | 作者 |
| :--- | :--- | :--- | :--- |
| 2025-12-21 | 1.0 | 正式版：锁定 Flutter+Sherpa 方案，确认 C++ 插件已就绪 | PM (John) |

## 2. 需求 (Requirements)

### 2.1 功能性需求 (Functional Requirements)

*   **FR1 [UI/交互]: 悬浮胶囊窗口**
    *   应用启动后默认隐藏，托盘显示图标。
    *   激活时显示无边框、真透明胶囊窗口。
    *   **实时反馈**：用户说话时，文字逐字显示在预览区。
*   **FR2 [核心]: 实时语音识别 (ASR)**
    *   **模型**：`sherpa-onnx-streaming-zipformer-bilingual-zh-en` (流式双语)。
    *   **采集**：通过 Dart FFI + PortAudio 采集 16k 单声道音频。
*   **FR3 [核心]: 智能端点检测 (VAD)**
    *   使用 Sherpa 内置 VAD (默认停顿 ~1.5s 触发)。
    *   检测到静音后，自动提交预览区文本。
*   **FR4 [集成]: 文本上屏**
    *   客户端通过 Unix Domain Socket 连接 `$XDG_RUNTIME_DIR/nextalk-fcitx5.sock`。
    *   协议：`[4字节长度 (LE)] + [UTF-8 文本]`。
    *   **注意**：直接调用 Fcitx5 接口提交，**不需要** ydotool 回退机制。
*   **FR5 [系统]: 托盘管理**
    *   支持显示/隐藏/退出。
*   **FR6 [系统]: 全局快捷键**
    *   **默认键位**：`Right Alt`。
    *   **逻辑**：按下唤醒/开始录音；再次按下停止/上屏/隐藏。
    *   支持配置文件自定义。

### 2.2 非功能性需求 (Non-Functional Requirements)
*   **NFR1**: 端到端延迟 < 200ms。
*   **NFR2**: 纯离线推理，无网络请求。
*   **NFR3**: 兼容 Ubuntu 22.04+ (X11/Wayland via XWayland)。
*   **NFR4**: 窗口启动无黑框闪烁 (基于 C++ Runner 改造)。

## 3. 用户界面设计目标 (UI Goals)

*   **视觉**：极简胶囊，深色半透明背景，白色内发光描边。
*   **尺寸**：400x120 (逻辑像素)，胶囊高度 60px。
*   **动画**：
    *   **波纹**：EaseOutQuad 曲线扩散。
    *   **呼吸**：红点随波纹律动。
    *   **光标**：1s 周期闪烁。

## 4. 技术假设 (Technical Assumptions)

*   **仓库结构**: Monorepo
    *   `/addons`: 现有的 C++ Fcitx5 插件源码。
    *   `/voice_capsule`: Flutter 客户端源码。
*   **核心栈**:
    *   Flutter (Dart) + Linux C++ Runner (Modified)
    *   Sherpa-onnx (C-API) via Dart FFI
    *   PortAudio via Dart FFI
    *   Unix Domain Socket IPC

## 5. Epic 列表与详情 (Epics)

### Epic 1: 插件集成与 IPC (The Bridge)
**状态**: *大部分已完成，需清理和集成*
*   **Story 1.1 [Integration]**: 将现有的 `addons/fcitx5` 代码迁入项目结构，配置 CMake 构建流程。
*   **Story 1.2 [Refactor]**: 清理 C++ 代码，移除 `ydotool` 回退逻辑（根据最新需求）。
*   **Story 1.3 [Dev]**: 实现 Dart 端的 Socket Client，验证与 C++ 插件的通信（发送 Hello World 并上屏）。
*   **Story 1.4 [DevOps]**: 编写 `scripts/install_addon.sh`，实现插件的一键编译和安装。

### Epic 2: 听觉与大脑 (The Brain)
**状态**: *待开发*
*   **Story 2.1 [Infra]**: 配置 Flutter Linux 构建环境，链接 `libsherpa-onnx-c-api.so` 和 `libportaudio.so`。
*   **Story 2.2 [FFI]**: 编写 Dart FFI Bindings，映射 Sherpa 和 PortAudio 的 C 函数。
*   **Story 2.3 [Dev]**: 实现音频采集流 -> Sherpa 推理流的数据管道。
*   **Story 2.4 [Dev]**: 实现 VAD 事件监听与处理。

### Epic 3: 融合与交付 (The Product)
**状态**: *待开发*
*   **Story 3.1 [UI]**: 迁移已验证的 Flutter UI 代码到主工程。
*   **Story 3.2 [Logic]**: 串联 `Right Alt` -> 录音 -> 识别 -> Socket 上屏 的完整业务流。
*   **Story 3.3 [Sys]**: 实现全局快捷键监听 (Rust FFI 或 C++ Runner 扩展)。
*   **Story 3.4 [Sys]**: 完善托盘与窗口显隐逻辑。