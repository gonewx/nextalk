# PRD 质量评审 — Nextalk PRD v1.2

- **评审对象**：`docs/prd_zh.md`（中文主文档）与 `docs/prd.md`（英文镜像），v1.2（2026-07-09，目标：与 v0.2.8 代码库对齐）
- **评审依据**：`.claude/skills/bmad-prd/assets/prd-validation-checklist.md`（七维度评审 rubric）
- **事实核对来源**：`_bmad-output/epics.md`、`_bmad-output/implementation-artifacts/sprint-status.yaml`、`README.md`，以及 v0.2.8 代码（`voice_capsule/lib/`、`addons/fcitx5/src/nextalk.cpp`）
- **评审日期**：2026-07-09

## 总体判定（Overall verdict）

**有条件通过。** v1.2 对齐工作总体质量高：双引擎 ASR、silero VAD、libpulse-simple 音频栈、模型管理、i18n、音频设备选择、打包发布等新增/修正条目均与 v0.2.8 代码逐一核实为准确，FR 编号稳定连续，中英镜像语义一致，NFR 基本可测量。但存在一处与"对齐代码"这一版本目标直接冲突的事实性错误（FR4 焦点锁定），以及第 5 节对 epics.md 的引用计数错误和"唯一事实来源"自相矛盾的问题——这两类问题修复前，PRD 不应作为下游依据分发。

---

## 1. 决策就绪度（Decision-readiness）— adequate

作为 brownfield 对齐型 PRD，v1.2 的"决策"多为既成事实的记录（SCP-002 快捷键方案、剪贴板 fallback、SenseVoice 默认引擎），变更日志（§1 Change Log）清楚交代了每次版本的取舍来源，SCP-002 变更在 FR6 中以引用块显式标注，这是好的实践。Epic 3 的未完成状态（3-9 待评审）也如实呈现，没有粉饰。

### Findings

- **medium** 无 Open Questions / 假设清单（全文）— 3-9 尚在评审（sprint-status.yaml 标注 `ready-for-review`，且注释"重构为 libpulse-simple 录音……待用户测试验证"），意味着 FR2/FR11 所述音频栈行为仍有待验证的成分，但 PRD 将其写成已定事实，未标注任何 `[ASSUMPTION]` 或待决事项。*修复：* 在 FR2/FR11 或第 5 节 Epic 3 处补一句"3-9 音频栈重构待用户验证，相关行为描述以验收结果为准"。

## 2. 实质重于形式（Substance over theater）— strong

无 persona 堆砌、无套话式 NFR。NFR1 给出了产品特定阈值（20ms 上屏延迟、RTF < 1、100ms 音频块 < 100ms/参考硬件 < 10ms），NFR2 对"离线"的边界（仅首次下载联网、可自定义 URL/手动放置模型实现完全离线）交代得具体而诚实——这是对 v1.0"纯离线无网络请求"的实事求是修正。无需额外发现。

## 3. 战略一致性（Strategic coherence）— strong

五条目标（§1 Goals）与 FR/NFR 一一呼应（透明 UI→FR1/NFR4，隐私性能→FR2/NFR1/NFR2，即说即打→FR3，Fcitx5 集成+降级→FR4/FR7），四个 Epic 的推进顺序（Bridge→Brain→Product→Distribution）体现清晰的价值递进。无发现。

## 4. 完成标准清晰度（Done-ness clarity）— adequate

多数 FR 有可验证后果（FR7 的 2 秒自动隐藏与提示文案、FR8 的进度/取消/完整性校验、FR9 列举了 5 类必须可视化处理的故障、FR11 的 CLI 三种模式）。少量条目留有模糊：

### Findings

- **low** "无可感知掉帧"不可测（§2.2 NFR1 第三条，中英同）— 主观表述，无法验收。*修复：* 改为可测阈值，如"录音期间 UI 动画帧率 ≥ 55fps（60Hz 屏）"或引用 front-end-spec 中的动画性能标准。
- **low** FR8 "校验完整性"未指明机制（§2.1 FR8）— epics.md Story 2.4 明确为 SHA256 比对，PRD 弱化为"校验完整性"。*修复：* 补"（SHA256）"，与 Story 2.4 验收标准对齐。

## 5. 范围诚实度（Scope honesty）— thin（本次评审最严重问题所在）

### Findings

- **critical** FR4 "焦点锁定"与 epics.md 及 v0.2.8 代码直接矛盾（§2.1 FR4，`prd_zh.md:44` / `prd.md:44`）— PRD 声称"录音期间切换窗口，文本仍提交到开始录音时的目标窗口"。但：(1) epics.md Story 3.6（`epics.md:591`）明确标注"**SCP-002 变更：焦点锁定机制已移除**，Wayland 环境下如切换窗口可能导致文本提交到当前焦点窗口"，Story 3.5 中焦点锁定验收标准已划线删除；(2) v0.2.8 插件代码 `addons/fcitx5/src/nextalk.cpp` 的 `commitText()` 在**提交时**调用 `instance_->mostRecentInputContext()` 解析目标，无任何"录音开始时捕获输入上下文"的锁定逻辑；(3) git 历史显示焦点锁定随插件侧快捷键机制引入（d60eec8），又随 SCP-002 极简架构（e970149）一并移除。README 的 "Focus Lock" 特性宣称同样过时。v1.2 的目标恰是与代码对齐，此条为对齐失败。*修复：* 三选一并保持三处文档一致——(a) 从 FR4 删除焦点锁定，改为如实描述"提交时以当前最近输入上下文为目标，窗口本身不夺焦（依赖胶囊窗口不接受焦点的实现）"；(b) 若焦点锁定确为需求，将其标注为未实现的目标需求并开 Story；(c) 若近期已在别处重新实现，补充代码出处。同时修正 README.md 第 19 行的 Focus Lock 宣称。
- **high** "唯一事实来源" epics.md 自身停留在 v1.1，与 PRD v1.2 矛盾（§5 引言，`prd_zh.md:107`）— PRD 宣称 epics.md 为唯一事实来源，但 epics.md 的 Requirements Inventory（`epics.md:19-51`）仍是旧版：FR2 写"流式 Zipformer + PortAudio"（无 SenseVoice/libpulse）、FR3 写"Sherpa 内置 VAD"（PRD v1.2 已改为独立 silero VAD）、FR6 写"默认键位 Right Alt，支持配置文件自定义"（已被 SCP-002 废弃）、NFR2 写"无网络请求"；FR Coverage Map（`epics.md:74-83`）只覆盖 FR1–FR6，FR7–FR12 无归属。下游读者顺着"唯一事实来源"链接会读到与 PRD 冲突的需求定义。*修复：* 同步更新 epics.md 的需求清单与覆盖表至 v1.2（含 FR7–FR12 → Epic 映射），或至少在 PRD §5 注明"epics.md 的需求清单为 v1.1 历史快照，需求定义以本 PRD §2 为准，epics.md 仅作 Story 分解与验收标准之用"。
- **medium** 无 Non-Goals 表述（全文）— 例如"不支持非 Fcitx5 输入法框架的原生上屏（仅剪贴板降级）""不做说话人识别/标点以外的后处理"等边界靠读者自行推断。对齐型 PRD 影响有限，但补 3-4 条 Non-Goals 成本低收益高。*修复：* 在 §2 末尾补简短 Non-Goals 小节。

## 6. 下游可用性（Downstream usability）— adequate（有两处必须修复的引用错误）

FR1–FR12、NFR1–NFR4 编号连续、无重复，v1.2 新增条目均标注了来源 Story/Epic，这对追溯友好。但对 epics.md 的两处引用不成立：

### Findings

- **high** "4 个 Epic / 24 个 Story" 计数与 epics.md 不符（§5 引言，`prd_zh.md:107` / `prd.md:107`）— epics.md 实际仅含 **23** 个 Story（Epic1×4 + Epic2×7 + Epic3×8 + Epic4×4），编号从 3.6 直接跳到 3.8，**Story 3.7 不存在于 epics.md**。24 的数字来自 implementation-artifacts 目录（含 `3-7-init-wizard-error-handling.md`，共 24 个 story 文件）。*修复：* 将 Story 3.7（初始化向导与错误处理）补入 epics.md Epic 3（使 24 计数成立），或将 PRD 改为"23 个 Story"并另行说明 3-7 的出处。前者是正解——3-7 已实现（sprint-status 为 done）却在"唯一事实来源"中缺席，本身就是 epics.md 的缺陷。
- **high** FR4/FR9 引用的 "Story 3-7" 在 epics.md 中无法解析（§2.1 FR4 文本保护、FR9 标题）— 与上条同根：引用指向的 Story 只存在于 `_bmad-output/implementation-artifacts/3-7-init-wizard-error-handling.md`，不在 PRD 声明的事实来源文档内，下游按图索骥会扑空。*修复：* 随上条一并解决。
- **low** FR11 未提及 `nextalk audio default` 子命令（§2.1 FR11）— 代码（`voice_capsule/lib/cli/audio_command.dart:47`）与 README 均含"恢复系统默认设备"子命令，PRD 只列了交互式/`--list`/按序号三种。*修复：* 补一项"`audio default` 恢复系统默认设备"。
- **low** NFR3 兼容范围与 FR12/Story 4.4 不一致（§2.2 NFR3）— NFR3 只承诺 Ubuntu 22.04+，而 FR12 的 Docker 跨发行版编译环境（Story 4.4 验收标准）明确面向 Ubuntu 24.04、Fedora 40/41、Debian 12。*修复：* NFR3 扩写为"Ubuntu 22.04+；经 Docker 构建产物额外验证 Ubuntu 24.04 / Fedora 40/41 / Debian 12"。

## 7. 形态匹配（Shape fit）— adequate

单用户桌面工具 + brownfield 对齐，采用能力规格（capability spec）形态、无 UJ，是正确选择；UI 细节正确地外引 front-end-spec（两个语言版本各自链接对应 spec 文件，均存在）。brownfield 形态的硬要求是"现有代码引用必须准确"——除 FR4 焦点锁定（critical，见维度 5）外，抽查的其余代码事实全部核实通过：

- FR2 双引擎、SenseVoice 默认：`SettingsConstants.defaultEngineType = EngineType.sensevoice`（`voice_capsule/lib/constants/settings_constants.dart:61`），`sensevoice_engine.dart`/`zipformer_engine.dart` 存在 ✓
- FR2 音频栈：`pulse_audio_capture.dart`、`libpulse_simple_ffi.dart`（主）+ `audio_capture.dart`（PortAudio 回退）✓
- FR5/FR10 托盘引擎切换与语言子菜单：`tray_service.dart:180-217`（Story 2-7 / 3-8 标注）✓
- FR6 `--toggle/--show/--hide` 与单实例转发：`main.dart:77-96` ✓
- FR8 默认下载源 GitHub Releases（k2-fsa/sherpa-onnx）：`model_manager.dart:83` ✓
- FR9 初始化向导：`voice_capsule/lib/ui/init_wizard/` 存在，Story 3-7 状态 done ✓
- FR11 audio CLI 三种模式：`cli/audio_command.dart` ✓

### Findings

- **medium** FR6 "settings.yaml 中的 hotkey 字段仅用于界面提示文案"已过时（§2.1 FR6 SCP-002 注，`prd_zh.md:54` / `prd.md:54`）— v0.2.8 的默认配置模板（`settings_constants.dart:170-174`）中 **hotkey 已不是配置字段**，只剩一段注释指引用户去系统设置配置快捷键；`settings_service.dart` 中也无 hotkey 键的读取逻辑，界面提示文案来自 `hotkey_constants.dart`。*修复：* 改为"配置文件中不再包含 hotkey 字段，仅保留注释指引；界面提示键位由内置常量提供"。

---

## 事实核对专项结论（对应评审任务 2）

| 核对项 | PRD 表述 | 核对结果 |
| :--- | :--- | :--- |
| Epic/Story 计数 | 4 Epic / 24 Story | **不符**：epics.md 仅 23 个 Story，缺 3.7（见 high 发现） |
| Epic 状态 | E1/E2/E4 ✅ 完成，E3 收尾中（3-9 待评审） | **实质相符**：sprint-status.yaml 中 E1/E2/E4 全部 Story done，E3 的 3-9 为 ready-for-review；但 yaml 中四个 epic 的形式状态均为 `in-progress`（epic→done 需手动流转，未做）。低风险，建议顺手把 yaml 的 E1/E2/E4 流转为 done |
| 各 Epic 内容摘要 | §5 四段摘要 | 相符：与 epics.md 各 Epic 范围及 Story 清单一致 |
| 焦点锁定（FR4） | 提交到录音开始时的窗口 | **不符**：epics.md 声明已移除，代码为提交时 `mostRecentInputContext()`（critical 发现）。README 亦有同样的过时宣称 |
| audio CLI（FR11） | 交互式 / `--list` / 按序号 | 相符（README+代码），PRD 漏 `audio default`（low） |
| i18n（FR10） | 托盘切换中英、即时生效 | 与代码相符（tray_service Story 3-8）；README 托盘菜单清单未列语言项（README 过时，非 PRD 问题） |
| 剪贴板 fallback（FR7） | socket 缺失/提交失败→复制+提示+2s 隐藏 | 相符（README"Non-Fcitx5 Environment"+ Story 3.6 AC） |
| 快捷键配置方式（FR6） | 系统原生快捷键绑定 `nextalk --toggle` | 相符（README Configure Hotkey 章节）；唯 hotkey 字段表述过时（medium） |

另注（非 PRD 缺陷，建议同步）：README.md 相对 v0.2.8 明显滞后——无 SenseVoice/双引擎描述（仍称"streaming bilingual model"、配置只有 `model.type: int8|standard`）、托盘菜单无语言切换项、宣称 Focus Lock。若 PRD 修复后 README 不改，产品文档间仍互相矛盾。

## 中英镜像一致性（对应评审任务 3）

逐条抽查 FR1–FR12、NFR1–NFR4 及 §1/§3/§4/§5：编号完全对应，语义无漂移；版本标注（v1.2 更新/新增、SCP-002、Story 编号）两版一致；Change Log 三行内容一致；§3 分别正确链接 `front-end-spec_zh.md` / `front-end-spec.md`（两文件均存在）；§5 状态标记（收尾中/Wrapping up、待评审/in review）语义等价。**未发现镜像不一致问题。** 注意：上述 critical/high 发现在两份文档中同时存在，修复时须双语同步。

## 机械性检查（Mechanical notes）

- FR/NFR ID 连续无重复（FR1–FR12，NFR1–NFR4）✓
- 交叉引用：`front-end-spec(_zh).md`、`../_bmad-output/epics.md` 链接可解析 ✓；"Story 3-7"引用不可在 epics.md 内解析（已列 high）
- 术语一致性：中文文档内"上屏/提交"混用但语境无歧义；"待评审"与 sprint-status 的 `ready-for-review` 对应准确
- 无 `[ASSUMPTION]` / `[NOTE FOR PM]` 标注体系（本 PRD 未采用该规范，属可选）

## 修复优先级汇总

| 级别 | 条目 | 位置 |
| :--- | :--- | :--- |
| critical | FR4 焦点锁定与代码/epics.md 矛盾 | prd_zh.md:44 / prd.md:44（+README:19） |
| high | "24 Story" 计数错误，epics.md 缺 Story 3.7 | prd_zh.md:107 / prd.md:107（+epics.md） |
| high | Story 3-7 引用在事实来源中不可解析 | FR4、FR9 |
| high | epics.md 需求清单停留 v1.1，与"唯一事实来源"声明冲突 | §5 引言（+epics.md:19-83） |
| medium | FR6 hotkey 字段表述过时 | prd_zh.md:54 / prd.md:54 |
| medium | 无 Open Questions（3-9 待验证事项未标注） | §2/§5 |
| medium | 无 Non-Goals | §2 |
| low | FR11 漏 `audio default`；NFR1 掉帧不可测；FR8 未指明 SHA256；NFR3 与 FR12 发行版范围不一致；sprint-status.yaml epic 状态未流转 | 各对应条目 |
