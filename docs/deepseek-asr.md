# DeepSeek 云端语音识别

适用于 Nextalk v0.4.0 及以上。DeepSeek 是可选云端引擎，默认仍使用本地 Qwen3-ASR。使用云端引擎需要可用的 API Key 和网络；停止录音后音频会离开本机上传到服务端。

在托盘打开“模型选择”，点击 DeepSeek 同行的“配置”按钮。输入 API Key，可先“测试连接”，再“保存配置”。保存后返回模型列表，点击已就绪的 DeepSeek 行切换引擎，无需重启。未配置的模型不可选择，但始终可以打开配置。模型选择、配置与下载共用普通、不透明的设置窗口，关闭后继续在托盘运行。

- 测试连接上传程序生成的 1 秒静音，不使用麦克风，会产生少量 API 用量。成功表示鉴权和 ASR 接口可用，不代表识别准确率测试。
- 录音时不显示实时转写；停止录音后上传并识别，再通过原有 Fcitx5／GNOME／剪贴板流程提交文字。
- 每次录音最长 120 秒，达到上限自动停止。支持 Esc／`nextalk --cancel` 取消，取消录音不会上传；已发出的请求会尽力取消，但服务端可能已产生用量。
- 正在录音或提交时请先结束当前操作再切换引擎。服务错误不会自动重试或切换本地引擎。

密钥保存在 `$XDG_CONFIG_HOME/nextalk/settings.yaml`（默认 `~/.config/nextalk/settings.yaml`），文件权限为仅当前用户读写。配置文件中的非空密钥优先于 `DEEPSEEK_API_KEY` 环境变量。UI 显示来源，保存后采用新配置。

```yaml
model:
  engine: deepseek
  deepseek:
    api_key: "你的 API Key"
```

接口固定为官方 HTTPS 地址，不需要填写模型名、采样率或语种。应用将录音转为 16 kHz 单声道 PCM16 WAV。使用云端引擎无需下载本地识别模型。

官方文档：https://api-docs.deepseek.com/zh-cn/guides/asr/
