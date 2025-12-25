/*
 * SPDX-FileCopyrightText: 2024 Nextalk Project
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#include "nextalk.h"
#include <fcitx-utils/log.h>
#include <fcitx-utils/key.h>
#include <fcitx/inputcontext.h>
#include <fcitx/inputcontextmanager.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
#include <vector>
#include <sstream>
#include <algorithm>

// Maximum message size (1MB)
constexpr size_t MAX_MESSAGE_SIZE = 1024 * 1024;

namespace fcitx {

FCITX_DEFINE_LOG_CATEGORY(nextalk_log, "nextalk");

#define NEXTALK_DEBUG() FCITX_LOGC(nextalk_log, Debug)
#define NEXTALK_INFO() FCITX_LOGC(nextalk_log, Info)
#define NEXTALK_WARN() FCITX_LOGC(nextalk_log, Warn)
#define NEXTALK_ERROR() FCITX_LOGC(nextalk_log, Error)

NextalkAddon::NextalkAddon(Instance *instance) : instance_(instance) {
    NEXTALK_INFO() << "Nextalk addon initializing...";

    // 初始化按键映射表
    initKeyMap();

    // 附加 dispatcher 到主事件循环
    dispatcher_.attach(&instance_->eventLoop());

    // 设置快捷键事件监听
    setupKeyEventHandler();

    // 启动文本接收 Socket
    startSocketListener();

    // 启动配置接收 Socket
    startConfigListener();

    NEXTALK_INFO() << "Nextalk addon initialized";
    NEXTALK_INFO() << "Text socket: " << getSocketPath();
    NEXTALK_INFO() << "Config socket: " << getConfigSocketPath();
    NEXTALK_INFO() << "Command socket (to Flutter): " << getCommandSocketPath();
    NEXTALK_INFO() << "Default hotkey: Alt_R";
}

NextalkAddon::~NextalkAddon() {
    NEXTALK_INFO() << "Nextalk addon shutting down...";
    eventHandlers_.clear();
    stopSocketListener();
    stopConfigListener();
    dispatcher_.detach();
}

// ===== 按键映射初始化 =====

void NextalkAddon::initKeyMap() {
    // 修饰键
    keyNameMap_["Alt_L"] = FcitxKey_Alt_L;
    keyNameMap_["Alt_R"] = FcitxKey_Alt_R;
    keyNameMap_["altLeft"] = FcitxKey_Alt_L;
    keyNameMap_["altRight"] = FcitxKey_Alt_R;
    keyNameMap_["Control_L"] = FcitxKey_Control_L;
    keyNameMap_["Control_R"] = FcitxKey_Control_R;
    keyNameMap_["ctrlLeft"] = FcitxKey_Control_L;
    keyNameMap_["ctrlRight"] = FcitxKey_Control_R;
    keyNameMap_["Shift_L"] = FcitxKey_Shift_L;
    keyNameMap_["Shift_R"] = FcitxKey_Shift_R;
    keyNameMap_["shiftLeft"] = FcitxKey_Shift_L;
    keyNameMap_["shiftRight"] = FcitxKey_Shift_R;
    keyNameMap_["Super_L"] = FcitxKey_Super_L;
    keyNameMap_["Super_R"] = FcitxKey_Super_R;
    keyNameMap_["Meta_L"] = FcitxKey_Meta_L;
    keyNameMap_["Meta_R"] = FcitxKey_Meta_R;

    // 功能键 F1-F12
    keyNameMap_["F1"] = FcitxKey_F1;
    keyNameMap_["F2"] = FcitxKey_F2;
    keyNameMap_["F3"] = FcitxKey_F3;
    keyNameMap_["F4"] = FcitxKey_F4;
    keyNameMap_["F5"] = FcitxKey_F5;
    keyNameMap_["F6"] = FcitxKey_F6;
    keyNameMap_["F7"] = FcitxKey_F7;
    keyNameMap_["F8"] = FcitxKey_F8;
    keyNameMap_["F9"] = FcitxKey_F9;
    keyNameMap_["F10"] = FcitxKey_F10;
    keyNameMap_["F11"] = FcitxKey_F11;
    keyNameMap_["F12"] = FcitxKey_F12;

    // 常用键
    keyNameMap_["space"] = FcitxKey_space;
    keyNameMap_["Space"] = FcitxKey_space;
    keyNameMap_["Escape"] = FcitxKey_Escape;
    keyNameMap_["Tab"] = FcitxKey_Tab;
    keyNameMap_["Return"] = FcitxKey_Return;
    keyNameMap_["Enter"] = FcitxKey_Return;
    keyNameMap_["BackSpace"] = FcitxKey_BackSpace;
    keyNameMap_["Caps_Lock"] = FcitxKey_Caps_Lock;

    // 方向键
    keyNameMap_["Up"] = FcitxKey_Up;
    keyNameMap_["Down"] = FcitxKey_Down;
    keyNameMap_["Left"] = FcitxKey_Left;
    keyNameMap_["Right"] = FcitxKey_Right;

    // 编辑键
    keyNameMap_["Insert"] = FcitxKey_Insert;
    keyNameMap_["Delete"] = FcitxKey_Delete;
    keyNameMap_["Home"] = FcitxKey_Home;
    keyNameMap_["End"] = FcitxKey_End;
    keyNameMap_["Page_Up"] = FcitxKey_Page_Up;
    keyNameMap_["Page_Down"] = FcitxKey_Page_Down;

    // 字母键 a-z
    keyNameMap_["a"] = FcitxKey_a;
    keyNameMap_["b"] = FcitxKey_b;
    keyNameMap_["c"] = FcitxKey_c;
    keyNameMap_["d"] = FcitxKey_d;
    keyNameMap_["e"] = FcitxKey_e;
    keyNameMap_["f"] = FcitxKey_f;
    keyNameMap_["g"] = FcitxKey_g;
    keyNameMap_["h"] = FcitxKey_h;
    keyNameMap_["i"] = FcitxKey_i;
    keyNameMap_["j"] = FcitxKey_j;
    keyNameMap_["k"] = FcitxKey_k;
    keyNameMap_["l"] = FcitxKey_l;
    keyNameMap_["m"] = FcitxKey_m;
    keyNameMap_["n"] = FcitxKey_n;
    keyNameMap_["o"] = FcitxKey_o;
    keyNameMap_["p"] = FcitxKey_p;
    keyNameMap_["q"] = FcitxKey_q;
    keyNameMap_["r"] = FcitxKey_r;
    keyNameMap_["s"] = FcitxKey_s;
    keyNameMap_["t"] = FcitxKey_t;
    keyNameMap_["u"] = FcitxKey_u;
    keyNameMap_["v"] = FcitxKey_v;
    keyNameMap_["w"] = FcitxKey_w;
    keyNameMap_["x"] = FcitxKey_x;
    keyNameMap_["y"] = FcitxKey_y;
    keyNameMap_["z"] = FcitxKey_z;

    // 数字键 0-9
    keyNameMap_["0"] = FcitxKey_0;
    keyNameMap_["1"] = FcitxKey_1;
    keyNameMap_["2"] = FcitxKey_2;
    keyNameMap_["3"] = FcitxKey_3;
    keyNameMap_["4"] = FcitxKey_4;
    keyNameMap_["5"] = FcitxKey_5;
    keyNameMap_["6"] = FcitxKey_6;
    keyNameMap_["7"] = FcitxKey_7;
    keyNameMap_["8"] = FcitxKey_8;
    keyNameMap_["9"] = FcitxKey_9;

    NEXTALK_DEBUG() << "Key map initialized with " << keyNameMap_.size() << " keys";
}

std::string NextalkAddon::getSocketPath() const {
    const char *runtimeDir = getenv("XDG_RUNTIME_DIR");
    if (runtimeDir) {
        return std::string(runtimeDir) + "/nextalk-fcitx5.sock";
    }
    return "/tmp/nextalk-fcitx5.sock";
}

std::string NextalkAddon::getCommandSocketPath() const {
    // 用于向 Flutter 发送命令 (toggle 等)
    const char *runtimeDir = getenv("XDG_RUNTIME_DIR");
    if (runtimeDir) {
        return std::string(runtimeDir) + "/nextalk-cmd.sock";
    }
    return "/tmp/nextalk-cmd.sock";
}

std::string NextalkAddon::getConfigSocketPath() const {
    // 用于接收 Flutter 发送的配置命令 (hotkey 等)
    const char *runtimeDir = getenv("XDG_RUNTIME_DIR");
    if (runtimeDir) {
        return std::string(runtimeDir) + "/nextalk-fcitx5-cfg.sock";
    }
    return "/tmp/nextalk-fcitx5-cfg.sock";
}

// ===== 快捷键监听实现 =====

void NextalkAddon::setupKeyEventHandler() {
    NEXTALK_INFO() << "Setting up key event handler (configurable hotkey)";

    // 监听键盘事件 (PreInputMethod 阶段，优先于输入法处理)
    eventHandlers_.emplace_back(instance_->watchEvent(
        EventType::InputContextKeyEvent,
        EventWatcherPhase::PreInputMethod,
        [this](Event &event) {
            auto &keyEvent = static_cast<KeyEvent &>(event);
            handleKeyEvent(keyEvent);
        }
    ));

    NEXTALK_INFO() << "Key event handler registered (PreInputMethod phase)";
}

bool NextalkAddon::isConfiguredHotkey(const Key &key) const {
    // 检查主键是否匹配
    if (key.sym() != configuredKey_) {
        // 特殊处理: Alt_R 有时会被映射为 ISO_Level3_Shift
        if (configuredKey_ == FcitxKey_Alt_R &&
            key.sym() == FcitxKey_ISO_Level3_Shift) {
            return true;
        }
        return false;
    }

    // 如果配置了修饰键，检查修饰键是否匹配
    // 注意：对于单键（如 Alt_R），不检查修饰键状态
    // 因为 Alt_R 本身就是修饰键，按下时修饰键状态可能不一致
    if (configuredModifiers_ != KeyStates{}) {
        // 获取当前按键的修饰键状态（排除自身）
        KeyStates currentModifiers = key.states();
        // 简化检查：只要配置的修饰键都被按下即可
        if ((currentModifiers & configuredModifiers_) != configuredModifiers_) {
            return false;
        }
    }

    return true;
}

void NextalkAddon::handleKeyEvent(KeyEvent &keyEvent) {
    const Key &key = keyEvent.key();

    // 检测是否是配置的快捷键
    if (!isConfiguredHotkey(key)) {
        return;
    }

    if (keyEvent.isRelease()) {
        // 快捷键释放
        hotkeyPressed_ = false;
    } else {
        // 快捷键按下 - 立即响应
        if (!hotkeyPressed_) {
            hotkeyPressed_ = true;

            // ===== 焦点锁定：保存当前 InputContext =====
            InputContext *currentIc = keyEvent.inputContext();
            InputContext *mostRecentIc = instance_->mostRecentInputContext();

            NEXTALK_INFO() << "keyEvent.inputContext(): "
                           << (currentIc ? currentIc->program() : "null")
                           << " hasFocus=" << (currentIc ? currentIc->hasFocus() : false);
            NEXTALK_INFO() << "mostRecentInputContext(): "
                           << (mostRecentIc ? mostRecentIc->program() : "null")
                           << " hasFocus=" << (mostRecentIc ? mostRecentIc->hasFocus() : false);

            if (currentIc) {
                lockedInputContextUUID_ = currentIc->uuid();
                hasLockedContext_ = true;
                NEXTALK_INFO() << "Hotkey pressed, locked InputContext: " << currentIc->program();
            } else {
                hasLockedContext_ = false;
                NEXTALK_INFO() << "Hotkey pressed, no InputContext to lock";
            }

            // 发送切换命令到 Flutter
            sendCommandToFlutter("toggle");
        }
    }
}

// ===== 快捷键配置解析 =====

bool NextalkAddon::parseHotkeyConfig(const std::string &config) {
    // 解析格式: "Key" 或 "Modifier+Modifier+Key"
    // 例如: "Alt_R", "Control+Shift+Space", "F12"

    std::vector<std::string> parts;
    std::stringstream ss(config);
    std::string part;
    while (std::getline(ss, part, '+')) {
        // 去除首尾空格
        part.erase(0, part.find_first_not_of(" \t"));
        part.erase(part.find_last_not_of(" \t") + 1);
        if (!part.empty()) {
            parts.push_back(part);
        }
    }

    if (parts.empty()) {
        NEXTALK_WARN() << "Empty hotkey config";
        return false;
    }

    // 最后一个是主键，前面的是修饰键
    std::string mainKey = parts.back();
    parts.pop_back();

    // 查找主键
    auto it = keyNameMap_.find(mainKey);
    if (it == keyNameMap_.end()) {
        NEXTALK_WARN() << "Unknown key: " << mainKey;
        return false;
    }

    KeySym newKey = it->second;
    KeyStates newModifiers{};

    // 解析修饰键
    for (const auto &mod : parts) {
        if (mod == "Control" || mod == "Ctrl") {
            newModifiers |= KeyState::Ctrl;
        } else if (mod == "Shift") {
            newModifiers |= KeyState::Shift;
        } else if (mod == "Alt") {
            newModifiers |= KeyState::Alt;
        } else if (mod == "Super" || mod == "Meta") {
            newModifiers |= KeyState::Super;
        } else {
            NEXTALK_WARN() << "Unknown modifier: " << mod;
            return false;
        }
    }

    // 更新配置
    configuredKey_ = newKey;
    configuredModifiers_ = newModifiers;

    NEXTALK_INFO() << "Hotkey configured: " << config;
    return true;
}

void NextalkAddon::processCommand(const std::string &command) {
    // 解析命令格式: "config:hotkey:<key_spec>"
    const std::string prefix = "config:hotkey:";
    if (command.compare(0, prefix.size(), prefix) == 0) {
        std::string keySpec = command.substr(prefix.size());
        if (parseHotkeyConfig(keySpec)) {
            NEXTALK_INFO() << "Hotkey updated to: " << keySpec;
        }
    } else {
        NEXTALK_DEBUG() << "Unknown command: " << command;
    }
}

void NextalkAddon::sendCommandToFlutter(const std::string &command) {
    std::string socketPath = getCommandSocketPath();

    int sockFd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sockFd < 0) {
        NEXTALK_ERROR() << "Failed to create command socket: " << strerror(errno);
        return;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, socketPath.c_str(), sizeof(addr.sun_path) - 1);

    // 设置连接超时 (非阻塞 + select)
    struct timeval timeout;
    timeout.tv_sec = 1;
    timeout.tv_usec = 0;
    setsockopt(sockFd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));

    if (connect(sockFd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        if (errno != ENOENT && errno != ECONNREFUSED) {
            NEXTALK_WARN() << "Failed to connect to Flutter: " << strerror(errno);
        }
        // Flutter 应用可能未运行，静默失败
        close(sockFd);
        return;
    }

    // 发送命令 (协议: 4字节长度 + UTF-8文本)
    uint32_t len = static_cast<uint32_t>(command.size());
    if (send(sockFd, &len, sizeof(len), 0) != sizeof(len)) {
        NEXTALK_WARN() << "Failed to send command length";
        close(sockFd);
        return;
    }

    if (send(sockFd, command.c_str(), len, 0) != static_cast<ssize_t>(len)) {
        NEXTALK_WARN() << "Failed to send command data";
        close(sockFd);
        return;
    }

    NEXTALK_INFO() << "Command sent to Flutter: " << command;
    close(sockFd);
}

void NextalkAddon::startSocketListener() {
    running_ = true;
    listenerThread_ = std::thread(&NextalkAddon::socketListenerLoop, this);
}

void NextalkAddon::stopSocketListener() {
    running_ = false;

    // 关闭服务器 socket 以中断 accept()
    if (serverFd_ >= 0) {
        shutdown(serverFd_, SHUT_RDWR);
        close(serverFd_);
        serverFd_ = -1;
    }

    if (listenerThread_.joinable()) {
        listenerThread_.join();
    }

    // 删除 socket 文件
    unlink(getSocketPath().c_str());
}

void NextalkAddon::socketListenerLoop() {
    std::string socketPath = getSocketPath();

    // 删除旧的 socket 文件
    unlink(socketPath.c_str());

    // 创建 Unix Domain Socket
    serverFd_ = socket(AF_UNIX, SOCK_STREAM, 0);
    if (serverFd_ < 0) {
        NEXTALK_ERROR() << "Failed to create socket: " << strerror(errno);
        return;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, socketPath.c_str(), sizeof(addr.sun_path) - 1);

    if (bind(serverFd_, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        NEXTALK_ERROR() << "Failed to bind socket: " << strerror(errno);
        close(serverFd_);
        serverFd_ = -1;
        return;
    }

    // Set socket file permissions to 0600 (owner read/write only) for security
    // Prevents other users from injecting malicious text
    if (chmod(socketPath.c_str(), 0600) < 0) {
        NEXTALK_WARN() << "Failed to set socket permissions: " << strerror(errno);
        // Continue anyway, but log the warning
    }

    if (listen(serverFd_, 5) < 0) {
        NEXTALK_ERROR() << "Failed to listen on socket: " << strerror(errno);
        close(serverFd_);
        serverFd_ = -1;
        return;
    }

    NEXTALK_INFO() << "Socket listening at: " << socketPath;

    while (running_) {
        int clientFd = accept(serverFd_, nullptr, nullptr);
        if (clientFd < 0) {
            if (running_) {
                NEXTALK_ERROR() << "Failed to accept connection: " << strerror(errno);
            }
            continue;
        }

        NEXTALK_DEBUG() << "Client connected";
        handleClient(clientFd);
        close(clientFd);
        NEXTALK_DEBUG() << "Client disconnected";
    }
}

void NextalkAddon::handleClient(int clientFd) {
    // 设置 recv 超时 (30秒)，防止客户端异常断开时永久阻塞
    struct timeval timeout;
    timeout.tv_sec = 30;
    timeout.tv_usec = 0;
    if (setsockopt(clientFd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) < 0) {
        NEXTALK_WARN() << "Failed to set socket timeout: " << strerror(errno);
    }

    // 协议：4字节长度（小端）+ UTF-8文本
    while (running_) {
        // 读取长度 (with EINTR retry and timeout handling)
        uint32_t len = 0;
        ssize_t n;
        do {
            n = recv(clientFd, &len, sizeof(len), MSG_WAITALL);
        } while (n < 0 && errno == EINTR);

        // 处理超时：检查连接是否还活着
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            // 超时但连接可能还在，发送空检测
            char probe = 0;
            ssize_t probeResult = send(clientFd, &probe, 0, MSG_NOSIGNAL);
            if (probeResult < 0 && errno != EAGAIN) {
                NEXTALK_DEBUG() << "Client connection lost (timeout probe failed)";
                break;
            }
            // 连接还在，继续等待
            continue;
        }

        if (n <= 0) {
            if (n == 0) {
                NEXTALK_DEBUG() << "Client closed connection gracefully";
            } else {
                NEXTALK_DEBUG() << "Client connection error: " << strerror(errno);
            }
            break;
        }

        // 限制最大长度
        if (len > MAX_MESSAGE_SIZE) {
            NEXTALK_WARN() << "Message too large: " << len;
            break;
        }

        // 读取文本 (with EINTR retry)
        std::vector<char> buffer(len);
        do {
            n = recv(clientFd, buffer.data(), len, MSG_WAITALL);
        } while (n < 0 && errno == EINTR);
        
        if (n != static_cast<ssize_t>(len)) {
            NEXTALK_WARN() << "Incomplete message";
            break;
        }

        std::string text(buffer.data(), len);
        NEXTALK_INFO() << "Received text: " << text;

        // 提交文本（需要在主线程执行）
        dispatcher_.schedule([this, text]() {
            commitText(text);
        });

        // 发送确认
        uint8_t ack = 1;
        send(clientFd, &ack, 1, 0);
    }
}

void NextalkAddon::commitText(const std::string &text) {
    if (text.empty()) {
        NEXTALK_DEBUG() << "Skipping empty text";
        return;
    }

    InputContext *ic = nullptr;

    // ===== 焦点锁定：优先使用锁定的 InputContext =====
    // 这解决了 Wayland 下用户在录音过程中切换窗口导致文字提交到错误应用的问题
    if (hasLockedContext_) {
        auto &icManager = instance_->inputContextManager();
        ic = icManager.findByUUID(lockedInputContextUUID_);
        if (ic) {
            NEXTALK_INFO() << "Using locked InputContext: " << ic->program()
                           << " hasFocus=" << ic->hasFocus();
        } else {
            NEXTALK_INFO() << "Locked InputContext no longer exists, falling back";
        }
        // 提交后清除锁定状态
        hasLockedContext_ = false;
    }

    // 如果没有锁定的 InputContext，使用 mostRecentInputContext
    if (!ic) {
        ic = instance_->mostRecentInputContext();
    }

    if (!ic) {
        // 尝试遍历所有输入上下文，找到任何可用的
        auto &icManager = instance_->inputContextManager();
        icManager.foreach([&ic](InputContext *ctx) {
            if (ctx && ctx->hasFocus()) {
                ic = ctx;
                return false; // 找到了，停止遍历
            }
            return true; // 继续遍历
        });
    }

    if (!ic) {
        // 仍然没有，尝试获取任意一个输入上下文
        auto &icManager = instance_->inputContextManager();
        icManager.foreach([&ic](InputContext *ctx) {
            if (ctx) {
                ic = ctx;
                return false;
            }
            return true;
        });

        if (ic) {
            NEXTALK_INFO() << "Using fallback input context (no focus)";
        }
    }

    if (!ic) {
        NEXTALK_WARN() << "No active input context available, text not committed: " << text;
        return;
    }

    // 提交文本
    ic->commitString(text);
    NEXTALK_INFO() << "Committed text to: " << ic->program()
                   << " hasFocus=" << ic->hasFocus()
                   << " text=" << text;
}

// ===== 配置 Socket 服务器 (接收 Flutter 发送的配置) =====

void NextalkAddon::startConfigListener() {
    configRunning_ = true;
    configListenerThread_ = std::thread(&NextalkAddon::configListenerLoop, this);
}

void NextalkAddon::stopConfigListener() {
    configRunning_ = false;

    if (configServerFd_ >= 0) {
        shutdown(configServerFd_, SHUT_RDWR);
        close(configServerFd_);
        configServerFd_ = -1;
    }

    if (configListenerThread_.joinable()) {
        configListenerThread_.join();
    }

    unlink(getConfigSocketPath().c_str());
}

void NextalkAddon::configListenerLoop() {
    std::string socketPath = getConfigSocketPath();

    // 删除旧的 socket 文件
    unlink(socketPath.c_str());

    // 创建 Unix Domain Socket
    configServerFd_ = socket(AF_UNIX, SOCK_STREAM, 0);
    if (configServerFd_ < 0) {
        NEXTALK_ERROR() << "Failed to create config socket: " << strerror(errno);
        return;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, socketPath.c_str(), sizeof(addr.sun_path) - 1);

    if (bind(configServerFd_, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        NEXTALK_ERROR() << "Failed to bind config socket: " << strerror(errno);
        close(configServerFd_);
        configServerFd_ = -1;
        return;
    }

    if (chmod(socketPath.c_str(), 0600) < 0) {
        NEXTALK_WARN() << "Failed to set config socket permissions: " << strerror(errno);
    }

    if (listen(configServerFd_, 5) < 0) {
        NEXTALK_ERROR() << "Failed to listen on config socket: " << strerror(errno);
        close(configServerFd_);
        configServerFd_ = -1;
        return;
    }

    NEXTALK_INFO() << "Config socket listening at: " << socketPath;

    while (configRunning_) {
        int clientFd = accept(configServerFd_, nullptr, nullptr);
        if (clientFd < 0) {
            if (configRunning_) {
                NEXTALK_ERROR() << "Failed to accept config connection: " << strerror(errno);
            }
            continue;
        }

        handleConfigClient(clientFd);
        close(clientFd);
    }
}

void NextalkAddon::handleConfigClient(int clientFd) {
    // 设置超时
    struct timeval timeout;
    timeout.tv_sec = 5;
    timeout.tv_usec = 0;
    setsockopt(clientFd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

    // 协议：4字节长度（小端）+ UTF-8命令
    uint32_t len = 0;
    ssize_t n = recv(clientFd, &len, sizeof(len), MSG_WAITALL);
    if (n != sizeof(len)) {
        return;
    }

    if (len > 1024) {  // 命令不应该太长
        NEXTALK_WARN() << "Config command too long: " << len;
        return;
    }

    std::vector<char> buffer(len);
    n = recv(clientFd, buffer.data(), len, MSG_WAITALL);
    if (n != static_cast<ssize_t>(len)) {
        return;
    }

    std::string command(buffer.data(), len);
    NEXTALK_INFO() << "Received config command: " << command;

    // 处理命令（需要在主线程执行）
    dispatcher_.schedule([this, command]() {
        processCommand(command);
    });

    // 发送确认
    uint8_t ack = 1;
    send(clientFd, &ack, 1, 0);
}

} // namespace fcitx

FCITX_ADDON_FACTORY(fcitx::NextalkAddonFactory);
