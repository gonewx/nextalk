# 架构文档 v2.1 对抗性事实核查报告

- **评审对象**: `docs/architecture_zh.md`（主）与 `docs/architecture.md`（英文镜像），版本 2.1（2026-07-09 棕地校准）
- **核查基准**: v0.2.8 代码库（以代码为准）
- **评审日期**: 2026-07-09
- **总体判定**: **有条件通过** —— 文档整体质量高，目录树、IPC 数字约束、并发模型结论、配置模板等大部分"校准"内容与代码吻合；但存在 2 处核心技术事实错误（ACK、silero VAD 共用）与 2 处构建/模型管理陈述失实，须修正后方可作为权威架构基线。

---

## Critical

### C1. "两条路径共用 silero VAD 模型" 与代码矛盾（Zipformer 不使用 silero VAD）

- **位置**: 中文 §4.2.2 第 247 行（"两条路径共用 silero VAD 模型与端点事件流"）、§2.1 系统上下文图（`Pipeline --> VAD[silero VAD]` 置于两引擎公共路径上）、§3 技术栈表（"独立 VAD 模型，两引擎共用"）；英文镜像同位置（L248、L129 等）。
- **代码事实**:
  - `voice_capsule/lib/services/audio_inference_pipeline.dart` L330-347: Zipformer 路径构造 `ZipformerConfig(enableEndpoint: true, rule1MinTrailingSilence: 2.4, rule2MinTrailingSilence: …, rule3MinUtteranceLength: 20.0)`，**不含任何 vadModelPath**；仅 SenseVoice 路径传入 `vadModelPath: _modelManager.vadModelFilePath`。
  - `voice_capsule/lib/services/asr/zipformer_engine.dart` L184、L327-329: 使用 sherpa-onnx **OnlineRecognizer 内置端点检测**（解码器静音规则），不加载 silero 模型。
  - `voice_capsule/lib/services/asr/sensevoice_engine.dart` L272-280: 仅此引擎经 `sherpa_vad_bindings` 初始化 Silero VAD。
- **正确表述**: 两条路径共用的是 **Pipeline 层的 `EndpointEvent` 端点事件流**（此半句正确）；端点检测机制不同——SenseVoice 用独立 silero VAD 模型分段，Zipformer 用 sherpa-onnx 识别器内置端点规则（rule1/2/3）。silero_vad.onnx 仅在 SenseVoice 引擎下被加载。
- **修复建议**: 三处同步改写：§4.2.2 改为"两条路径共用端点事件流（EndpointEvent）；silero VAD 仅 SenseVoice 路径使用，Zipformer 依赖识别器内置端点规则"；§2.1 图中把 VAD 节点移到 SenseVoice 分支下、给 Zipformer 标注"内置端点检测"；§3 技术栈表"两引擎共用"改为"仅 SenseVoice 引擎使用"。中英两份同改。

### C2. "协议无 ACK" 与代码矛盾（插件对每条消息回发 1 字节 ACK）

- **位置**: 中文 §4.1.1 "已知限制 (设计负债)"："协议无版本号/魔数，**无 ACK**——客户端无法探测插件版本"（L167）；英文镜像 L167。
- **代码事实**: `addons/fcitx5/src/nextalk.cpp` L204-206:
  ```cpp
  // 发送确认
  uint8_t ack = 1;
  send(clientFd, &ack, 1, 0);
  ```
  插件在每条消息调度上屏后**确实发送 1 字节 ACK**。另一侧 `voice_capsule/lib/services/fcitx_client.dart` L157-159 客户端 `listen((_) {})` 显式**忽略**入站数据（且其注释"服务端不发送数据"同样与插件代码矛盾）。
- **影响**: 这是协议规格性文档；按文档实现的第三方客户端/插件会产生线协议不一致（客户端不读 ACK 只是缓冲区积累 1 字节/条，但"无 ACK"的规格描述是错的）。
- **修复建议**: 改为"插件对每条消息回发 1 字节 ACK（值 0x01），当前 Flutter 客户端不消费该 ACK（发后即忘），故 ACK 不构成可靠投递语义；协议无版本号/魔数仍为已知限制"。中英同改。顺带建议在代码侧修正 `fcitx_client.dart` L158 的错误注释（非本文档职责，可另开 issue）。

---

## High

### H1. §4.4 模型表：Zipformer standard "跳过校验" 失实（int8/standard 同包同校验）

- **位置**: 中文 §4.4 模型表（L289-294）：将 Zipformer 拆为 int8（✅ 有校验）与 standard（⚠️ 跳过）两行；§6 "下载校验"亦写"（Zipformer int8）"。英文镜像 L290-295、L402。
- **代码事实**: `voice_capsule/lib/services/model_manager.dart` L78-114 仅定义 **3 个** `ModelConfig`：
  - `zipformer`：单一压缩包 `sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2`，`sha256: '27ffbd…c5f8'`——该包**同时包含 int8 与 standard 两套模型文件**，int8/standard 只是加载时选择（`useInt8Model`，pipeline L324-326），不存在独立的 standard 下载物。
  - `sensevoice`：`sha256: null`（跳过，注释"官方未提供校验值"）。
  - `sileroVad`：单文件，`sha256: null`（跳过）。
- **正确表述**: Zipformer（int8+standard 同包）✅ 下载即 SHA256 校验；SenseVoice ⚠️ 跳过；silero_vad.onnx ⚠️ 跳过。
- **修复建议**: 模型表改为 3 行（Zipformer 双版本合一行，注明"同一压缩包含 int8/standard 两套权重，共用同一 SHA256"）；§6 中"（Zipformer int8）"改为"（Zipformer 模型包）"。中英同改。

### H2. §5.1 "构建脚本经 --dart-define=APP_VERSION 注入" 陈述过宽（build-pkg.sh 未注入）

- **位置**: 中文 §5.1（L351）："构建脚本读取 version.yaml，经 `--dart-define=APP_VERSION` 注入应用"。英文镜像 L353。
- **代码事实**:
  - `scripts/docker-build.sh` L182/L191: 从 version.yaml 读取版本并 `flutter build linux --release --dart-define=APP_VERSION=${app_ver}` ✅。
  - `scripts/build-pkg.sh` L201: 触发重建时执行的是 **`flutter build linux --release`（无 dart-define）**；它读取 version.yaml（L171-188）仅用于 DEB/RPM **包名/元数据版本**。`voice_capsule/lib/main.dart` L141-144: 未注入时 `appVersion` 回落为 `'dev'`。
- **影响**: 按文档理解，任一脚本产出的二进制都携带正确版本；实际上 build-pkg.sh 本地重建路径产出的应用自报版本为 "dev"（包版本与应用内版本脱节）。这既是文档失实，也暴露一个真实构建缺口。
- **修复建议**: 文档改为"docker-build.sh 经 `--dart-define=APP_VERSION` 注入应用内版本；build-pkg.sh 读取 version.yaml 仅用于 DEB/RPM 包版本，其内置重建路径当前未注入 APP_VERSION（缺口，见 backlog）"，或先修 build-pkg.sh L201 补上 dart-define 再保留原表述。中英同改。

---

## Medium

### M1. §4.4 "支持按引擎分别自定义下载地址" 仅对 Zipformer 生效

- **位置**: 中文 §4.4 第 5 点（L298）："支持经配置文件按引擎分别自定义下载地址"；§4.5 YAML 示例中 sensevoice 亦含 `custom_url`。英文镜像 L299。
- **代码事实**: `model_manager.dart` L755-763 `_getCustomUrlForEngine`：注释明写"目前仅支持 Zipformer 的 custom_url"，SenseVoice 分支直接返回 `null`；`settings_service.dart` L314 虽解析了 `model.sensevoice.custom_url`，但下载路径不消费。VAD 模型 `vadDownloadUrl`（L753）也只用默认 URL。
- **修复建议**: 改为"当前仅 Zipformer 的 `custom_url` 生效；`sensevoice.custom_url` 字段已在配置模板中预留但实现未消费（已知缺口）"。§4.5 示例中该字段加注释说明。中英同改。

### M2. §4.1.4 遗漏 commitText 的无焦点回退（文本可能提交到非焦点上下文）

- **位置**: 中文 §4.1.4（L199）："文本提交到……即提交时刻焦点所在的输入框"。英文镜像 L199。
- **代码事实**: `nextalk.cpp` L216-248 `commitText` 有**三级**目标选择：① `mostRecentInputContext()`；② 为空则遍历 `inputContextManager` 找任一 `hasFocus()` 的 IC；③ 仍无则取**任意一个 IC（可能无焦点）**并记录 "Using fallback input context (no focus)"。即极端情况下文本会提交到当前并无焦点的上下文，"焦点所在的输入框"并不总成立。
- **修复建议**: 补记三级回退顺序，并把"③ 任意无焦点 IC"标注为潜在误注入风险（可与 §6 安全联动记为已知行为）。中英同改。

### M3. §5.2/§5.3 遗漏 libportaudio 被复制进 bundle

- **位置**: 中文 §5.2（L358）："音频库（libpulse/libpulse-simple、libportaudio）从系统动态链接"；§5.3 Bundle 结构（L384-392）lib/ 只列 3 个 .so。英文镜像 L360、L386-394。
- **代码事实**: `voice_capsule/linux/CMakeLists.txt` L159-172: `find_library(PORTAUDIO_LIBRARY …)` 后将系统 libportaudio 的 REALPATH **复制进 bundle/lib 并改名 `libportaudio.so.2`**（找不到仅 WARNING）。即最终 bundle/lib 实际含 4 个 .so：libsherpa-onnx-c-api.so、libonnxruntime.so、libflutter_linux_gtk.so、libportaudio.so.2（另有 AOT libapp.so，Release 构建）。libpulse 确为纯系统链接 ✓。捆绑 sherpa/onnxruntime 自 `libs/` 复制 ✓（L151-155，且 L28-32 缺库即 FATAL_ERROR）。
- **修复建议**: §5.2 改为"libpulse 系统链接；libportaudio 构建时从构建机复制入 bundle（libportaudio.so.2）"；§5.3 Bundle 结构补 `libportaudio.so.2`（及可选注明 libapp.so）。中英同改。

---

## Low

### L1. "强制 chmod 0600" 措辞偏强（失败仅告警不终止）

- **位置**: 中文 §4.1.1（L154）"bind 后对 socket 文件强制 chmod 0600"、§6（L396）；英文镜像同。
- **代码事实**: `nextalk.cpp` L112-114: `chmod` 失败仅 `NEXTALK_WARN` 并继续监听，不拒绝服务。数值 0600、bind 后执行均属实 ✓。
- **修复建议**: 加半句"chmod 失败时仅记录告警，不中止监听"。

### L2. §2.2 目录树两处极小遗漏（不影响判定）

- **核查结论**: 目录树**总体准确**——`lib/` 下 8 个顶层目录、`services/` 全部 17 个文件、`asr/` 5 个文件、`ffi/` 7 个绑定文件、`constants/` 6 类常量逐一对得上，无虚构文件。仅两处小项：
  - `libs/` 下实际还有 `VERSIONS.md`（树只列 2 个 .so）；
  - `utils/` 实际含 `clipboard_helper.dart` 与 `diagnostic_logger.dart`，树写"clipboard_helper 等"已用"等"覆盖，可选择性点名。
- **修复建议**: 可不改；若求全，`libs/` 补 `VERSIONS.md`、`utils/` 点名 diagnostic_logger。

### L3. version.yaml 注释与现实不符（顺带发现，非文档错误）

- `version.yaml` 注释称 app_version "同步到 voice_capsule/pubspec.yaml"，但 `pubspec.yaml` 仍为 `0.2.3+1`（version.yaml 为 0.2.8）。文档 §5.1 已正确声明"pubspec 的 version 不作为发布依据"，与代码现状一致 ✓；建议在文档该条后加一句"pubspec.yaml 当前值滞后，属预期"，或修 version.yaml 注释。

### L4. 中英镜像一致性：结构与数字一致，错误亦同步存在

- **抽查结论**: 两份文档章节结构逐节对应；关键数字全部一致——1MB（zh L163/L398，en L163/L400）、30 秒（L164）、0600（L154/L396-398）、app 0.2.8 / addon 0.3.0（L350/L352）、剪贴板 2 秒自动隐藏（L189，代码 `hotkey_controller.dart` L430 `Duration(seconds: 2)` ✓）、150ms 首帧等待未提及（无需）。英文版 404 行 vs 中文 402 行仅为换行差异。
- **注意**: C1、C2、H1、H2、M1-M3 的错误在两份中**镜像存在**，修复必须双份同步，否则镜像一致性反而放大错误。

---

## 核实通过项（抽样列举，供信心参考）

| 文档陈述 | 代码佐证 | 结论 |
| :--- | :--- | :--- |
| MAX_MESSAGE_SIZE = 1MB，超限断开 | nextalk.cpp L25、L180-183（break→close） | ✓ |
| recv 超时 30s + 零字节探活 | nextalk.cpp L143-167（SO_RCVTIMEO 30s；`send(fd,&probe,0,MSG_NOSIGNAL)`） | ✓ |
| /tmp/nextalk-fcitx5.sock 回退 | nextalk.cpp L55-61 | ✓ |
| 单客户端顺序处理、无并发 | nextalk.cpp L125-138（accept→handleClient 串行） | ✓ |
| preedit→commitString→清 preedit 三步 IME 周期 | nextalk.cpp L251-266 | ✓ |
| 主 Isolate 轮询（Future.delayed + 阻塞 read），无后台 Isolate | audio_inference_pipeline.dart L485-554（100ms 目标间隔、10ms 可中断延迟） | ✓ |
| 零拷贝：calloc 缓冲区同一指针给采集与 acceptWaveform | audio_capture.dart L290、pipeline L564-582 | ✓ |
| AudioCapture 门面：libpulse-simple 主 / PortAudio 回退 | audio_capture.dart L38-61、L201 | ✓ |
| sink 预查询唤醒 PipeWire 节点、pa_context_get_source_info_list 枚举 | libpulse_ffi.dart L136-150、L235-237、L285 | ✓ |
| 模型来源 GitHub Releases k2-fsa/sherpa-onnx（三个 URL 均是） | model_manager.dart L82-110 | ✓ |
| 存储路径 $XDG_DATA_HOME/nextalk/models | model_manager.dart L162-168 | ✓ |
| §4.5 YAML 字段（engine/zipformer.type/custom_url/sensevoice.use_itn/language/custom_url/audio.input_device，无快捷键字段） | settings_constants.dart L89-184 模板逐字段一致 | ✓ |
| 单实例 socket $XDG_RUNTIME_DIR/nextalk.sock，--toggle/--show/--hide | single_instance.dart L28-32、main.dart L79-98 | ✓ |
| 剪贴板回退 + 2 秒自动隐藏 | fcitx_client.dart L118-119、hotkey_controller.dart L423-430 | ✓ |
| RPATH $ORIGIN/lib | linux/CMakeLists.txt L19 | ✓ |
| version.yaml app 0.2.8 / addon 0.3.0，独立管理 | version.yaml | ✓ |
| DEB/RPM 由 build-pkg.sh 产出、包版本取自 version.yaml | build-pkg.sh L67-86、L171-188 | ✓ |
| FFI 三组绑定拆分（online/offline/vad） | lib/ffi/ 目录实际文件 | ✓ |

---

## 修复优先级建议

1. **必须修（阻塞基线）**: C1（三处 silero VAD 表述+架构图）、C2（ACK 规格）。
2. **应修（发布前）**: H1（模型表 4 行→3 行）、H2（版本注入表述或补 build-pkg.sh 缺口）。
3. **建议修**: M1-M3、L1。
4. **可选**: L2-L4。

全部修复须中英两份同步提交。
