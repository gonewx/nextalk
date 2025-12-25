/*
 * SPDX-FileCopyrightText: 2024 Nextalk Project
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Nextalk Fcitx5 Addon - 语音识别文本提交插件
 *
 * 功能：
 * 1. 监听 Unix Socket，接收语音识别结果，提交到当前焦点应用
 * 2. 监听全局快捷键（可配置），通知 Flutter 应用激活/隐藏窗口
 */

#ifndef _FCITX5_NEXTALK_NEXTALK_H_
#define _FCITX5_NEXTALK_NEXTALK_H_

#include <fcitx/addoninstance.h>
#include <fcitx/addonfactory.h>
#include <fcitx/addonmanager.h>
#include <fcitx/instance.h>
#include <fcitx-utils/eventdispatcher.h>
#include <fcitx-utils/handlertable.h>
#include <fcitx-utils/key.h>
#include <fcitx/event.h>
#include <memory>
#include <string>
#include <thread>
#include <atomic>
#include <vector>
#include <unordered_map>
#include <unordered_set>

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

    // ===== 命令 Socket 服务器 (接收配置) =====
    void startConfigListener();
    void stopConfigListener();
    void configListenerLoop();
    void handleConfigClient(int clientFd);
    void processCommand(const std::string &command);
    std::string getConfigSocketPath() const;

    // ===== 快捷键监听 (Wayland 支持) =====
    void setupKeyEventHandler();
    void handleKeyEvent(KeyEvent &keyEvent);
    // 发送命令到 Flutter 应用
    void sendCommandToFlutter(const std::string &command);
    std::string getCommandSocketPath() const;

    // ===== 快捷键配置 =====
    void initKeyMap();
    bool parseHotkeyConfig(const std::string &config);
    bool isConfiguredHotkey(const Key &key) const;

    Instance *instance_;
    EventDispatcher dispatcher_;

    // 文本接收 Socket
    std::thread listenerThread_;
    std::atomic<bool> running_{false};
    int serverFd_{-1};

    // 配置接收 Socket
    std::thread configListenerThread_;
    std::atomic<bool> configRunning_{false};
    int configServerFd_{-1};

    // 快捷键事件处理器
    std::vector<std::unique_ptr<HandlerTableEntry<EventHandler>>> eventHandlers_;
    // 快捷键状态跟踪 (用于检测按下-释放)
    bool hotkeyPressed_{false};

    // ===== 快捷键配置 =====
    // 当前配置的主键 (默认 Alt_R)
    KeySym configuredKey_{FcitxKey_Alt_R};
    // 配置的修饰键集合
    KeyStates configuredModifiers_{};
    // 按键名称到 KeySym 的映射
    std::unordered_map<std::string, KeySym> keyNameMap_;

    // ===== 焦点锁定 (Wayland 支持) =====
    // 在按下快捷键时锁定的 InputContext UUID
    // 用于解决 Wayland 下焦点切换导致文本提交到错误窗口的问题
    ICUUID lockedInputContextUUID_{};
    bool hasLockedContext_{false};
};

class NextalkAddonFactory : public AddonFactory {
public:
    AddonInstance *create(AddonManager *manager) override {
        return new NextalkAddon(manager->instance());
    }
};

} // namespace fcitx

#endif // _FCITX5_NEXTALK_NEXTALK_H_
