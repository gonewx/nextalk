# FunASR 语音识别服务器设置指南

## 概述

NexTalk 需要连接到 FunASR WebSocket 服务器来进行语音识别。服务器负责：
- 接收音频流
- 进行语音活动检测（VAD）
- 实时语音识别（ASR）
- 添加标点符号（Punctuation）

## 快速启动

### 1. 安装 FunASR

```bash
# 安装 FunASR
pip install funasr modelscope
```

### 2. 启动服务器

```bash
# 基本启动（使用默认配置）
python funasr_wss_server.py

# 或指定参数
python funasr_wss_server.py --host 0.0.0.0 --port 10095
```

服务器将在 `ws://localhost:10095` 上监听。

## 详细配置

### 服务器参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | 0.0.0.0 | 监听地址（0.0.0.0 表示所有网络接口） |
| `--port` | 10095 | WebSocket 端口 |
| `--ngpu` | 1 | GPU 数量（0 表示使用 CPU） |
| `--device` | cuda | 设备类型（cuda 或 cpu） |
| `--ncpu` | 4 | CPU 核心数 |

### 模型参数

服务器使用以下模型（自动从 ModelScope 下载）：

| 模型类型 | 默认模型 | 用途 |
|----------|----------|------|
| ASR 离线模型 | speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch | 高精度离线识别 |
| ASR 在线模型 | speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online | 实时流式识别 |
| VAD 模型 | speech_fsmn_vad_zh-cn-16k-common-pytorch | 语音活动检测 |
| 标点模型 | punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727 | 自动添加标点 |

### SSL/TLS 配置（可选）

如需使用加密连接（wss://）：

```bash
python funasr_wss_server.py \
    --certfile ssl_key/server.crt \
    --keyfile ssl_key/server.key
```

## 系统要求

### 最低配置
- CPU: 4 核心
- 内存: 8GB RAM
- 存储: 10GB（用于模型文件）
- Python 3.8+

### 推荐配置
- CPU: 8 核心
- 内存: 16GB RAM
- GPU: NVIDIA GPU（支持 CUDA）
- 存储: 20GB SSD

## 首次运行

### 1. 模型下载

首次运行时，服务器会自动下载所需模型（约 2-3GB）：

```bash
python funasr_wss_server.py
# 输出：
# model loading
# Downloading model files... (这可能需要几分钟)
# model loaded! only support one client at the same time now!!!!
```

模型将缓存在 `~/.cache/modelscope/` 目录。

### 2. 验证服务器

服务器启动后，可以通过以下方式验证：

```bash
# 使用 NexTalk 的验证脚本
python scripts/verify_installation.py

# 或使用测试客户端
python funasr_wss_client.py
```

## 运行模式

服务器支持三种识别模式：

### 1. 离线模式（offline）
- 最高精度
- 等待语音结束后返回完整结果
- 适合：录音、语音命令

### 2. 在线模式（online）
- 实时返回识别结果
- 边说边显示
- 适合：实时字幕、同声传译

### 3. 两遍模式（2pass）- 推荐
- 结合在线和离线模式优点
- 实时显示初步结果
- 语音结束后返回精确结果
- 适合：日常使用

在 NexTalk 配置中设置模式：

```yaml
# config/nextalk.yaml
server:
  mode: "2pass"  # 可选：offline, online, 2pass
```

## 性能优化

### 使用 GPU 加速

如果有 NVIDIA GPU：

```bash
# 检查 CUDA 是否可用
python -c "import torch; print(torch.cuda.is_available())"

# 使用 GPU 运行
python funasr_wss_server.py --ngpu 1 --device cuda
```

### CPU 模式

如果没有 GPU：

```bash
python funasr_wss_server.py --ngpu 0 --device cpu --ncpu 8
```

### 内存优化

减少内存使用：

```bash
python funasr_wss_server.py \
    --asr_model iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch \
    --asr_model_online "" \  # 禁用在线模型
    --punc_model ""  # 禁用标点模型
```

## 故障排除

### 问题：模型下载失败

**解决方案**：
1. 检查网络连接
2. 使用代理：`export http_proxy=http://proxy:port`
3. 手动下载模型到 `~/.cache/modelscope/`

### 问题：内存不足

**解决方案**：
1. 使用 CPU 模式而非 GPU
2. 减少 `--ncpu` 参数
3. 禁用不必要的模型

### 问题：连接被拒绝

**解决方案**：
1. 检查防火墙：`sudo ufw allow 10095`
2. 确认服务器正在运行：`ps aux | grep funasr_wss_server`
3. 检查端口占用：`netstat -tlnp | grep 10095`

### 问题：识别精度低

**解决方案**：
1. 确保音频采样率为 16kHz
2. 检查麦克风质量
3. 使用离线模式提高精度

## 生产环境部署

### 使用 systemd（Linux）

创建服务文件 `/etc/systemd/system/funasr.service`：

```ini
[Unit]
Description=FunASR WebSocket Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/nextalk
ExecStart=/usr/bin/python3 /path/to/funasr_wss_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable funasr
sudo systemctl start funasr
```

### 使用 Docker

```dockerfile
FROM python:3.9

RUN pip install funasr modelscope websockets

COPY funasr_wss_server.py /app/
COPY ssl_key/ /app/ssl_key/

WORKDIR /app

EXPOSE 10095

CMD ["python", "funasr_wss_server.py"]
```

构建并运行：

```bash
docker build -t funasr-server .
docker run -d -p 10095:10095 --gpus all funasr-server
```

### 使用 PM2（Node.js）

```bash
# 安装 PM2
npm install -g pm2

# 启动服务器
pm2 start funasr_wss_server.py --interpreter python3

# 设置开机自启
pm2 startup
pm2 save
```

## 多客户端支持

当前服务器一次只支持一个客户端。如需支持多客户端：

1. **运行多个实例**：
```bash
# 实例 1
python funasr_wss_server.py --port 10095

# 实例 2
python funasr_wss_server.py --port 10096
```

2. **使用负载均衡**（如 nginx）

3. **等待官方多客户端支持**

## 监控和日志

### 查看服务器日志

```bash
# 实时查看日志
python funasr_wss_server.py 2>&1 | tee funasr.log

# 使用 journalctl（如果使用 systemd）
journalctl -u funasr -f
```

### 性能监控

```bash
# 监控 GPU 使用
nvidia-smi -l 1

# 监控 CPU 和内存
htop

# 监控网络连接
netstat -an | grep 10095
```

## 安全建议

1. **使用 SSL/TLS** 加密连接
2. **限制访问来源**：
   ```bash
   # 只允许本地连接
   python funasr_wss_server.py --host 127.0.0.1
   ```
3. **使用防火墙**限制端口访问
4. **定期更新**模型和依赖

## 相关链接

- [FunASR 官方文档](https://github.com/alibaba-damo-academy/FunASR)
- [ModelScope 模型库](https://modelscope.cn)
- [NexTalk 配置指南](../README.md)