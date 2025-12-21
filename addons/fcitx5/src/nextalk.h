/*
 * SPDX-FileCopyrightText: 2024 Nextalk Project
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Nextalk Fcitx5 Addon - 语音识别文本提交插件
 *
 * 功能：监听 Unix Socket，接收语音识别结果，提交到当前焦点应用
 */

#ifndef _FCITX5_NEXTALK_NEXTALK_H_
#define _FCITX5_NEXTALK_NEXTALK_H_

#include <fcitx/addoninstance.h>
#include <fcitx/addonfactory.h>
#include <fcitx/addonmanager.h>
#include <fcitx/instance.h>
#include <fcitx-utils/eventdispatcher.h>
#include <memory>
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
    // 启动 Socket 监听线程
    void startSocketListener();
    // 停止 Socket 监听
    void stopSocketListener();
    // Socket 监听循环
    void socketListenerLoop();
    // 处理客户端连接
    void handleClient(int clientFd);
    // 获取 Socket 路径
    std::string getSocketPath() const;

    Instance *instance_;
    EventDispatcher dispatcher_;
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
