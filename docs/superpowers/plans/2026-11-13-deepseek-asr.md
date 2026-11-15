# DeepSeek 云端引擎实施计划

> 执行方式：当前会话按 executing-plans 技能逐项实现，结束后独立评审。

**目标：** 新增独立云端引擎及即时配置、连接测试窗口。
**架构：** 独立 Dio 客户端负责协议与脱敏错误；引擎负责 PCM 缓冲及请求隔离；配置窗口复用主窗口服务。收尾接口使用 FutureOr，保留本地同步实现。
**技术栈：** Flutter / Dart、Dio、现有 YAML 设置。
**设计：** ../specs/2026-11-13-deepseek-asr-design.md（用户已确认）

## 全局约束
- 16 kHz 单声道 PCM16 WAV；120 秒自动停止；不自动重试付费请求。
- UI 保存密钥立即生效，文件优先于环境变量；日志不包含密钥。
- 取消不上传；关闭麦克风后才等待 HTTP；旧结果不得串入新会话。
- 不加载云端模式不需要的本地模型；保留现有默认引擎。

## 评审重点
- 快速取消、重新录音时的迟到结果和共享状态（任务 2）。
- 保存失败、配置来源覆盖和旧测试结果（任务 3）。
- 云端启动无本地模型、切换中失败（任务 4）。
- 请求错误体包含敏感信息（任务 1）。
- 达到 120 秒后尾帧越界、空录音（任务 1、2）。

## 任务 1：协议客户端和引擎
- [x] 新增 services/asr/deepseek_asr_client.dart 和 deepseek_asr_engine.dart。
- [x] 接口：transcribe(Uint8List wav, String apiKey, {CancelToken? cancelToken}) → Future<String>；DeepSeekConfig(apiKey)。
- [x] 测试 WAV 编码、multipart、错误脱敏、上限和取消隔离，运行 flutter test test/services/asr/deepseek_asr_test.dart。

## 任务 2：异步收尾与录音生命周期
- [x] asr_engine.dart 使用 FutureOr<ASRResult> finalizeUtterance()；更新 pipeline 所有收尾调用。
- [x] 云端停止先释放麦克风，独立取消，不触发上传；通过会话代数隔离旧 stop。
- [x] hotkey_controller.dart 处理网络异常、时长上限通知及重新录音时的取消。
- [x] 回归 audio_inference_pipeline_test.dart，增加云端异步与取消测试。

## 任务 3：设置与配置 UI
- [x] 新增 deepseek_settings_store.dart，原子更新 YAML，0600 权限，保留其他配置。
- [x] SettingsService 提供 deepseekApiKey / hasDeepSeekConfig / saveDeepSeekApiKey(String)。
- [x] 新增 ui/deepseek_settings_view.dart，草稿、遮罩、测试、保存／取消和迟到测试隔离。
- [x] 运行配置持久化及 widget 测试，验证失败不切换、取消不保存、配置即时生效。

## 任务 4：应用接线和交付
- [x] 更新枚举、工厂、初始化器、model_manager、main、tray_service 和 nextalk_app。
- [x] 缺少配置打开窗口；常驻设置入口；配置期间禁止录音与窗口自动隐藏。
- [x] 更新中文文档、中英文 UI 文案及配置模板。
- [x] 执行 flutter analyze 和相关测试；必要时构建 Linux 应用；独立评审并修复问题。

## 执行记录
- 已完成方案确认；按用户授权直接实施，不增加重复确认。
- 在当前工作区保留可审查差异，不自动提交用户未要求的 Git 提交。

- 完成独立评审，修复原生窗口焦点、YAML 特殊结构和取消／重启竞态。
- 相关回归：168 项通过；设置／模型／快捷键补充回归 86 项通过（与前组有重复）；取消会话专项 2 项通过。
- Linux debug 构建成功；静态分析无 error，保留仓库已有 warning/info。
- Xvfb 独立桌面使用临时 XDG 配置验证：无模型／无密钥启动打开配置、键盘输入、保存并切换成功、配置权限 0600。使用占位密钥，没有发送真实 API 请求。
- 最终差异保留在当前工作区，未提交、未安装或替换正在使用的应用。
