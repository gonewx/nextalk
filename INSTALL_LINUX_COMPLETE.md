# Linux 完整安装指南

## 系统依赖安装

### Ubuntu/Debian 系统

```bash
# 基础系统依赖（必需）
sudo apt update
sudo apt install -y \
    python3 python3-venv python3-pip \
    xdotool python3-dbus python3-gi \
    libgirepository1.0-dev libcairo2-dev \
    pkg-config python3-dev

# GUI 托盘支持（必需）
sudo apt install -y \
    gir1.2-ayatanaappindicator3-0.1 \
    gir1.2-gtk-3.0 python3-gi-cairo

# 音频支持
sudo apt install -y \
    portaudio19-dev python3-pyaudio \
    pulseaudio-utils

# 可选：系统集成
sudo apt install -y \
    desktop-file-utils \
    xdg-utils
```

### Fedora/RHEL/CentOS

```bash
# 基础依赖
sudo dnf install -y \
    python3 python3-venv python3-pip \
    xdotool python3-dbus python3-gobject \
    gobject-introspection-devel cairo-devel \
    pkgconfig python3-devel

# GUI 托盘支持
sudo dnf install -y \
    libayatana-appindicator-gtk3 \
    gtk3-devel python3-cairo

# 音频支持
sudo dnf install -y \
    portaudio-devel python3-pyaudio \
    pulseaudio-utils
```

### Arch Linux

```bash
# 基础依赖
sudo pacman -S \
    python python-venv python-pip \
    xdotool python-dbus python-gobject \
    gobject-introspection cairo \
    pkgconf

# GUI 托盘支持
sudo pacman -S \
    libayatana-appindicator gtk3

# AUR 包（如需要）
yay -S python-pystray
```

## Python 环境设置

### 1. 创建虚拟环境

```bash
cd nextalk
python3 -m venv venv
source venv/bin/activate
```

### 2. 安装 Python 依赖

```bash
# 核心依赖
pip install -r requirements.txt

# GUI 依赖（必需，如果要使用托盘）
pip install -r requirements-gui.txt

# 开发依赖（可选）
pip install -r requirements-dev.txt
```

### 3. 解决 PyGObject 安装问题

如果 `pip install PyGObject` 失败：

**方案 A: 使用系统包（推荐）**
```bash
# 创建符号链接到虚拟环境
ln -sf /usr/lib/python3/dist-packages/gi venv/lib/python3.*/site-packages/
ln -sf /usr/lib/python3/dist-packages/cairo venv/lib/python3.*/site-packages/
```

**方案 B: 编译安装**
```bash
# 确保所有编译依赖已安装
sudo apt install -y build-essential
pip install --no-binary=:all: PyGObject
```

## 桌面环境配置

### GNOME Shell

**检查托盘支持:**
```bash
# 检查 AppIndicator 扩展
gnome-extensions list | grep appindicator

# 如果没有，安装 TopIcons Plus 或类似扩展
# 通过 https://extensions.gnome.org 安装
```

**常见问题:**
- 如果托盘图标不显示，可能需要安装托盘扩展
- Ubuntu 默认启用了 `ubuntu-appindicators@ubuntu.com`

### KDE Plasma

```bash
# 确保系统托盘小部件已添加到面板
# 在系统设置中启用"旧版系统托盘支持"
```

### XFCE/LXDE/其他

```bash
# 这些环境通常原生支持系统托盘
# 无需额外配置
```

## 音频设备配置

### 检查音频设备

```bash
# 列出可用音频设备
python -c "
import sounddevice as sd
print('可用音频设备:')
print(sd.query_devices())
"
```

### PulseAudio 配置

```bash
# 重启 PulseAudio（如有问题）
pulseaudio -k
pulseaudio --start

# 检查录音设备权限
groups | grep audio
# 如果当前用户不在 audio 组：
sudo usermod -a -G audio $USER
# 然后重新登录
```

## 安装验证

### 1. 基础功能测试

```bash
# 测试音频设备
python -c "
import sounddevice as sd
import numpy as np
print('录音测试...')
audio = sd.rec(int(2 * 16000), samplerate=16000, channels=1)
sd.wait()
print(f'录音成功，数据形状: {audio.shape}')
"
```

### 2. GUI 功能测试

```bash
# 测试托盘图标（会显示5秒）
python -c "
import os
os.environ['PYSTRAY_BACKEND'] = 'gtk'  # 强制使用稳定后端

import pystray
from PIL import Image, ImageDraw
import threading
import time

def create_icon():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill=(0, 255, 0, 255))
    return img

menu = pystray.Menu(pystray.MenuItem('测试', lambda: None))
icon = pystray.Icon('test', create_icon(), menu=menu)

def stop_after_5s():
    time.sleep(5)
    icon.stop()

threading.Thread(target=stop_after_5s, daemon=True).start()
print('显示托盘图标 5 秒...')
icon.run()
print('托盘测试完成')
"
```

### 3. 文本注入测试

```bash
# 测试文本注入功能
python debug_inject.py
```

## 故障排除

### 托盘图标不显示

**症状**: NexTalk 启动正常但托盘中看不到图标

**解决方案**:

1. **检查后端选择**:
   ```bash
   # 查看日志中的后端信息
   python -c "
   import os
   os.environ['PYSTRAY_BACKEND'] = 'gtk'
   import pystray
   print(f'使用后端: {type(pystray.Icon(\"test\", None))}')
   "
   ```

2. **强制使用 GTK 后端**:
   ```bash
   export PYSTRAY_BACKEND=gtk
   nextalk
   ```

3. **检查桌面环境支持**:
   ```bash
   # GNOME 用户检查扩展
   gnome-extensions list --enabled | grep indicator
   
   # 通用检查
   echo "桌面环境: $XDG_CURRENT_DESKTOP"
   echo "会话类型: $XDG_SESSION_TYPE"
   ```

### PyGObject 相关错误

**症状**: `No module named 'gi'` 或类似导入错误

**解决方案**:
```bash
# 重新创建符号链接
rm -f venv/lib/python3.*/site-packages/gi
rm -f venv/lib/python3.*/site-packages/cairo
ln -sf /usr/lib/python3/dist-packages/gi venv/lib/python3.*/site-packages/
ln -sf /usr/lib/python3/dist-packages/cairo venv/lib/python3.*/site-packages/
```

### 权限问题

**症状**: 音频录制失败或文本注入无权限

**解决方案**:
```bash
# 音频权限
sudo usermod -a -G audio $USER

# X11 权限（如果使用 X11）
xhost +local:

# 重新登录使权限生效
```

## 高级配置

### 环境变量配置

在 `~/.bashrc` 或 `~/.profile` 中添加:

```bash
# NexTalk 配置
export PYSTRAY_BACKEND=gtk          # 强制使用稳定的托盘后端
export PULSE_LATENCY_MSEC=50        # 降低音频延迟
export XDG_CONFIG_HOME="$HOME/.config"
```

### systemd 服务（可选）

创建 `~/.config/systemd/user/nextalk.service`:

```ini
[Unit]
Description=NexTalk Voice Recognition
After=graphical-session.target

[Service]
Type=simple
Environment="PYSTRAY_BACKEND=gtk"
ExecStart=/path/to/nextalk/venv/bin/python -m nextalk
Restart=always
RestartSec=5

[Install]
WantedBy=graphical-session.target
```

启用服务:
```bash
systemctl --user enable nextalk.service
systemctl --user start nextalk.service
```

## 性能优化

### 音频优化

```bash
# 在 ~/.asoundrc 中配置 ALSA（可选）
cat > ~/.asoundrc << 'EOF'
pcm.!default {
    type pulse
}
ctl.!default {
    type pulse
}
EOF
```

### 系统调优

```bash
# 增加实时音频处理能力（可选）
echo '@audio - rtprio 95' | sudo tee -a /etc/security/limits.conf
echo '@audio - memlock unlimited' | sudo tee -a /etc/security/limits.conf
```

---

## 完整安装脚本

将以下内容保存为 `install_linux.sh`:

```bash
#!/bin/bash
set -e

echo "=== NexTalk Linux 安装脚本 ==="

# 检测发行版
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo "无法检测 Linux 发行版"
    exit 1
fi

echo "检测到系统: $OS"

# 安装系统依赖
case $OS in
    "Ubuntu"*|"Debian"*)
        echo "安装 Ubuntu/Debian 依赖..."
        sudo apt update
        sudo apt install -y \
            python3 python3-venv python3-pip \
            xdotool python3-dbus python3-gi python3-gi-cairo \
            libgirepository1.0-dev libcairo2-dev pkg-config python3-dev \
            gir1.2-ayatanaappindicator3-0.1 gir1.2-gtk-3.0 \
            portaudio19-dev pulseaudio-utils
        ;;
    "Fedora"*|"Red Hat"*|"CentOS"*)
        echo "安装 Fedora/RHEL 依赖..."
        sudo dnf install -y \
            python3 python3-venv python3-pip \
            xdotool python3-dbus python3-gobject python3-cairo \
            gobject-introspection-devel cairo-devel pkgconfig python3-devel \
            libayatana-appindicator-gtk3 gtk3-devel \
            portaudio-devel pulseaudio-utils
        ;;
    *)
        echo "未支持的发行版，请手动安装依赖"
        exit 1
        ;;
esac

# 创建虚拟环境
echo "创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装 Python 依赖
echo "安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-gui.txt

# 设置系统包链接
echo "配置 PyGObject..."
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
SITE_PACKAGES="venv/lib/python${PYTHON_VERSION}/site-packages"

ln -sf /usr/lib/python3/dist-packages/gi "$SITE_PACKAGES/"
ln -sf /usr/lib/python3/dist-packages/cairo "$SITE_PACKAGES/" 2>/dev/null || true

# 设置环境变量
echo "配置环境变量..."
echo 'export PYSTRAY_BACKEND=gtk' >> ~/.bashrc

# 验证安装
echo "验证安装..."
python -c "
import sounddevice as sd
import pystray
from PIL import Image
print('✅ 所有依赖安装成功')
print('   音频设备:', len(sd.query_devices()), '个')
print('   托盘后端:', type(pystray.Icon('test', Image.new('RGBA', (16,16)))).__module__)
"

echo "=== 安装完成 ==="
echo "请运行以下命令启动 NexTalk:"
echo "  source venv/bin/activate"
echo "  python -m nextalk"
```

使用方法:
```bash
chmod +x install_linux.sh
./install_linux.sh
```