/*
 * SPDX-FileCopyrightText: 2024 Nextalk Project
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * SCP-002 极简架构：
 * - 只保留文本接收和上屏功能
 * - 快捷键由系统原生快捷键 + --toggle 参数处理
 * - 唯一的按键监听是录音期间的 Esc 取消 (其余时间 Esc 原样放行)
 */

#include "nextalk.h"
#include <fcitx-utils/log.h>
#include <fcitx/inputcontext.h>
#include <fcitx/inputcontextmanager.h>
#include <fcitx/inputpanel.h>
#include <fcitx/text.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
#include <fstream>
#include <vector>

// Maximum message size (1MB)
constexpr size_t MAX_MESSAGE_SIZE = 1024 * 1024;

namespace fcitx {

FCITX_DEFINE_LOG_CATEGORY(nextalk_log, "nextalk");

#define NEXTALK_DEBUG() FCITX_LOGC(nextalk_log, Debug)
#define NEXTALK_INFO() FCITX_LOGC(nextalk_log, Info)
#define NEXTALK_WARN() FCITX_LOGC(nextalk_log, Warn)
#define NEXTALK_ERROR() FCITX_LOGC(nextalk_log, Error)

NextalkAddon::NextalkAddon(Instance *instance) : instance_(instance) {
    NEXTALK_INFO() << "Nextalk addon initializing (SCP-002 simplified)...";

    // 附加 dispatcher 到主事件循环
    dispatcher_.attach(&instance_->eventLoop());

    // 启动文本接收 Socket
    startSocketListener();

    // 录音期间的 Esc 取消：PreInputMethod 阶段早于输入法引擎，
    // 保证即使处于拼音组词中也由我们先处理
    keyEventWatcher_ = instance_->watchEvent(
        EventType::InputContextKeyEvent, EventWatcherPhase::PreInputMethod,
        [this](Event &event) {
            handleKeyEvent(static_cast<KeyEvent &>(event));
        });

    NEXTALK_INFO() << "Nextalk addon initialized";
    NEXTALK_INFO() << "Text socket: " << getSocketPath();
}

NextalkAddon::~NextalkAddon() {
    NEXTALK_INFO() << "Nextalk addon shutting down...";
    keyEventWatcher_.reset();
    stopSocketListener();
    dispatcher_.detach();
}

std::string NextalkAddon::getSocketPath() const {
    const char *runtimeDir = getenv("XDG_RUNTIME_DIR");
    if (runtimeDir) {
        return std::string(runtimeDir) + "/nextalk-fcitx5.sock";
    }
    return "/tmp/nextalk-fcitx5.sock";
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
    if (chmod(socketPath.c_str(), 0600) < 0) {
        NEXTALK_WARN() << "Failed to set socket permissions: " << strerror(errno);
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
    // 设置 recv 超时 (30秒)
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

        // 处理超时
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            char probe = 0;
            ssize_t probeResult = send(clientFd, &probe, 0, MSG_NOSIGNAL);
            if (probeResult < 0 && errno != EAGAIN) {
                NEXTALK_DEBUG() << "Client connection lost (timeout probe failed)";
                break;
            }
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

static std::string runtimePath(const char *name) {
    const char *runtimeDir = getenv("XDG_RUNTIME_DIR");
    if (runtimeDir && *runtimeDir) {
        return std::string(runtimeDir) + "/" + name;
    }
    return std::string("/tmp/") + name;
}

void NextalkAddon::handleKeyEvent(KeyEvent &keyEvent) {
    // 只处理不带修饰键的 Esc，其余按键零开销放行
    if (!keyEvent.key().check(FcitxKey_Escape)) {
        return;
    }

    if (keyEvent.isRelease()) {
        if (swallowEscRelease_) {
            swallowEscRelease_ = false;
            keyEvent.filterAndAccept();
        }
        return;
    }

    if (!isRecordingActive()) {
        return;
    }

    keyEvent.filterAndAccept();
    swallowEscRelease_ = true;
    NEXTALK_INFO() << "Esc pressed while recording, sending cancel";
    sendCancelCommand();
}

bool NextalkAddon::isRecordingActive() const {
    // Nextalk 录音期间写入该文件 (内容为其 PID)，结束时删除。
    // 校验 PID 存活，防止应用崩溃残留的文件永久吞掉 Esc。
    std::ifstream marker(runtimePath("nextalk-recording"));
    if (!marker) {
        return false;
    }
    long pid = 0;
    if (!(marker >> pid) || pid <= 0) {
        return false;
    }
    return kill(static_cast<pid_t>(pid), 0) == 0 || errno == EPERM;
}

void NextalkAddon::sendCancelCommand() const {
    // 非阻塞发送：运行在 Fcitx5 主线程，绝不能因应用无响应而卡住输入法
    int fd = socket(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
    if (fd < 0) {
        NEXTALK_WARN() << "Failed to create cancel socket: " << strerror(errno);
        return;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    std::string path = runtimePath("nextalk.sock");
    strncpy(addr.sun_path, path.c_str(), sizeof(addr.sun_path) - 1);

    if (connect(fd, reinterpret_cast<struct sockaddr *>(&addr), sizeof(addr)) < 0) {
        NEXTALK_WARN() << "Failed to connect to Nextalk: " << strerror(errno);
        close(fd);
        return;
    }

    // 与 single_instance.dart 相同的协议：4 字节小端长度 + UTF-8 命令
    static const char command[] = "cancel";
    constexpr uint32_t len = sizeof(command) - 1;
    unsigned char message[4 + len];
    message[0] = len & 0xff;
    message[1] = (len >> 8) & 0xff;
    message[2] = (len >> 16) & 0xff;
    message[3] = (len >> 24) & 0xff;
    memcpy(message + 4, command, len);

    ssize_t sent = send(fd, message, sizeof(message), MSG_NOSIGNAL | MSG_DONTWAIT);
    if (sent != static_cast<ssize_t>(sizeof(message))) {
        NEXTALK_WARN() << "Failed to send cancel command: " << strerror(errno);
    }
    close(fd);
}

void NextalkAddon::commitText(const std::string &text) {
    if (text.empty()) {
        NEXTALK_DEBUG() << "Skipping empty text";
        return;
    }

    InputContext *ic = instance_->mostRecentInputContext();

    if (!ic) {
        // 尝试遍历所有输入上下文，找到任何可用的
        auto &icManager = instance_->inputContextManager();
        icManager.foreach([&ic](InputContext *ctx) {
            if (ctx && ctx->hasFocus()) {
                ic = ctx;
                return false;
            }
            return true;
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

    // 模拟完整 IME 周期
    // Step 1: 设置 preedit
    ic->inputPanel().setClientPreedit(Text(text));
    ic->updatePreedit();
    NEXTALK_DEBUG() << "Set preedit: " << text;

    // Step 2: 提交文本
    ic->commitString(text);
    NEXTALK_INFO() << "Committed text to: " << ic->program()
                   << " hasFocus=" << ic->hasFocus()
                   << " text=" << text;

    // Step 3: 清空 preedit
    ic->inputPanel().setClientPreedit(Text(""));
    ic->updatePreedit();
    NEXTALK_DEBUG() << "Cleared preedit";
}

} // namespace fcitx

FCITX_ADDON_FACTORY(fcitx::NextalkAddonFactory);
