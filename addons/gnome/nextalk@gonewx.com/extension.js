// Nextalk GNOME Shell 注入扩展
//
// 在 gnome-shell 进程内导出 D-Bus 方法 CommitText，内部调用
// Main.inputMethod.commit()——这是 GNOME 屏幕键盘 (OSK) 的上屏通道，
// 与会话使用的输入法框架无关（ibus/fcitx5 均可，中文直接提交）。
// 供 Nextalk 在 fcitx5 socket 不可用的 GNOME 环境（如 Fedora 默认
// ibus 会话）作为二级注入后端直接上屏识别文本。
//
// 客户端调用方式：dest 为 org.gnome.Shell（扩展挂在 gnome-shell 自身
// 的 bus 连接上，无需自持 bus name），路径 /com/gonewx/nextalk/Inject，
// 接口 com.gonewx.nextalk.Inject，方法 CommitText(s)→(s)。
//
// 已于 2026-07-10 在 Fedora 43 (GNOME 49.1 + ibus) POC 验证可注入中文。
//
// GrabCancelKey(b)→(b)：录音期间临时抢占 Esc 加速键，按下时发出
// CancelRequested 信号，Nextalk 据此取消本次语音输入。胶囊窗口不接受
// 焦点，应用自身收不到 Esc，只能由 compositor 侧代为捕获。

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const IFACE = `<node>
<interface name="com.gonewx.nextalk.Inject">
  <method name="CommitText">
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
    }

    disable() {
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

    CommitText(text) {
        try {
            // commit 走 mutter 的 text-input 通道，仅 Wayland 原生窗口可达；
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
