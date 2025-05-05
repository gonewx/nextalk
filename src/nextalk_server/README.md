# NexTalk Server - FunASR版

这是NexTalk语音识别服务器的简化版本，专门为FunASR模型优化。该版本移除了多模型支持，并将所有模块扁平化，避免过度设计。

## 功能特点

- 实时语音识别，使用FunASR Paraformer模型
- 同时支持流式和离线两种识别模式（2pass）
- 简化的架构，更易于维护和扩展
- 通过WebSocket提供语音识别服务

## 文件结构

```
nextalk_server/
├── __init__.py           # 包初始化文件
├── main.py               # 应用入口
├── app.py                # FastAPI应用配置
├── websocket_routes.py   # WebSocket路由定义
├── websocket_handler.py  # WebSocket处理器
├── funasr_model.py       # FunASR模型封装
├── audio_processors.py   # 音频处理（VAD和缓冲区）
├── config.py             # 配置管理
├── cleanup.sh            # 清理脚本
└── README.md             # 文档
```

## 快速开始

1. 安装依赖:

```bash
pip install -r requirements.txt
```

2. 启动服务器:

```bash
python -m nextalk_server.main
```

## 配置选项

服务器支持以下命令行选项:

```
--host TEXT                 服务器主机名
--port INTEGER              服务器端口
--log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]
                            日志级别
--model-path TEXT           模型缓存路径
--device [cpu|cuda]         计算设备
--ngpu INTEGER              使用的GPU数量
--ncpu INTEGER              使用的CPU核心数
--vad-sensitivity [1|2|3]   VAD灵敏度 (1-低, 3-高)
```

## WebSocket API

服务器提供以下WebSocket端点：

- `/ws` - 主WebSocket端点，用于语音识别

### 消息格式

#### 客户端到服务器：

1. 二进制音频数据（PCM 16-bit，16kHz采样率）
2. 文本命令（JSON格式）:
   - 控制命令：`{"command": "restart|stop|start"}`
   - 配置选项：`{"mode": "online|offline|2pass", "is_speaking": true|false, ...}`

#### 服务器到客户端：

1. 识别结果：`{"type": "transcription", "text": "识别文本", "is_final": true|false}`
2. 状态更新：`{"type": "status", "status": "listening|processing|error"}`
3. 错误消息：`{"type": "error", "code": "错误代码", "message": "错误信息"}`

## 测试

项目包含的测试位于`nextalk/tests/server`目录中，分为单元测试和集成测试：

```
tests/server/
├── unit/                 # 单元测试
│   ├── test_vad.py       # VAD测试
│   └── test_audio_buffer.py  # 音频缓冲区测试
└── integration/          # 集成测试
    └── test_websocket_flow.py  # WebSocket流程测试
```

运行测试:

```bash
# 运行所有测试
pytest nextalk/tests/server

# 只运行单元测试
pytest nextalk/tests/server/unit

# 只运行集成测试
pytest nextalk/tests/server/integration
```

注意：集成测试中的某些WebSocket测试可能在同步TestClient中不可靠，因此被标记为跳过。

## 架构说明

该简化版本使用以下核心组件：

1. **WebSocketHandler**: 处理WebSocket连接和消息
2. **FunASRModel**: 封装FunASR模型，提供语音识别功能
3. **AudioBuffer & VADFilter**: 处理音频流和语音活动检测
4. **Config**: 管理全局配置 