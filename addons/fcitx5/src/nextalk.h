/*
 * SPDX-FileCopyrightText: 2024 Nextalk Project
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Nextalk Fcitx5 Addon - 语音识别文本提交插件
 *
 * 功能：
 * - 监听 Unix Socket，接收语音识别结果，提交到当前焦点应用
 *
 * SCP-002 极简架构：
 * - 移除快捷键监听 (改为系统快捷键 + --toggle 参数)
 * - 移除配置 Socket
 * - 只保留文本接收和上屏功能
 */

#ifndef _FCITX5_NEXTALK_NEXTALK_H_
#define _FCITX5_NEXTALK_NEXTALK_H_

#include <fcitx/addoninstance.h>
#include <fcitx/addonfactory.h>
#include <fcitx/addonmanager.h>
#include <fcitx/instance.h>
#include <fcitx-utils/eventdispatcher.h>
#include <string>
#include <thread>
#include <atomic>

namespace fcitx {

class NextalkAddon : public AddonInstance {
public:
    NextalkAddon(Instance *instance);
    ~NextalkAddon() override;

    // 提交文本到当前焦点的输入上下文
    void commitText(const std::string &text);

private:
    // ===== Socket 服务器 (接收识别文本) =====
    void startSocketListener();
    void stopSocketListener();
    void socketListenerLoop();
    void handleClient(int clientFd);
    std::string getSocketPath() const;

    Instance *instance_;
    EventDispatcher dispatcher_;

    // 文本接收 Socket
    std::thread listenerThread_;
    std::atomic<bool> running_{false};
    int serverFd_{-1};
};

class NextalkAddonFactory : public AddonFactory {
public:
    AddonInstance *create(AddonManager *manager) override {
        return new NextalkAddon(manager->instance());
    }
};

} // namespace fcitx

#endif // _FCITX5_NEXTALK_NEXTALK_H_
