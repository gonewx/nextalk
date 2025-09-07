# NexTalk Docker 镜像
# 多阶段构建以减小镜像大小

# 构建阶段
FROM python:3.10-slim as builder

# 设置工作目录
WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    portaudio19-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt requirements-build.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pyinstaller>=6.0.0

# 复制源代码
COPY . .

# 构建可执行文件
RUN python scripts/build.py --mode onefile --skip-check

# 运行阶段
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONUNBUFFERED=1

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    portaudio19 \
    pulseaudio \
    libxcb1 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    x11-utils \
    libx11-6 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrender1 \
    libxcb-randr0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libfontconfig1 \
    libfreetype6 \
    libssl3 \
    libdbus-1-3 \
    libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd -m -s /bin/bash nextalk && \
    mkdir -p /app /config /logs && \
    chown -R nextalk:nextalk /app /config /logs

# 设置工作目录
WORKDIR /app

# 从构建阶段复制可执行文件
COPY --from=builder /build/dist/nextalk /app/
COPY --from=builder /build/config/nextalk.yaml /config/

# 切换到非 root 用户
USER nextalk

# 设置音频相关环境变量
ENV PULSE_RUNTIME_PATH=/var/run/pulse

# 挂载点
VOLUME ["/config", "/logs"]

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f nextalk || exit 1

# 入口点
ENTRYPOINT ["/app/nextalk"]

# 默认参数
CMD ["--config", "/config/nextalk.yaml", "--log-dir", "/logs"]