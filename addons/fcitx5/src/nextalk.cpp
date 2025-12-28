/*
 * SPDX-FileCopyrightText: 2024 Nextalk Project
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * SCP-002 极简架构：
 * - 只保留文本接收和上屏功能
 * - 快捷键由系统原生快捷键 + --toggle 参数处理
 */

#include "nextalk.h"
#include <fcitx-utils/log.h>
#include <fcitx/inputcontext.h>
#include <fcitx/inputcontextmanager.h>
#include <fcitx/inputpanel.h>
#include <fcitx/text.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
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

    NEXTALK_INFO() << "Nextalk addon initialized";
    NEXTALK_INFO() << "Text socket: " << getSocketPath();
}

NextalkAddon::~NextalkAddon() {
    NEXTALK_INFO() << "Nextalk addon shutting down...";
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
