// Nextalk GNOME Shell 注入扩展
//
// 在 gnome-shell 进程内导出 D-Bus 方法 CommitText，优先通过 IBus 主 Panel
// 提交，失败后回退到 Main.inputMethod.commit()（GNOME 屏幕键盘通道），
// 两者均失败时返回 ERR，由客户端回退到剪贴板。
// 供 Nextalk 在 fcitx5 socket 不可用的 GNOME 环境（如 Fedora 默认
// ibus 会话）作为二级注入后端直接上屏识别文本。
//
// 客户端调用方式：dest 为 org.gnome.Shell（扩展挂在 gnome-shell 自身
// 的 bus 连接上，无需自持 bus name），路径 /com/gonewx/nextalk/Inject，
// 接口 com.gonewx.nextalk.Inject，方法 CommitText(s)→(s)。
//
// Panel 路径已于 2026-11-01 在 Fedora 43 VM（GNOME 49.1 + ibus）
// 验证可注入 Wayland 原生及 XWayland 窗口；_panelService 是 gnome-shell
// 私有字段，因此保留 Main.inputMethod 路径作为回退。
//
// GrabCancelKey(b)→(b)：录音期间临时抢占 Esc 加速键，按下时发出
// CancelRequested 信号，Nextalk 据此取消本次语音输入。胶囊窗口不接受
// 焦点，应用自身收不到 Esc，只能由 compositor 侧代为捕获。
// CommitTextViaPanel 保留为诊断方法，验证记录见
// docs/research/ibus-support-2026.md §8.1。

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import IBus from 'gi://IBus';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as IBusManager from 'resource:///org/gnome/shell/misc/ibusManager.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const IFACE = `<node>
<interface name="com.gonewx.nextalk.Inject">
  <method name="CommitText">
    <arg type="s" direction="in" name="text"/>
    <arg type="s" direction="out" name="result"/>
  </method>
  <method name="CommitTextViaPanel">
    <arg type="s" direction="in" name="text"/>
    <arg type="s" direction="out" name="result"/>
  </method>
  <method name="GrabCancelKey">
    <arg type="b" direction="in" name="grab"/>
    <arg type="b" direction="out" name="grabbed"/>
  </method>
  <signal name="CancelRequested"/>
</interface>
</node>`;

export default class NextalkInjectExtension extends Extension {
    enable() {
        this._dbus = Gio.DBusExportedObject.wrapJSObject(IFACE, this);
        this._dbus.export(Gio.DBus.session, '/com/gonewx/nextalk/Inject');
        try {
            this._ibusManager = IBusManager.getIBusManager();
            this._ibusReadyId = this._ibusManager.connect('ready', () => {
                try {
                    this._hookPanelService();
                } catch (e) {
                    console.debug(`Nextalk：监听 IBus 面板失败：${e}`);
                }
            });
            this._hookPanelService();
        } catch (e) {
            console.debug(`Nextalk：初始化 IBus 面板监听失败：${e}`);
        }
    }

    disable() {
        if (this._ibusReadyId) {
            this._ibusManager.disconnect(this._ibusReadyId);
            this._ibusReadyId = 0;
        }
        this._ibusManager = null;
        this._disconnectPanelService();
        this._releaseCancelKey();
        if (this._acceleratorId) {
            global.display.disconnect(this._acceleratorId);
            this._acceleratorId = 0;
        }
        if (this._dbus) {
            this._dbus.unexport();
            this._dbus = null;
        }
    }

    GrabCancelKey(grab) {
        try {
            if (!grab) {
                this._releaseCancelKey();
                return true;
            }
            if (this._escAction)
                return true;

            const action = global.display.grab_accelerator(
                'Escape', Meta.KeyBindingFlags.NONE);
            if (action === Meta.KeyBindingAction.NONE)
                return false;

            this._escAction = action;
            this._escName = Meta.external_binding_name_for_action(action);
            Main.wm.allowKeybinding(this._escName, Shell.ActionMode.ALL);

            if (!this._acceleratorId) {
                this._acceleratorId = global.display.connect(
                    'accelerator-activated', (display, activated) => {
                        if (activated === this._escAction)
                            this._dbus?.emit_signal('CancelRequested', null);
                    });
            }

            // 安全阀：客户端崩溃未归还时自动释放，Esc 不会被永久抢占
            this._escTimeoutId = GLib.timeout_add_seconds(
                GLib.PRIORITY_DEFAULT, 600, () => {
                    this._escTimeoutId = 0;
                    this._releaseCancelKey();
                    return GLib.SOURCE_REMOVE;
                });
            return true;
        } catch (e) {
            logError(e, 'Nextalk: GrabCancelKey failed');
            return false;
        }
    }

    _releaseCancelKey() {
        if (this._escTimeoutId) {
            GLib.source_remove(this._escTimeoutId);
            this._escTimeoutId = 0;
        }
        if (!this._escAction)
            return;
        global.display.ungrab_accelerator(this._escAction);
        Main.wm.allowKeybinding(this._escName, Shell.ActionMode.NONE);
        this._escAction = 0;
        this._escName = null;
    }

    _disconnectPanelService() {
        for (const id of this._panelSignalIds ?? [])
            this._panelService.disconnect(id);
        this._panelSignalIds = [];
        this._panelService = null;
        this._panelFocusKnown = false;
        this._panelContextPath = null;
    }

    _hookPanelService() {
        const panel = IBusManager.getIBusManager()._panelService ?? null;
        if (panel === this._panelService)
            return panel;
        this._disconnectPanelService();
        this._panelService = panel;
        if (panel) {
            // 新实例尚未发出焦点信号时，不能推断已有输入焦点。
            this._panelSignalIds.push(panel.connect('focus-in', (service, path) => {
                this._panelFocusKnown = true;
                this._panelContextPath = path.endsWith('/InputContext_1') ? null : path;
            }));
            this._panelSignalIds.push(panel.connect('focus-out', () => {
                this._panelFocusKnown = true;
                this._panelContextPath = null;
            }));
        }
        return panel;
    }

    CommitTextViaPanel(text) {
        if (!text)
            return 'ERR: empty text';
        return this._commitViaPanel(text);
    }

    _commitViaPanel(text) {
        try {
            const panel = this._hookPanelService();
            if (!panel)
                return 'ERR: ibus panel service unavailable';
            if (!this._panelFocusKnown)
                return 'ERR: focus state unknown';
            if (!this._panelContextPath)
                return 'ERR: no focused ibus input context';
            console.debug(`Nextalk：通过 IBus 面板提交，上下文：${this._panelContextPath}`);
            panel.commit_text(IBus.Text.new_from_string(text));
            return 'OK';
        } catch (e) {
            return `ERR: ${e}`;
        }
    }

    CommitText(text) {
        if (!text)
            return 'ERR: empty text';
        const panelResult = this._commitViaPanel(text);
        if (panelResult === 'OK')
            return 'OK';
        const imResult = this._commitViaInputMethod(text);
        if (imResult === 'OK')
            return 'OK';
        return `ERR: panel(${panelResult.slice(5)}); im(${imResult.slice(5)})`;
    }

    _commitViaInputMethod(text) {
        try {
            // Panel 失败后的回退走 mutter 的 text-input 通道，仅 Wayland 原生窗口可达；
            // XWayland/X11 窗口收不到且无报错（2026-07-10 Fedora 43 实测），
            // 必须显式返回 ERR 让客户端走剪贴板 fallback，否则文本静默丢失。
            const focusWindow = global.display.focus_window;
            if (!focusWindow)
                return 'ERR: no focused window';
            if (focusWindow.get_client_type() === Meta.WindowClientType.X11)
                return 'ERR: X11/XWayland target not reachable via text-input';
            const im = Main.inputMethod;
            if (!im)
                return 'ERR: Main.inputMethod is null';
            // im.commit() 返回 void，对无活动 text-input 上下文的目标（焦点
            // 不在可编辑控件、或应用未实现 text-input 协议，如部分 Electron）
            // 是静默 no-op——必须提交前确认存在活动输入焦点并返回 ERR 让客户
            // 端走剪贴板，否则文本静默丢失。currentFocus 是 gnome-shell
            // InputMethod 的 getter；若未来版本移除（undefined）则退回私有
            // 字段，两者都取不到时保持提交（宁可尝试，不误伤正常路径）。
            const focus = im.currentFocus !== undefined
                ? im.currentFocus : im._currentFocus;
            if (focus === null)
                return 'ERR: no active text input in focused window';
            im.commit(text);
            return 'OK';
        } catch (e) {
            return `ERR: ${e}`;
        }
    }
}
