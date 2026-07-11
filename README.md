# Nextalk

**High-performance offline voice input for Linux**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)]()
[![Wayland: Supported](https://img.shields.io/badge/Wayland-Supported-green.svg)]()

[简体中文](README_zh.md) | English

Convert speech to text in real-time, input to any application via the Fcitx5 input method framework. Runs completely offline to protect your privacy.

## Features

- **Offline Recognition** - Dual-engine ASR based on Sherpa-onnx: SenseVoice offline engine (default — high accuracy, multilingual, auto punctuation) and Zipformer streaming engine (optional — real-time, character by character); data never leaves your device
- **Low Latency** - Streaming engine transcribes as you speak; text commit path latency < 20ms
- **Transparent Floating Window** - Borderless capsule UI with breathing animation, minimal workflow disruption
- **Native Wayland Support** - System shortcuts and text submission both support Wayland
- **Bilingual UI** - Simplified Chinese / English interface, switchable from the tray menu
- **Engine & Model Options** - Hot-switch engines and Zipformer int8/standard variants from the tray menu

## Quick Start

### Installation

**Ubuntu/Debian:**

```bash
# Recommended: apt installs dependencies automatically
sudo apt install ./nextalk_0.2.13-1_amd64.deb
```

> If you install with `sudo dpkg -i`, dpkg does not resolve dependencies; run `sudo apt -f install` afterwards if it complains about missing ones.

**Fedora/CentOS/RHEL:**

```bash
# Recommended: dnf installs dependencies automatically
sudo dnf install ./nextalk-0.2.13-1.x86_64.rpm
```

**Runtime dependencies:**

| Dependency | Notes |
|------|------|
| `fcitx5` (≥ 5.0) | Required, text commit channel (declared by deb/rpm, installed automatically by the package manager) |
| `libgtk-3-0` / `gtk3` | Required (installed automatically by the package manager) |
| PulseAudio or PipeWire (`pipewire-pulse`) | Audio capture, shipped by default on mainstream distros |
| `xdg-desktop-portal` + your desktop's backend | Needed for shortcut auto-registration (bundled with GNOME 48+/KDE 5.27+, no manual install) |
| `libayatana-appindicator3-1` / `libayatana-appindicator-gtk3` | Tray runtime library (declared by deb/rpm since 0.2.13, installed automatically) |
| `gnome-shell-extension-appindicator` | **GNOME only**: extension required to show the tray icon; enable it and re-log after installing (see [FAQ](#system-tray-icon-not-showing-gnomefedora)); KDE supports the tray natively |

Fcitx5 will automatically restart after installation to load the plugin.

### Configure Hotkey

**Works out of the box (supported environments):** On KDE Plasma 5.27+, GNOME 48+, and Hyprland, the app auto-registers a global shortcut (default `Super+Z`) via XDG Desktop Portal on first launch. The system shows a one-time authorization dialog — confirm it and the shortcut takes effect immediately, no manual setup required.

**Fallback (manual configuration):** On environments without Portal GlobalShortcuts support (GNOME <48, wlroots/Sway, and the default sessions of Ubuntu 22.04/24.04), the app silently falls back to the system shortcut. Configure it manually and bind the `nextalk-toggle` command:

**GNOME:**

1. Settings → Keyboard → View and Customize Shortcuts → Custom Shortcuts
2. Click "Add Shortcut"
3. Name: `Nextalk Voice Input`
4. Command: `nextalk-toggle`
5. Shortcut: Press `Super+Z` (recommended; do NOT use `Alt+Space` — GNOME's window-menu key already occupies it)

**KDE Plasma:**

1. System Settings → Shortcuts → Custom Shortcuts
2. Edit → New → Global Shortcut → Command/URL
3. Trigger: Set to `Super+Z`
4. Action: `nextalk-toggle`

> The current hotkey mode (Portal / system) is shown as a read-only item in the tray menu.

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
| `audio` | Manage audio input device (interactive mode) |
| `audio <number>` | Set audio device by index number directly |
| `audio --list` | List available devices (machine-readable) |
| `audio default` | Reset to system default device |
| `--help` | Show help information |
| `--version` | Show version |

### Non-Fcitx5 Environment

If Fcitx5 is not installed, the app automatically uses clipboard mode:
- Recognized text is copied to system clipboard
- UI shows "Copied to clipboard" prompt
- Manually paste (`Ctrl+V`) to target application

### System Tray

The app supports system tray (on supported desktop environments), right-click menu provides:

- Show/Hide window
- **Reconnect Fcitx5** - manually reconnect when the input-method channel drops
- **Hotkey mode (read-only)** - shows the active hotkey path: `Hotkey: Super+Z (Portal auto-registered)` or `Hotkey: System settings (nextalk-toggle)`
- Model settings - switch ASR engine (SenseVoice / Zipformer) and Zipformer model version (int8 / standard)
- Switch UI language (中文 / English)
- **Audio input device** - Select from available audio input devices
- Settings - open the config directory
- Exit app

> **Note**: On GNOME the tray icon only shows after installing and enabling the `gnome-shell-extension-appindicator` extension (KDE supports it natively) — see the [FAQ](#system-tray-icon-not-showing-gnomefedora). Without a tray the app still works via the `nextalk --toggle` command.

## System Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Linux (Ubuntu 22.04+ recommended) |
| **Display Server** | X11 or Wayland |
| **Audio System** | PulseAudio or PipeWire (`pipewire-pulse`) |
| **Input Method** | Fcitx5 |

## Configuration

### Engine & Model Settings

Switch via system tray menu:

| Engine | Description |
|--------|-------------|
| `sensevoice` (default) | Offline engine: recognizes per VAD segment, higher accuracy, auto punctuation, multilingual (zh/en/ja/ko/yue) |
| `zipformer` | Streaming engine: recognize-while-listening, text appears character by character |

Zipformer variants: `int8` (faster, smaller memory) / `standard` (higher accuracy).

### Config File

Advanced configuration: `~/.config/nextalk/settings.yaml`

```yaml
model:
  # ASR engine: zipformer | sensevoice
  engine: sensevoice

  zipformer:
    type: int8        # Model variant: int8 | standard
    custom_url: ""    # Custom model download URL (empty = default)

  sensevoice:
    use_itn: true     # Inverse text normalization
    language: auto    # auto | zh | en | ja | ko | yue
    custom_url: ""

audio:
  input_device: "default"  # Audio input device: "default" or device name
```

**Audio Device Selection:**
- Use `"default"` to use system default audio device
- Specify device name (e.g. `"Built-in Audio Analog Stereo"`) to use a specific device
- Use `nextalk audio` command or system tray menu to select devices interactively

**Hotkey Configuration:**
On supported environments the hotkey is auto-registered via XDG Desktop Portal (no config needed); otherwise it is configured through your desktop environment's native settings, not through this config file. See [Configure Hotkey](#configure-hotkey) section for details.

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

> 📦 For the full maintainer release flow, CI/CD automation, and version management, see the [Build and Release Guide](docs/build-and-release.md).

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

GNOME desktop doesn't show AppIndicator tray icons by default; install and enable the `gnome-shell-extension-appindicator` extension:

```bash
# Debian/Ubuntu
sudo apt install gnome-shell-extension-appindicator

# Fedora
sudo dnf install gnome-shell-extension-appindicator
```

**Log out and back in** after installing (a Wayland session must be re-logged to load the extension), then make sure it is enabled:

```bash
gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com
```

Restart Nextalk and the tray icon appears. KDE Plasma supports the tray natively with no configuration.

Without the extension the tray is invisible, but the app still works fully via the command line:

```bash
nextalk --toggle  # Toggle recording state
```

### App Crashes on Startup (Segfault)

0.2.13 fixes the startup segfault on Fedora caused by the legacy `libappindicator` library (the tray plugin now prefers the ayatana implementation). If you still hit a tray-related crash, temporarily disable the tray to isolate it:

```bash
NEXTALK_NO_TRAY=1 nextalk
```

When configuring system shortcut (fallback mode):

```bash
nextalk-toggle
```

### Hotkey Not Responding

1. Confirm hotkey is configured in system settings (command: `nextalk-toggle`)
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
  zipformer:
    custom_url: "https://your-mirror/zipformer-model.tar.bz2"
  sensevoice:
    custom_url: "https://your-mirror/sensevoice-model.tar.bz2"
```

### Audio Device Issues

If you encounter "Audio device busy" error (e.g., when using EasyEffects), you can select a different audio input device:

**Method 1: CLI Interactive Mode**
```bash
nextalk audio       # Enter interactive mode to select device
```

**Method 2: CLI Direct Selection**
```bash
nextalk audio --list  # List available devices
nextalk audio 2       # Select device by index
nextalk audio default # Reset to system default
```

**Method 3: System Tray**
Right-click tray icon → Audio Input Device → Select from available devices

**Debug Commands:**
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
