# NexTalk 用户指南

## 目录

- [NexTalk 用户指南](#nextalk-用户指南)
  - [目录](#目录)
  - [基本使用](#基本使用)
    - [启动方式](#启动方式)
      - [使用统一启动脚本（推荐）](#使用统一启动脚本推荐)
      - [使用传统脚本](#使用传统脚本)
      - [作为Python模块启动](#作为python模块启动)
    - [热键操作](#热键操作)
    - [转录控制](#转录控制)
  - [配置选项](#配置选项)
    - [模型选择](#模型选择)
    - [音频设置](#音频设置)
    - [界面设置](#界面设置)
  - [故障排除](#故障排除)
    - [连接问题](#连接问题)
    - [识别问题](#识别问题)
    - [模型下载问题](#模型下载问题)
    - [文本注入问题](#文本注入问题)
    - [日志检查](#日志检查)
      - [使用统一脚本查看日志](#使用统一脚本查看日志)
      - [使用传统方法查看日志](#使用传统方法查看日志)
      - [使用调试脚本](#使用调试脚本)
      - [常见问题调试](#常见问题调试)
      - [调试模式启动](#调试模式启动)
  - [高级功能](#高级功能)
    - [多语言支持](#多语言支持)
    - [FunASR特有配置](#funasr特有配置)
    - [性能调优](#性能调优)
  - [其他资源](#其他资源)

## 基本使用

### 启动方式

NexTalk提供了多种启动方式，您可以根据需要选择最适合的方式：

#### 使用统一启动脚本（推荐）

NexTalk现在提供了一个统一的启动脚本`nextalk.py`，它可以启动服务器、客户端或完整的工作流：

```bash
# 启动完整工作流（服务器+客户端）
python nextalk/scripts/nextalk.py start

# 启动服务器
python nextalk/scripts/nextalk.py server

# 启动客户端
python nextalk/scripts/nextalk.py client

# 获取帮助信息
python nextalk/scripts/nextalk.py --help
```

启用调试模式并指定日志文件：

```bash
# 启动调试模式的完整工作流
python nextalk/scripts/nextalk.py start --debug

# 启动调试模式的服务器，并指定日志文件
python nextalk/scripts/nextalk.py server --debug --log-file server.log

# 启动调试模式的客户端，并指定服务器地址
python nextalk/scripts/nextalk.py client --debug --server-host 192.168.1.100
```

#### 使用传统脚本

如果您习惯使用旧的脚本，这些脚本仍然可用：

```bash
# 启动服务器
python -m nextalk_server.main

# 启动客户端
python -m nextalk_client.main

# 使用Shell脚本启动调试模式
./scripts/run_server_debug.sh
./scripts/run_client_debug.sh
./scripts/run_debug_workflow.sh
```

#### 作为Python模块启动

对于开发者，您可以直接导入模块并启动：

```python
# 启动服务器
from nextalk_server.main import app
import uvicorn
uvicorn.run(app, host="127.0.0.1", port=8000)

# 启动客户端
from nextalk_client.main import run_client
run_client(debug=True)
```

### 热键操作

NexTalk使用全局热键激活语音识别。默认热键为：

- `Ctrl+Shift+Space`: 开始/停止语音识别
- `Esc`: 取消当前转录

您可以在配置文件中自定义这些热键。

### 转录控制

NexTalk提供了多种控制转录过程的方式：

- **自动模式**: 自动检测语音开始和结束，无需手动控制
- **手动模式**: 按下热键开始录音，再次按下停止并转录
- **持续模式**: 连续录音并实时转录，直到手动停止

## 配置选项

配置文件位于 `~/.config/nextalk/config.ini`，首次运行时会自动创建。
或者您可以将 `config/default_config.ini` 复制到该位置并进行修改。

### 模型选择

您可以在配置文件中选择不同的语音识别模型：

```ini
[server]
# Whisper模型可选值: tiny, base, small, medium, large, large-v3, distil-large-v3
# FunASR模型可选值: paraformer-zh, paraformer-zh-streaming, SenseVoiceSmall
default_model = large-v3
# 可选值: cpu, cuda
device = cuda
```

Whisper模型的对比：
- `tiny`: 最小，速度最快，精度最低
- `base`/`small`: 平衡速度和精度
- `medium`/`large`: 高精度，但需要更多计算资源
- `large-v3`/`distil-large-v3`: 最新模型，支持更多语言

FunASR模型的对比：
- `paraformer-zh`: 标准中文模型，精度较高，速度适中
- `paraformer-zh-streaming`: 流式中文模型，实时性好，适合持续转录
- `SenseVoiceSmall`: 小型通用模型，资源占用少，速度快

选择模型时的建议：
- 对于中文识别，推荐使用FunASR的`paraformer-zh`或`paraformer-zh-streaming`模型
- 对于英文或多语言识别，推荐使用Whisper的`large-v3`或`medium`模型
- 在资源受限的设备上，可以选择较小的模型，如Whisper的`small`或FunASR的`SenseVoiceSmall`

### 音频设置

调整音频设置以获得最佳识别效果：

```ini
[audio]
# 音频后端选择 (pulseaudio, alsa, portaudio)
audio_backend = pulseaudio
# 采样率 (16000推荐)
sample_rate = 16000
# 声道数 (1=单声道)
channels = 1
```

### 界面设置

客户端界面和行为设置：

```ini
[client]
# 服务器连接设置
server_host = 127.0.0.1
server_port = 8765
# 转录结果显示时间(秒)
notification_timeout = 5
# 自动输入文本到当前活动窗口
auto_type = true
```

## 故障排除

### 连接问题

如果客户端无法连接到服务器：

1. 确保服务器已启动并在运行
2. 检查客户端配置中的服务器地址和端口是否正确
3. 检查网络连接，特别是防火墙设置
4. 尝试使用`ping`或`telnet`测试连接

### 识别问题

如果语音识别不准确或失败：

1. 确保麦克风正常工作且未静音
2. 尝试调整麦克风音量或距离
3. 如果GPU内存不足，尝试使用更小的模型或切换到CPU模式
   - 在 `~/.config/nextalk/config.ini` 中将 `device` 设置为 `cpu`

### 模型下载问题

首次运行NexTalk时，系统会尝试下载语音识别模型。如果自动下载失败（如出现 `basic_string::_S_construct null not valid` 错误），您可以使用我们提供的模型下载工具手动下载模型。

**模型下载工具使用方法**:

使用 `download_models.py` 脚本进行模型管理：

```bash
# 查看所有可用模型列表
python nextalk/scripts/download_models.py --list

# 检查已下载的模型
python nextalk/scripts/download_models.py --check

# 下载指定模型（推荐先尝试小模型）
python nextalk/scripts/download_models.py --download small

# 下载大型模型（更准确但需要更多资源）
python nextalk/scripts/download_models.py --download large-v3

# 指定自定义缓存目录
python nextalk/scripts/download_models.py --download medium --cache-dir /path/to/custom/cache

# 强制重新下载模型
python nextalk/scripts/download_models.py --download large-v3 --force
```

**注意事项**:
- 建议从小型模型开始，如 `small` 或 `base`，这些模型下载更快且资源需求较低
- 较大的模型（如 `large-v3`）提供更高的识别精度，但需要更多的下载时间和系统资源
- 下载后的模型会被缓存在 `~/.cache/NexTalk/models` 目录中，后续启动将直接使用已下载的模型
- 下载需要稳定的网络连接，如果下载中断，可以使用 `--force` 选项重新开始下载

如果仍然遇到问题，可以尝试将模型配置更改为较小的模型：在 `~/.config/nextalk/config.ini` 中将 `default_model` 设置为 `small` 或 `base`。

### 文本注入问题

如果识别正常但文本没有输入到应用程序：

1. 确保已安装 `xdotool`（Linux系统）
2. 检查目标应用程序是否接受键盘输入
3. 尝试在不同的应用程序中测试

### 日志检查

如果遇到其他问题，您可以检查日志获取更多信息：

#### 使用统一脚本查看日志

```bash
# 启动调试模式并指定日志文件
python nextalk/scripts/nextalk.py server --debug --log-file server.log
python nextalk/scripts/nextalk.py client --debug --log-file client.log

# 启动完整工作流并自动保存日志到默认文件
python nextalk/scripts/nextalk.py start --debug
```

这将创建 `server_debug.log` 和 `client_debug.log` 文件，包含详细的调试信息。

#### 使用传统方法查看日志

```bash
# 运行客户端时重定向输出到日志文件
python -m nextalk_client.main > client_log.txt 2>&1
```

或者：

```bash
# 设置更详细的日志级别
export PYTHONPATH=./src
python -m nextalk_client.main --debug
```

#### 使用调试脚本

NexTalk仍然提供了传统的调试脚本，可以方便地启用详细日志并将输出保存到文件：

```bash
# 调试模式运行客户端
./scripts/run_client_debug.sh

# 调试模式运行服务器
./scripts/run_server_debug.sh

# 一键启动完整调试工作流（同时启动服务器和客户端）
./scripts/run_debug_workflow.sh
```

调试脚本将：
1. 启用详细的调试级别日志
2. 将所有日志保存到`client_debug.log`和`server_debug.log`文件中
3. 同时将输出显示在控制台上，便于实时查看
4. 将控制台输出额外保存到`client_output.log`和`server_output.log`文件中

> **提示**：推荐使用`nextalk.py start --debug`脚本进行调试，它会自动检查依赖项、启动服务器，并在正确的时机启动客户端。

#### 常见问题调试

1. **转录结果不显示**
   - 检查客户端日志中是否有"接收到转录"和"转录结果"相关信息
   - 检查服务器日志中是否有"已发送转录结果"相关信息
   - 检查xdotool是否正确安装并可用：`which xdotool`
   - 当识别到文本时，控制台应该直接显示"语音识别结果：xxx"

2. **未安装xdotool问题**
   - 如果看到"xdotool工具不可用"的错误，请安装：`sudo apt install xdotool`
   - xdotool是在Linux上进行文本注入所必需的
   - 如果不安装xdotool，识别结果仍会显示在控制台，但不会自动输入到活动窗口

3. **音频捕获问题**
   - 查看客户端日志中与音频设备相关的警告或错误
   - 确认系统中是否有可用的麦克风设备：`arecord -l`
   - 检查音频后端配置是否正确（pulse或alsa）

4. **网络连接问题**
   - 检查WebSocket连接状态日志
   - 确认服务器是否正常运行并监听在正确端口：`netstat -tuln | grep 8000`
   - 查看防火墙设置是否阻止了WebSocket连接

5. **无任何输出问题**
   - 如果程序运行后没有任何输出，请检查调试模式运行：`NEXTALK_DEBUG=1 python -m nextalk_client.main`
   - 检查控制台是否显示了任何错误消息
   - 检查Python版本是否兼容（需要3.10+）：`python --version`
   - 检查依赖项是否正确安装：`pip list | grep nextalk`

#### 调试模式启动

您也可以不使用脚本，直接启用调试模式：

```bash
# 选项1：使用命令行参数
python -m nextalk_client.main --debug

# 选项2：使用环境变量
NEXTALK_DEBUG=1 python -m nextalk_client.main

# 选项3：同时保存日志到文件
python -m nextalk_client.main --debug --log-file debug.log
```

## 高级功能

### 多语言支持

NexTalk支持多种语言的语音识别：

1. 对于英语识别：
   - 在配置文件中设置 `language=en`
   - 使用带有语言后缀的Whisper模型（例如 `small.en`）

2. 对于中文识别：
   - 在配置文件中设置 `language=zh`
   - 使用FunASR模型（如 `paraformer-zh`）或通用Whisper模型（如 `large-v3`）

3. 对于其他语言：
   - 在配置文件中设置相应的语言代码（如 `fr` 表示法语）
   - 使用通用Whisper模型（不带语言后缀的模型）
   
### FunASR特有配置

使用FunASR模型时，您可以调整以下特有的配置选项：

```ini
[Server]
# FunASR使用的VAD模型
funasr_vad_model=fsmn-vad
# 是否启用流式（实时）处理模式
funasr_streaming=true
# 标点恢复模型（可选）
funasr_punc_model=ct-punc
# 时间戳预测模型（可选）
funasr_timestamp_model=fa-zh
```

FunASR的关键配置选项：
- **VAD模型**:
  - `fsmn-vad`: 标准VAD模型，适用于大多数场景
  - `silero-vad`: 替代VAD模型，在某些嘈杂环境中可能有更好表现

- **流式处理模式**:
  - `true`: 启用流式处理（默认），适合实时转录，支持连续音频处理
  - `false`: 禁用流式处理，一次性处理整段音频，转录精度可能更高但延迟更大

- **标点恢复**:
  - 如果配置了标点恢复模型（如`ct-punc`），系统会自动为识别的文本添加标点符号
  - 对中文文本特别有用，显著提高可读性

- **时间戳预测**:
  - 通过配置时间戳模型（如`fa-zh`），可以获取每个字的时间戳信息
  - 适用于需要音频与文本精确同步的场景

### 性能调优

对于性能优化，您可以：

1. 调整VAD敏感度（在服务器配置中设置 `vad_sensitivity`，值为1-3，默认为2）
2. 使用适合您硬件的计算精度（在服务器配置中设置 `compute_type`，可选 `int8`、`float16` 或 `float32`）

## 其他资源

- 安装指南：查看 [setup_guide.md](setup_guide.md) 获取完整的安装说明
- 项目架构：查看 [architecture.md](architecture.md)（即将发布）了解NexTalk的技术架构
- 贡献指南：查看 [developer_guide.md](developer_guide.md)（即将发布）了解如何参与项目开发 