# Development Pitfalls Record

[简体中文](development-pitfalls_zh.md) | English

This document records technical issues encountered during Nextalk development, root cause analysis, and solutions for future maintenance reference.

---

## Table of Contents

- [Flutter system_tray Library Linux Checkbox State Bug](#flutter-system_tray-library-linux-checkbox-state-bug)
- [xdg-desktop-portal-gnome 48.0 BindShortcuts False-Failure Bug](#xdg-desktop-portal-gnome-480-bindshortcuts-false-failure-bug)
- [Two Normal Mechanisms Behind the GNOME Global Shortcuts Dialog "Not Showing"](#two-normal-mechanisms-behind-the-gnome-global-shortcuts-dialog-not-showing)
- [60s Portal Dialog Interaction Timeout Breaks Slow-User Binding](#60s-portal-dialog-interaction-timeout-breaks-slow-user-binding)
- [Instant Segfault on Fedora: Upstream system_tray dlopens the Legacy libappindicator](#instant-segfault-on-fedora-upstream-system_tray-dlopens-the-legacy-libappindicator)
- [Window Positioning APIs Are Inert on the Native Wayland Backend (Prefer-XWayland Decision)](#window-positioning-apis-are-inert-on-the-native-wayland-backend-prefer-xwayland-decision)

---

## Flutter system_tray Library Linux Checkbox State Bug

### Problem Description

When using the `system_tray` package (v2.0.3) on Linux, the `MenuItemCheckbox` component in tray menus cannot correctly update checked state.

**Symptoms**:
- Code logic correctly passes `checked: false`, but UI still shows as checked (ticked)
- Multiple mutually exclusive checkbox items simultaneously show as checked
- Problem persists after rebuilding menu

### Reproduction Scenario

```dart
// Code logic is correct
final senseChecked = actualEngine == EngineType.sensevoice;  // false
final zipStdChecked = actualEngine == EngineType.zipformer;  // true

MenuItemCheckbox(
  label: 'SenseVoice',
  checked: senseChecked,  // passes false
  onClicked: (_) => _switchEngine(EngineType.sensevoice),
),
```

Log output confirms correct values:
```
[TrayService._buildMenu] zipInt8=false, zipStd=true, sense=false
```

But tray menu shows both SenseVoice and Zipformer items **simultaneously checked**.

### Root Cause Analysis

By analyzing `system_tray` library's Linux native implementation (`~/.pub-cache/hosted/pub.dev/system_tray-2.0.3/linux/`):

1. **Menu cache not cleared**: `MenuManager::menus_map_` static Map accumulates old menus, old menu GTK widgets may still be referenced
2. **GTK checkbox state residue**: `tray.cc`'s `set_context_menu()` method simply calls `app_indicator_set_menu_()`, doesn't properly destroy old GTK menu or reset checkbox state
3. **menu_id increments but old menus not deleted**: Each `buildFrom()` increments `_menuId`, but old entries in `menus_map_` not cleaned up

Key code locations:
- `tray.cc:set_context_menu()` - doesn't clean old menu
- `menu_manager.cc:add_menu()` - uses `emplace` which only adds, doesn't replace
- `menu.cc:value_to_menu_item()` - checkbox creation logic itself is correct

### Solution

**Adopted Solution**: Use `MenuItemLabel` + marker symbols instead of `MenuItemCheckbox` to avoid the library bug.

```dart
// Before (buggy)
MenuItemCheckbox(
  label: lang.tr('tray_engine_sensevoice'),
  checked: actualEngine == EngineType.sensevoice,
  onClicked: (_) => _switchEngine(EngineType.sensevoice),
),

// After (workaround)
MenuItemLabel(
  label: '${senseChecked ? "● " : ""}${lang.tr('tray_engine_sensevoice')}',
  onClicked: (_) => _switchEngine(EngineType.sensevoice),
),
```

**Result**:
- Selected item shows `● SenseVoice (Offline)`
- Unselected item shows `SenseVoice (Offline)`
- State updates reliably

### Related Files

- `voice_capsule/lib/services/tray_service.dart` - Tray service implementation
- Library source: `~/.pub-cache/hosted/pub.dev/system_tray-2.0.3/linux/`

### Alternative Solutions (Not Adopted)

1. **Destroy and rebuild entire tray**: Call `SystemTray.destroy()` then re-init `initSystemTray()`, but causes tray icon flicker
2. **Switch to tray_manager library**: Another tray library with explicit checkbox support, but requires migration cost evaluation
3. **Submit PR to fix upstream**: Fix `system_tray` library's Linux implementation, long-term solution

---

## xdg-desktop-portal-gnome 48.0 BindShortcuts False-Failure Bug

### Problem Description

On Debian 13/GNOME 48, the Portal `BindShortcuts` binding **actually fully succeeds** (gnome-shell completes GrabAccelerators, the `ShortcutsChanged` signal is emitted, the shortcut genuinely works), yet the app receives `Request::Response` status code 2 (failure). The app misreads this as failure, closes the session — unbinding the shortcut — and permanently falls back to system-shortcut mode.

### Reproduction

Launch the app on Debian 13 (xdg-desktop-portal-gnome 48.0-2); diagnostic.log shows on every start:

```
[PortalHotkey] ⚠️ Falling back to system shortcut: Portal registration failed: (response=2)
```

`dbus-monitor` capture shows the provider (gnome-control-center) returning the successfully-bound `<Super>z` from `BindShortcuts`, yet 1.5ms later portal-gnome emits `Response` `uint32 2` to the app — with the bound shortcuts array still present in results.

### Root Cause

In xdg-desktop-portal-gnome 48.0 `src/globalshortcuts.c`, `shell_grab_accelerators_done()` declares `int response;` but only the failure path assigns `response = 2`; **the success path never assigns it** before jumping to the `out:` label, sending an uninitialized stack value (which happens to be 2) to the app. Upstream commit `27511907` ("globalshortcuts: Fix BindShortcut success response", 2025-08-02) adds `response = 0;` on the success path, but Debian 13's 48.0-2 does not include it and, as a stable release, will stay on this version long-term.

### Solution

Detect the false failure app-side: `_sendRequest` throws `PortalRequestFailedException` carrying the results; `bindShortcuts` catches it and decides via `shortcutsActuallyBound()` — response=2 with a non-empty shortcuts array covering every requested id is treated as success. Safety: the bug's real failure paths (provider error, grab failure) all return an empty vardict, so no misclassification.

```dart
} on PortalRequestFailedException catch (e) {
  if (!shortcutsActuallyBound(e.results, shortcuts)) rethrow;
}
```

### Related Files

- `voice_capsule/lib/services/portal_hotkey_service.dart` (`PortalRequestFailedException`, `shortcutsActuallyBound`)
- `voice_capsule/test/services/portal_hotkey_service_test.dart` ("GNOME 48.0 false-failure detection" test group)

### Alternatives (Not Adopted)

- Verify via `ListShortcuts` after binding: an extra D-Bus round trip, and 48.0's ListShortcuts behavior is unverified
- Wait for a Debian patch: not in our control; stable branches rarely backport such fixes

---

## Two Normal Mechanisms Behind the GNOME Global Shortcuts Dialog "Not Showing"

### Problem Description

When testing the "first install shows the authorization dialog" flow, the dialog never appears on launch; even after clearing the `applications` authorization list in `gsettings`, reinstalling, and restarting, it still does not appear — and the app id is automatically written back into the list.

### Reproduction

```bash
gsettings set org.gnome.settings-daemon.global-shortcuts applications "[]"
# Restart the app → still no dialog, and com.gonewx.nextalk reappears in the list
```

### Root Cause

Two stacked mechanisms:

1. **Authorization memory**: GNOME stores each app's shortcut authorization in dconf under `/org/gnome/settings-daemon/global-shortcuts/` — the `applications` key is only an **index**; the shortcuts themselves live in per-app subpaths (e.g. `[com.gonewx.nextalk] shortcuts=...`).
2. **Silent approval**: gnome-control-center 48.4's `cc_global_shortcut_dialog_present()` begins with `if (!self->has_new_shortcuts) { emit_done(self, TRUE); return; }` — when the requested shortcuts match what is stored (nothing "new"), it approves directly, writes the app back into the index, and shows no dialog. Clearing only the index leaves the per-app subpaths intact, so requests always hit "already stored".

### Solution

To see the dialog again, reset the **entire subtree** (index + per-app storage):

```bash
dconf reset -f /org/gnome/settings-daemon/global-shortcuts/
```

Then restart the app (a single run attempts registration only once) and the dialog appears. Note both "no dialog" cases are benign for users — the binding silently succeeds and the shortcut works.

### Related Files

- gnome-control-center `global-shortcuts-provider/cc-global-shortcut-dialog.c` (upstream behavior)
- `docs/architecture.md` §2.1 4th-generation hotkey "Lifecycle"

### Alternatives (Not Adopted)

None — this is GNOME's intended design; the app neither needs to nor should bypass it.

---

## 60s Portal Dialog Interaction Timeout Breaks Slow-User Binding

### Problem Description

After the authorization dialog appears on first launch, if the user does not click "Add" within 60 seconds, the app times out (`TimeoutException after 0:01:00`), locks the registration attempt, and falls back to system shortcuts; **clicking "Add" afterwards only writes to GNOME-side storage — the shortcut stays dead for the current session** (the app already closed the session and stopped listening). Symptom: "I clicked Add but the shortcut does nothing."

### Reproduction

1. After `dconf reset -f /org/gnome/settings-daemon/global-shortcuts/`, launch the app; the dialog appears
2. Wait more than 60 seconds before clicking "Add"
3. Super+Z does nothing; diagnostic.log shows the timeout fallback; restarting the app recovers (authorization is stored, so startup registers silently)

### Root Cause

`DBusGlobalShortcutsBackend`'s interaction timeout (`_interactiveTimeout`) was 60s. Real first-run users frequently do not handle a system dialog immediately (reading it, switching windows, stepping away) — 60s is an easily-crossed threshold. The timeout takes the `catch` branch: `_registerAttempted = true` locks the attempt and `closeSession` runs, so the session cannot bind again. Meanwhile GNOME's dialog lives independently of the portal session, and a later click still writes to dconf — producing the split state "system authorized, app gave up".

### Solution

Relax the interaction timeout to **10 minutes**. Rationale: the dialog stays up waiting for the user, and `Response` is always emitted when a button is clicked (Add/Cancel) — the only thing the timeout must guard against is a backend that neither shows a dialog nor replies; 10 minutes is generous yet still converges. Field-tested: clicking "Add" after 8 minutes idle registers immediately.

```dart
_interactiveTimeout =
    interactiveTimeout ?? timeout ?? const Duration(minutes: 10)
```

### Related Files

- `voice_capsule/lib/services/portal_hotkey_service.dart` (`DBusGlobalShortcutsBackend` constructor)

### Alternatives (Not Adopted)

- Remove the timeout entirely: on a broken backend the Future hangs forever, the tray mode is stuck on "system shortcut", and resources never release
- Don't lock `_registerAttempted` on timeout: the current architecture has no automatic retry trigger, so locking or not behaves identically — treats the symptom, not the cause
- Keep the session open and listen for Response in the background after timeout: a large change; the 10-minute timeout already covers real scenarios

---

## Instant Segfault on Fedora: Upstream system_tray dlopens the Legacy libappindicator

### Problem Description

On Fedora 43 the app segfaults (core dumped) right after `method call InitSystemTray`; the exact same 0.2.13 package works perfectly on Debian 13.

### Reproduction

Fedora 43 (GNOME 49/Wayland) with the legacy `libappindicator-12.10.1` installed (an orphan package — nothing depends on it): running `nextalk` crashes every time. coredumpctl stack:

```
#0 app_indicator_set_status (libappindicator3.so.1)   ← deprecated legacy library
#1 Tray::init_tray (libsystem_tray_plugin.so)
```

### Root Cause

Upstream `system_tray 2.0.3`'s `linux/tray.cc` detects and links ayatana at the CMake level, but at runtime **hardcodes `dlopen("libappindicator3.so.1")`** (the legacy name) and pulls every function pointer via dlsym:

- **Debian 13**: the `libayatana-appindicator3-1` package ships a compat symlink `libappindicator3.so.1 -> libayatana-appindicator3.so.1`, so dlopen-by-old-name actually gets the healthy ayatana → works (the upstream bug is masked by the distro symlink)
- **Fedora 43**: no compat symlink; `libappindicator3.so.1` is provided by the genuinely legacy `libappindicator-12.10.1`, whose `app_indicator_set_status` segfaults under GNOME 49/Wayland

A Dart-level try/catch cannot contain a native segfault — the whole process dies.

### Solution

Vendor the plugin source into `third_party/system_tray/` and patch it — try ayatana first, fall back to the legacy name:

```c
void* handle = dlopen("libayatana-appindicator3.so.1", RTLD_LAZY);
if (!handle) {
  handle = dlopen("libappindicator3.so.1", RTLD_LAZY);
}
```

`pubspec.yaml` points to the vendored copy via `dependency_overrides`. Field-tested on Fedora 43: InitSystemTray passes and the top-bar icon shows (with the `gnome-shell-extension-appindicator` extension enabled).

### Related Files

- `third_party/system_tray/linux/tray.cc` (patch site, marked with a Nextalk patch comment)
- `voice_capsule/pubspec.yaml` (dependency_overrides)

### Alternatives (Not Adopted)

- Add `Conflicts: libappindicator` to the rpm: meddles with the user's system packages; other apps may need the legacy lib
- Tell users to `dnf remove libappindicator`: treats the symptom; fresh installs would still hit it
- Submit the patch upstream: should be done (the patch is directly contributable), but the upstream release cadence is out of our control — vendoring ships first

---

## Window Positioning APIs Are Inert on the Native Wayland Backend (Prefer-XWayland Decision)

### Problem Description

The capsule window always appears in the top-left corner of the screen, and after
the user drags it elsewhere the next invocation still snaps back to the top-left.
The position keys in `~/.local/share/nextalk/shared_preferences.json` end up
written as `0.0/0.0`.

### Reproduction Scenario

The `.desktop` file has carried `Exec=env GDK_BACKEND=x11 ...` all along, but when
no instance is running `scripts/nextalk-toggle.sh` cold-starts through
`exec nextalk --toggle`, bypassing the `.desktop` env entirely — so the app runs on
the native Wayland backend.

### Root Cause Analysis

The Wayland protocol does not let a client position its own toplevel. Probe output
measured on GNOME/Ubuntu with `XDG_SESSION_TYPE=wayland` and a GTK3 undecorated
UTILITY window:

```
=== NATIVE WAYLAND ===        === FORCED X11 (XWayland) ===
T1_INITIAL=(0,0)              T1_INITIAL=(58,0)
T2_MOVE_CALLED(700,900)       T2_MOVE_CALLED(700,900)
T3_AFTER_MOVE_SETTLED=(0,0)   T3_AFTER_MOVE_SETTLED=(700,900)
```

Conclusion: on the native Wayland backend `gtk_window_move()` is a complete no-op
and `gtk_window_get_position()` always returns `(0,0)`; under XWayland both work.

This single fact explains three linked symptoms:

1. Default positioning silently fails (`setPosition` has no effect).
2. `savePosition()` writes the pseudo-value `(0,0)` into prefs.
3. Even a later XWayland start faithfully "restores" to the top-left — because
   `(0,0)` used to be treated as a legitimate coordinate.

### Solution

**Prefer XWayland for the app process** by setting a GDK backend fallback chain in
`main()`, before GTK/GDK initialization:

```cpp
// voice_capsule/linux/runner/main.cc
setenv("GDK_BACKEND", "x11,wayland", 0);
```

All three preconditions are mandatory:

- **It must be a fallback chain, not plain `x11`.** With plain `x11`, the moment no
  X server is reachable GTK prints `cannot open display` and exits with code 1 —
  escalating "wrong position" into "won't start at all". **Launchability outranks
  positioning correctness.**

  Probing `getenv("DISPLAY")` yourself is not enough either: it misses "DISPLAY is
  set but the X server is unreachable" (a stale `DISPLAY=:0` in a pure Wayland
  session, dead SSH X forwarding). Measured comparison:

  | Scenario | `GDK_BACKEND=x11,wayland` | plain `x11` + DISPLAY probe |
  | --- | --- | --- |
  | X available | ok, backend=x11 | ok, backend=x11 |
  | no `DISPLAY` | ok, backend=wayland | probe skips injection → wayland |
  | `DISPLAY=:99` (unreachable) | ok, backend=wayland | **gtk_init_check FAILED** |

  The chain delegates the availability decision to GDK, covers more cases, and
  removes the hand-rolled probe.

- **Never override an explicit user setting**: `overwrite=0` (shell side:
  `${GDK_BACKEND:-x11,wayland}`), preserving the escape hatch.
- **Every entry point must agree.** `.desktop`, the `nextalk-toggle.sh` cold-start
  fallback, and running the binary directly — otherwise one path always slips
  through.

⚠️ **This is a global decision**: when X is available the entire app process runs on
XWayland, so the tray icon (`system_tray` / libayatana-appindicator), Portal global
shortcuts, and fcitx5 text injection all operate under XWayland semantics. Any
change to this decision requires re-verifying those three subsystems.

**Companion safeguards for position persistence** (downstream of the same cause):

- `(0,0)` is always rejected as the Wayland pseudo-value signature, blocking stale
  dirty values from coming back to life.
- Confirm the window is visible before saving; coordinates read while hidden are
  not trustworthy.
- The Linux side of window_manager only emits `move` (from `configure-event`) and
  **never emits `moved`**, so `onWindowMoved()` is a dead callback — the save hook
  must live on `onWindowMove()` with debouncing.
- `setSize()` also triggers `configure-event`, and the WM may translate the window
  along the way (measured: a resize at `4600,1300` moved it to `4580,900`). Saving
  must be suppressed during programmatic geometry changes, otherwise the capsule
  ends up permanently misplaced after the wizard or the expanded state.

### Related Files

- `voice_capsule/linux/runner/main.cc` — GDK backend fallback chain `x11,wayland`
- `scripts/nextalk-toggle.sh` — the same fallback chain on the cold-start path
  (transitional belt-and-braces)
- `packaging/deb/com.gonewx.nextalk.desktop` — `Exec=env GDK_BACKEND=x11 ...`
- `voice_capsule/lib/services/flutter_window_backend.dart` — save/restore logic
- `voice_capsule/lib/constants/window_constants.dart` — work-area checks and
  default position
- `scripts/verify-transparent-window.sh` — regression check for the fallback chain

### Alternative Solutions (Not Adopted)

- **layer-shell / GNOME Shell extension positioning**: works on native Wayland but
  introduces a new window-positioning dependency, and the extension route depends
  on the GNOME version plus manual user enablement.
- **Dropping position memory on native Wayland**: that deletes the feature, while
  the user's actual request is "remember where I dragged it".

---

## Document Maintenance

When encountering new pitfalls, please add using this template:

```markdown
## [Problem Title]

### Problem Description
[Brief description of symptoms]

### Reproduction Scenario
[Code example or steps]

### Root Cause Analysis
[Technical analysis of the cause]

### Solution
[Adopted solution with code example]

### Related Files
[Involved source file paths]

### Alternative Solutions (Not Adopted)
[Other considered solutions]
```
