# NexTalk Installation Guide

This document provides detailed instructions for installing and configuring NexTalk on Linux systems. NexTalk is a lightweight real-time local speech recognition and input system that uses the FunASR model for speech recognition and can automatically input recognized text into active windows.

## System Requirements

### Hardware Requirements
- NVIDIA GPU with CUDA support (recommended for faster speech recognition). Required VRAM depends on the specific FunASR model:
  - Small models (e.g. FunASR SenseVoice): 2-4GB VRAM may suffice
  - Medium models (e.g. FunASR Paraformer standard): At least 4-6GB VRAM recommended
  - Large models: May require 8GB or more VRAM
- Or CPU (for most FunASR models, CPU inference will be significantly slower than GPU)
- Microphone

### Operating System
- Linux (tested on Ubuntu 20.04+ and Debian 11+)
- X11 window system (required for client's `xdotool` text injection functionality)

### Software Dependencies
- Python 3.10 or higher
- `pip` or recommended `uv` package manager
- FunASR core library (`funasr`) and its dependencies (including PyTorch etc.)
- CUDA toolkit (if using GPU, version must be compatible with PyTorch and FunASR)
- System dependencies:
  - `xdotool` (for client text injection)
  - `libnotify-bin` (for client desktop notifications)
  - Audio libraries: `portaudio19-dev` (or compatible PortAudio development library)
  - `python3-tk` (required for client's `SimpleWindow` and system tray icon)

## Installation Steps

### 1. Install System Dependencies

```bash
# Update package list
sudo apt update

# Install core system tools and libraries
sudo apt install -y git xdotool libnotify-bin portaudio19-dev python3-tk python3-dev python3-pip
```

### 2. Install uv (Optional but Recommended for Package Management)

`uv` is a fast Python package installer and resolver. Refer to the official `uv` documentation for the latest installation instructions: [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv)

Typically, it can be installed via pip (if available) or other methods:
```bash
# Install uv using pip (if pip is available)
pip install uv
```

### 3. Clone NexTalk Repository

```bash
git clone https://your-repository-url/nextalk.git # Replace with actual repository URL
cd nextalk
```

### 4. Set Up Python Virtual Environment and Install Dependencies

It's recommended to execute the following commands in the project root directory (containing `pyproject.toml` or `requirements.txt`).

**Using uv (Recommended):**

```bash
# Create or activate .venv virtual environment
uv venv

# Activate virtual environment (Linux/macOS)
source .venv/bin/activate
# (Windows: .venv\Scripts\activate)

# Install project dependencies (including development dependencies)
# Assuming dependencies are defined in pyproject.toml with "dev" extra
uv pip install -e ".[dev]"
# Or, if only production dependencies or using requirements.txt:
# uv pip sync (if using uv.lock)
# uv pip install -r requirements.txt
```

**Using pip and venv (Traditional Method):**

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment (Linux/macOS)
source .venv/bin/activate
# (Windows: .venv\Scripts\activate)

# Upgrade pip
pip install --upgrade pip

# Install project dependencies (including development dependencies)
# Assuming dependencies are defined in pyproject.toml with "dev" extra
pip install -e ".[dev]"
# Or, if using requirements files:
# pip install -r requirements.txt
# pip install -r requirements-dev.txt (if development dependencies are separate)
```

## Configuring FunASR Models

### 1. Download FunASR Models

Download the required FunASR models from the official repository or other authorized sources. The models should be placed in the designated directory (typically `models/` in the project root).

Recommended models for NexTalk:
- `speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch` (Mandarin ASR)
- `speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch` (Mandarin ASR with VAD & punctuation)

```bash
# Example model directory structure
models/
├── speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
│   ├── config.yaml
│   ├── model.pb
│   └── ...
└── speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch
    ├── config.yaml
    ├── model.pb
    └── ...
```

### 2. Configure Model Paths

Edit the configuration file (typically `config.ini` or similar) to specify the model paths:

```ini
[asr]
model_dir = models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
vad_model_dir = models/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch
```

### 3. Model Configuration Options

Key configuration parameters for FunASR models:

```ini
[asr]
; Sampling rate (should match model training configuration)
sample_rate = 16000

; Number of decoding threads
decoding_thread_num = 4

; Whether to enable punctuation restoration
enable_punctuation = true

; Whether to enable voice activity detection
enable_vad = true

; Model quantization options (optional)
quantize = false
quantize_method = int8
```

## Initial Setup and Verification

### 1. Starting the Server

Run the NexTalk server using the following command from the project root directory:

```bash
python -m nextalk_server.main --config config.ini
```

Key server parameters:
- `--config`: Path to configuration file (default: config.ini)
- `--host`: Server host address (default: 0.0.0.0)
- `--port`: Server port (default: 8000)
- `--debug`: Enable debug mode (optional)

### 2. Client Connection Test

Verify client-server communication using the test client:

```bash
python -m nextalk_client.network.client --host 127.0.0.1 --port 8000
```

Expected successful connection output:
```
[INFO] Connected to server at ws://127.0.0.1:8000/ws
[DEBUG] Handshake completed
```

### 3. Basic Functionality Verification

Test core features after successful connection:

1. Audio capture test:
```python
# In client interactive shell
>>> start_recording()
[INFO] Recording started...
>>> stop_recording()
[INFO] Recording stopped. Received transcription: "测试麦克风输入"
```

2. Real-time ASR test:
```python
>>> enable_realtime_asr()
[INFO] Real-time ASR enabled
[DEBUG] Partial result: "正在测试实时语音识别"
[DEBUG] Final result: "正在测试实时语音识别功能"
```

3. Configuration verification:
```python
>>> get_config()
{
    "asr_model": "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "sample_rate": 16000,
    "vad_enabled": true
}
```

### Troubleshooting

Common issues and solutions:

1. Connection refused:
   - Verify server is running (`ps aux | grep nextalk_server`)
   - Check firewall settings
   - Validate host/port configuration

2. Audio device issues:
   - Verify microphone permissions
   - Check `arecord -l` for available devices
   - Update audio configuration in config.ini

3. Model loading errors:
   - Verify model paths in config.ini
   - Check model file permissions
   - Ensure sufficient disk space

## Advanced Configuration

### 1. Multiple Model Configuration

NexTalk supports loading multiple ASR models simultaneously. Configure in config.ini:

```ini
[asr_models]
primary = models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
secondary = models/speech_paraformer-large_asr_nat-zh-cn-8k-common-vocab8404-pytorch
fallback = models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-onnx

[model_switching]
auto_switch_sample_rate = true
8k_threshold = 8000
16k_threshold = 16000
```

### 2. Performance Tuning

Key performance parameters:

```ini
[performance]
threads = 4  # Number of inference threads
batch_size = 8  # Processing batch size
max_queue_size = 100  # Max pending requests
gpu_memory_fraction = 0.5  # GPU memory allocation

[quantization]
enable = true
bits = 8  # 8-bit quantization
calibration_samples = 1000
```

### 3. Logging Configuration

Customize logging behavior:

```ini
[logging]
level = INFO  # DEBUG, INFO, WARNING, ERROR
path = logs/nextalk.log
max_size = 10  # MB
backup_count = 5
```

### 4. Custom Hotwords

Add domain-specific vocabulary:

```ini
[hotwords]
# Format: word=boost_value (1.0-10.0)
技术术语=5.0
专业名词=3.0
公司名称=8.0
```

### Verification Commands

Check configuration effectiveness:

```bash
# Verify model loading
python -m nextalk_server.funasr_model --check-config config.ini

# Test performance settings
python -m nextalk_server.audio_processors --benchmark --config config.ini

# Validate hotwords
python -m nextalk_client.network.client --test-hotwords "技术术语 专业名词"
```

## 5. Common Installation Issues

### 1. PortAudio/PyAudio Errors
Error when running `import pyaudio`:
```python
OSError: PortAudio library not found
```

Solution:
```bash
# Reinstall PortAudio development libraries
sudo apt-get install --reinstall portaudio19-dev
# Then reinstall PyAudio
pip install --force-reinstall pyaudio
```

### 2. CUDA Version Mismatch
Error message:
```
CUDA error: no kernel image is available for execution on the device
```

Solutions:
1. Check CUDA version compatibility:
```bash
nvidia-smi  # Shows driver version
nvcc --version  # Shows runtime version
```
2. Reinstall PyTorch with correct CUDA version:
```bash
pip install torch torchaudio --extra-index-url https://download.pytorch.org/whl/cuXXX
# Replace XXX with your CUDA version (e.g. cu117 for CUDA 11.7)
```

### 3. Model Download Failures
When models fail to download from ModelScope:
1. Set up HTTP proxy if needed:
```python
# In Python before loading models
import os
os.environ['HTTP_PROXY'] = 'http://your-proxy:port'
os.environ['HTTPS_PROXY'] = 'http://your-proxy:port'
```
2. Or manually download models:
```bash
git lfs install
git clone https://www.modelscope.cn/namespace/model-name.git
```

## 6. Advanced Configuration

### Custom Model Integration
To use custom ASR models not from ModelScope:

1. Prepare model files in the structure:
```
custom_model/
├── config.yaml
├── model.pb
├── am.mvn
└── ...
```

2. Update config.ini:
```ini
[asr]
model_dir = path/to/custom_model
custom_model = true
```

### Multi-language Support
Configure multiple language models:

```ini
[language_models]
default = zh-CN
zh-CN = models/paraformer-zh
en-US = models/paraformer-en
ja-JP = models/paraformer-ja

[language_switching]
auto_detect = true
fallback = zh-CN
```

### Performance Optimization
For low-latency requirements:

```ini
[realtime]
chunk_size = 1600  # 100ms for 16kHz
chunk_interval = 10  # ms
max_alternatives = 1
```

[Additional advanced configurations will be translated next...]