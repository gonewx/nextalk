# Nextalk

**High-performance offline voice input for Linux**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)]()
[![Wayland: Supported](https://img.shields.io/badge/Wayland-Supported-green.svg)]()

[简体中文](README_zh.md) | English

Convert speech to text in real-time, input to any application via the Fcitx5 input method framework. Runs completely offline to protect your privacy.

## Features

- **Offline Recognition** - Based on Sherpa-onnx streaming bilingual model (Chinese/English), data never leaves your device
- **Ultra-low Latency** - End-to-end latency < 20ms for real-time transcription
- **Transparent Floating Window** - Borderless capsule UI with breathing animation, minimal workflow disruption
- **Native Wayland Support** - System shortcuts and text submission both support Wayland
- **Focus Lock** - Switch windows while recording, text still submits to the original window
- **Model Options** - Switch between int8 (fast) / standard (high accuracy) models

## Quick Start

### Installation

**Ubuntu/Debian:**

```bash
sudo dpkg -i nextalk_0.1.0-1_amd64.deb
```

**Fedora/CentOS/RHEL:**

```bash
sudo rpm -i nextalk-0.1.0-1.x86_64.rpm
```

Fcitx5 will automatically restart after installation to load the plugin.

### Configure Hotkey

The app is triggered via system global hotkey, manual configuration required:

**GNOME:**

1. Settings → Keyboard → View and Customize Shortcuts → Custom Shortcuts
2. Click "Add Shortcut"
3. Name: `Nextalk Voice Input`
4. Command: `nextalk --toggle`
5. Shortcut: Press `Ctrl+Alt+V` (recommended)

**KDE Plasma:**

1. System Settings → Shortcuts → Custom Shortcuts
2. Edit → New → Global Shortcut → Command/URL
3. Trigger: Set to `Ctrl+Alt+V`
4. Action: `nextalk --toggle`

### Usage

1. **Launch App** - Start Nextalk from app menu, or run `nextalk`
2. **Press Hotkey** - Floating window appears and starts recording
3. **Speak** - See recognized text in real-time
4. **Press Hotkey Again** - Stop recording, text auto-inputs to current app
5. **Or Wait for Auto-submit** - Text submits automatically after pause

> **First Run**: The app will automatically download the speech recognition model (~200MB)

### Command Line Options

| Option | Description |
|--------|-------------|
| `--toggle` | Toggle recording state (for system hotkey) |

### Non-Fcitx5 Environment

If Fcitx5 is not installed, the app automatically uses clipboard mode:
- Recognized text is copied to system clipboard
- UI shows "Copied to clipboard" prompt
- Manually paste (`Ctrl+V`) to target application

### System Tray

The app supports system tray (on supported desktop environments), right-click menu provides:

- Show/Hide window
- Switch model version
- Open config directory
- Exit app

> **Note**: It's normal that GNOME desktop doesn't show tray icon, the app can still be used via `nextalk --toggle` command.

## System Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Linux (Ubuntu 22.04+ recommended) |
| **Display Server** | X11 or Wayland |
| **Audio System** | ALSA or PulseAudio |
| **Input Method** | Fcitx5 |

## Configuration

### Model Settings

Switch via system tray menu:

| Version | Description |
|---------|-------------|
| `int8` | Quantized version, faster, smaller memory footprint (default) |
| `standard` | Standard version, higher recognition accuracy |

### Config File

Advanced configuration: `~/.config/nextalk/settings.yaml`

```yaml
model:
  custom_url: ""    # Custom model download URL
  type: int8        # Model version: int8 | standard

hotkey:
  key: v            # Main key (display only, actual key controlled by system shortcut)
  modifiers:        # Modifier keys
    - ctrl
    - alt
```

## Build from Source

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt install fcitx5 fcitx5-dev libportaudio2 portaudio19-dev cmake build-essential

# Install Flutter: https://flutter.dev/docs/get-started/install/linux
```

### Local Build

```bash
# Using Makefile (recommended)
make build

# Or build separately
make build-flutter    # Flutter client
make build-addon      # Fcitx5 plugin
```

### Docker Build (Cross-distro Compatible)

Recommended to use Docker build for cross-distribution compatibility:

```bash
# Incremental build (recommended)
make docker-build

# Full rebuild
make docker-rebuild

# Flutter only
make docker-build-flutter

# Plugin only
make docker-build-addon
```

### Install Plugin

```bash
make install-addon          # User-level installation
make install-addon-system   # System-level installation (requires sudo)
```

### Run

```bash
make run          # Development mode
make run-release  # Release version
```

### Build Packages

```bash
./scripts/build-pkg.sh --deb   # DEB package
./scripts/build-pkg.sh --rpm   # RPM package
./scripts/build-pkg.sh --all   # All formats
```

Output in `dist/` directory.

## Uninstall

**Ubuntu/Debian:**

```bash
sudo dpkg -r nextalk
```

**Fedora/CentOS/RHEL:**

```bash
sudo rpm -e nextalk
```

User data is preserved at `~/.local/share/nextalk/`, delete manually for complete cleanup.

## Project Structure

```
nextalk/
├── voice_capsule/        # Flutter client
│   └── lib/
│       ├── main.dart     # Entry point
│       ├── ffi/          # FFI bindings (sherpa, portaudio)
│       ├── services/     # Business logic
│       │   ├── asr/      # ASR engine abstraction
│       │   └── ...       # Other services
│       ├── ui/           # Widget components
│       └── l10n/         # Internationalization
├── addons/fcitx5/        # Fcitx5 C++ plugin
├── docs/                 # Design documents
├── scripts/              # Build scripts
├── libs/                 # Precompiled dynamic libraries
├── packaging/            # DEB/RPM templates
└── Makefile              # Build entry
```

Detailed architecture: [docs/architecture.md](docs/architecture.md)

## Development

```bash
make test       # Run tests
make analyze    # Code analysis
make clean      # Clean build
make help       # Show all commands
```

## FAQ

### System Tray Icon Not Showing (GNOME/Fedora)

GNOME desktop doesn't show system tray icons by default, this is normal. The app can still be used via command line:

```bash
nextalk --toggle  # Toggle recording state
```

> **⚠️ Note**: Installing AppIndicator extension is not recommended, may cause app crashes. If already installed and experiencing crashes, see next section.

### App Crashes on Startup (Segfault)

If app crashes after installing AppIndicator extension, disable tray functionality:

```bash
NEXTALK_NO_TRAY=1 nextalk
```

When configuring system shortcut:

```bash
env NEXTALK_NO_TRAY=1 /opt/nextalk/nextalk --toggle
```

### Hotkey Not Responding

1. Confirm hotkey is configured in system settings (command: `nextalk --toggle`)
2. Confirm Nextalk app is running (check system tray)
3. Test command line: `nextalk --toggle`

### Text Not Inputting to App

Ensure Fcitx5 plugin is correctly installed:

```bash
ls ~/.local/lib/fcitx5/libnextalk.so
ls ~/.local/share/fcitx5/addon/nextalk.conf
fcitx5 -r  # Restart Fcitx5
```

If not using Fcitx5, the app will automatically use clipboard mode.

### Model Download Failed

Configure custom download URL or use proxy:

```yaml
# ~/.config/nextalk/settings.yaml
model:
  custom_url: "https://your-mirror/model.tar.bz2"
```

### Audio Device Issues

```bash
nextalk audio --list  # List devices detected by the app
pactl list sources    # System-level debug command
```

## Contributing

Contributions, bug reports, and suggestions are welcome!

1. Fork this repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Create Pull Request

## Acknowledgments

- [Sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) - High-performance offline speech recognition engine
- [Fcitx5](https://github.com/fcitx/fcitx5) - Modern input method framework
- [Flutter](https://flutter.dev) - Cross-platform UI framework

## License

[MIT License](LICENSE)

---

**Issue Feedback**: [GitHub Issues](../../issues)
