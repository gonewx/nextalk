# NexTalk 配置说明

本目录包含 NexTalk 语音识别系统的配置文件模板。

## 配置文件

### nextalk.yaml
主配置文件，包含以下配置分组：

#### 🌐 服务器配置 (server)
- **host**: FunASR 服务器地址 (默认: localhost)
- **port**: 服务器端口 (默认: 10095，需与 funasr_wss_server.py 一致)
- **use_ssl**: 是否启用 SSL 加密
- **reconnect_attempts**: 连接失败重试次数

#### 🎤 音频配置 (audio)
- **sample_rate**: 音频采样率 (推荐: 16000Hz)
- **channels**: 声道数 (推荐: 1 单声道)
- **device_id/device_name**: 指定音频输入设备
- **noise_suppression**: 启用噪声抑制

#### ⌨️ 快捷键配置 (hotkey)
- **trigger_key**: 触发语音识别的快捷键 (默认: "ctrl+alt+space")
- **conflict_detection**: 快捷键冲突检测
- **enable_sound_feedback**: 按键声音反馈

#### 🖥️ 界面配置 (ui)
- **show_tray_icon**: 显示系统托盘图标
- **auto_start**: 开机自动启动
- **show_notifications**: 显示通知消息

#### 📝 文本注入配置 (text_injection)
- **auto_inject**: 自动注入识别结果到光标位置
- **fallback_to_clipboard**: 注入失败时使用剪贴板
- **compatible_apps**: 兼容应用程序列表

#### 🎯 语音识别配置 (recognition)
- **mode**: 识别模式 (2pass/online/offline)
- **use_itn**: 启用文本标准化
- **hotwords**: 热词列表，提高特定词汇识别率

#### 📋 日志配置 (logging)
- **level**: 日志级别 (INFO/DEBUG/WARNING/ERROR)
- **file_path**: 日志文件保存路径
- **console_output**: 控制台输出开关

## 使用说明

1. **首次运行**: NexTalk 会自动在用户数据目录创建配置文件
2. **手动配置**: 复制 `config/nextalk.yaml` 到用户数据目录进行自定义
3. **配置验证**: 应用启动时会自动验证配置文件有效性

## 用户数据目录

配置文件默认位置：
- **Windows**: `%APPDATA%\NexTalk\nextalk.yaml`
- **Linux**: `~/.config/nextalk/nextalk.yaml`  
- **macOS**: `~/.config/nextalk/nextalk.yaml`

## 配置热重载

修改配置文件后，可以通过系统托盘菜单选择"重新加载配置"来应用更改，无需重启应用。

## 常见问题

### Q: 快捷键不生效？
A: 检查是否与其他应用冲突，尝试更换快捷键组合。

### Q: 语音识别不准确？
A: 调整音频采样率到 16000Hz，启用噪声抑制。

### Q: 文本注入失败？
A: 将应用添加到 `incompatible_apps` 列表，使用剪贴板模式。