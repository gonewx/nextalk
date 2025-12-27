/**
 * Nextalk GNOME Shell Extension - POC
 *
 * 验证目标：
 * 1. 创建不抢焦点的 overlay 窗口
 * 2. 通过 D-Bus 控制 UI 显示
 * 3. 验证焦点保持在目标应用
 */

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// D-Bus 接口定义
const DBUS_INTERFACE = `
<node>
  <interface name="com.gonewx.nextalk.Panel">
    <method name="Show">
      <arg type="b" direction="in" name="visible"/>
    </method>
    <method name="SetText">
      <arg type="s" direction="in" name="text"/>
    </method>
    <method name="SetState">
      <arg type="s" direction="in" name="state"/>
    </method>
    <method name="SetPosition">
      <arg type="i" direction="in" name="x"/>
      <arg type="i" direction="in" name="y"/>
    </method>
    <method name="GetInfo">
      <arg type="s" direction="out" name="info"/>
    </method>
    <signal name="Clicked"/>
  </interface>
</node>`;

// 状态颜色映射
const STATE_STYLES = {
    'idle': 'background-color: rgba(60, 60, 60, 0.9);',
    'listening': 'background-color: rgba(220, 50, 50, 0.95);',
    'processing': 'background-color: rgba(50, 120, 220, 0.95);',
    'success': 'background-color: rgba(50, 180, 80, 0.95);',
};

class NextalkCapsule {
    constructor() {
        this._capsule = null;
        this._icon = null;
        this._label = null;
        this._dbusId = null;
        this._nameOwnerId = null;
        this._currentState = 'idle';
    }

    enable() {
        this._createUI();
        this._registerDBus();
        this._log('Extension enabled');
    }

    _createUI() {
        // 创建主容器 - 胶囊样式
        this._capsule = new St.BoxLayout({
            style_class: 'nextalk-capsule',
            style: `
                ${STATE_STYLES['idle']}
                border-radius: 25px;
                padding: 8px 16px;
                spacing: 8px;
            `,
            reactive: false,  // 关键：不响应鼠标事件
            can_focus: false, // 关键：不能获取焦点
            track_hover: false,
            visible: false,
        });

        // 麦克风图标
        this._icon = new St.Icon({
            icon_name: 'audio-input-microphone-symbolic',
            style: 'icon-size: 20px; color: white;',
        });

        // 文本标签
        this._label = new St.Label({
            text: 'Nextalk Ready',
            style: 'color: white; font-size: 14px; font-weight: 500;',
            y_align: Clutter.ActorAlign.CENTER,
        });

        this._capsule.add_child(this._icon);
        this._capsule.add_child(this._label);

        // ⚠️ 关键：添加到顶层 Chrome，设置不影响输入区域
        Main.layoutManager.addTopChrome(this._capsule, {
            affectsInputRegion: false,  // 🔑 不影响输入区域 = 不抢焦点
            affectsStruts: false,       // 不影响窗口布局
            trackFullscreen: true,      // 全屏时也显示
        });

        // 设置初始位置（屏幕顶部居中）
        this._updatePosition();

        // 监听屏幕大小变化
        this._monitorsChangedId = Main.layoutManager.connect(
            'monitors-changed',
            () => this._updatePosition()
        );
    }

    _updatePosition() {
        const monitor = Main.layoutManager.primaryMonitor;
        if (monitor && this._capsule) {
            const x = Math.floor((monitor.width - this._capsule.width) / 2);
            const y = 50; // 距离顶部 50px
            this._capsule.set_position(x, y);
        }
    }

    _registerDBus() {
        try {
            const nodeInfo = Gio.DBusNodeInfo.new_for_xml(DBUS_INTERFACE);

            this._dbusId = Gio.DBus.session.register_object(
                '/com/gonewx/nextalk/Panel',
                nodeInfo.interfaces[0],
                (connection, sender, path, iface, method, params, invocation) => {
                    this._handleMethodCall(connection, sender, path, iface, method, params, invocation);
                },
                null,
                null
            );

            this._nameOwnerId = Gio.DBus.session.own_name(
                'com.gonewx.nextalk.Panel',
                Gio.BusNameOwnerFlags.NONE,
                () => this._log('D-Bus name acquired: com.gonewx.nextalk.Panel'),
                () => this._log('D-Bus name lost')
            );

            this._log('D-Bus registered successfully');
        } catch (e) {
            this._log(`D-Bus registration failed: ${e.message}`);
        }
    }

    _handleMethodCall(connection, sender, path, iface, method, params, invocation) {
        this._log(`D-Bus call: ${method}`);

        try {
            switch (method) {
                case 'Show': {
                    const [visible] = params.deep_unpack();
                    this._capsule.visible = visible;
                    if (visible) {
                        this._updatePosition();
                    }
                    invocation.return_value(null);
                    break;
                }

                case 'SetText': {
                    const [text] = params.deep_unpack();
                    this._label.text = text || 'Nextalk';
                    this._updatePosition(); // 文本变化后重新居中
                    invocation.return_value(null);
                    break;
                }

                case 'SetState': {
                    const [state] = params.deep_unpack();
                    this._currentState = state;
                    const style = STATE_STYLES[state] || STATE_STYLES['idle'];
                    this._capsule.style = `
                        ${style}
                        border-radius: 25px;
                        padding: 8px 16px;
                        spacing: 8px;
                    `;

                    // 更新图标
                    if (state === 'listening') {
                        this._icon.icon_name = 'audio-input-microphone-symbolic';
                    } else if (state === 'processing') {
                        this._icon.icon_name = 'emblem-synchronizing-symbolic';
                    } else if (state === 'success') {
                        this._icon.icon_name = 'emblem-ok-symbolic';
                    } else {
                        this._icon.icon_name = 'audio-input-microphone-symbolic';
                    }

                    invocation.return_value(null);
                    break;
                }

                case 'SetPosition': {
                    const [x, y] = params.deep_unpack();
                    this._capsule.set_position(x, y);
                    invocation.return_value(null);
                    break;
                }

                case 'GetInfo': {
                    const info = JSON.stringify({
                        visible: this._capsule.visible,
                        state: this._currentState,
                        position: {
                            x: this._capsule.x,
                            y: this._capsule.y,
                        },
                        version: '1.0.0-poc',
                    });
                    invocation.return_value(new GLib.Variant('(s)', [info]));
                    break;
                }

                default:
                    invocation.return_error_literal(
                        Gio.DBusError,
                        Gio.DBusError.UNKNOWN_METHOD,
                        `Unknown method: ${method}`
                    );
            }
        } catch (e) {
            this._log(`Method ${method} error: ${e.message}`);
            invocation.return_error_literal(
                Gio.DBusError,
                Gio.DBusError.FAILED,
                e.message
            );
        }
    }

    _log(message) {
        console.log(`[Nextalk] ${message}`);
    }

    disable() {
        // 清理 D-Bus
        if (this._dbusId) {
            Gio.DBus.session.unregister_object(this._dbusId);
            this._dbusId = null;
        }

        if (this._nameOwnerId) {
            Gio.DBus.session.unown_name(this._nameOwnerId);
            this._nameOwnerId = null;
        }

        // 清理监听器
        if (this._monitorsChangedId) {
            Main.layoutManager.disconnect(this._monitorsChangedId);
            this._monitorsChangedId = null;
        }

        // 清理 UI
        if (this._capsule) {
            Main.layoutManager.removeChrome(this._capsule);
            this._capsule.destroy();
            this._capsule = null;
        }

        this._log('Extension disabled');
    }
}

// 导出扩展类
export default class NextalkExtension {
    constructor() {
        this._capsule = null;
    }

    enable() {
        this._capsule = new NextalkCapsule();
        this._capsule.enable();
    }

    disable() {
        if (this._capsule) {
            this._capsule.disable();
            this._capsule = null;
        }
    }
}
