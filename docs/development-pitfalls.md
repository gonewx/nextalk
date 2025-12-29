# Development Pitfalls Record

[简体中文](development-pitfalls_zh.md) | English

This document records technical issues encountered during Nextalk development, root cause analysis, and solutions for future maintenance reference.

---

## Table of Contents

- [Flutter system_tray Library Linux Checkbox State Bug](#flutter-system_tray-library-linux-checkbox-state-bug)

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
