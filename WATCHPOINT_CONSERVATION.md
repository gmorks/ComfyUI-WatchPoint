# 🛡️ WatchPoint Conservation Guide

## 📋 Document Purpose
This document serves as a "contra PRD" - a conservation guide for maintaining WatchPoint functionality while allowing future modifications. It outlines what MUST be preserved, what can be modified, and critical implementation details.

## 🔒 CRITICAL: Must Preserve

### Core Stability Features
1. **Window Minimization Protection**
   - `safe_close()` function in `watch_point.py`
   - Prevents accidental window closure from crashing ComfyUI
   - Uses `iconify()` as primary method, `withdraw()` as fallback
   - Updates window state tracking (`minimized`, `running` flags)

2. **Thread Safety**
   - All Tkinter operations must run on main thread
   - Use `self.window_manager.master.after()` for thread-safe GUI updates
   - Prevents `Tcl_AsyncDelete` crashes

3. **Debug Mode Persistence**
   - `watchpoint_debug_config.json` file-based configuration
   - `load_debug_config()` and `save_debug_config()` functions
   - Debug state survives ComfyUI restarts

4. **Recursion Prevention**
   - `_saving_dump` flag in `save_debug_dump()`
   - Prevents infinite loops during debug dump saving

### File Structure
```
ComfyUI-WatchPoint/
├── watch_point.py              # Core functionality (preserve stability features)
├── __init__.py                 # Optional utility imports (modify carefully)
├── watchpoint_debug_config.json # Debug persistence (auto-generated)
├── watchpoint_settings.json    # User settings (auto-generated)
├── nodes/
│   ├── __init__.py            # Node package init
│   ├── list_cycler.py         # Template for utility nodes
│   └── watchpoint_utils.py    # Optional utility nodes (safe to modify)
└── WATCHPOINT_CONSERVATION.md  # This file
```

## 📝 Implementation Rules

### When Adding New Features
1. **Utility Nodes**: Add to `nodes/watchpoint_utils.py`, not `watch_point.py`
2. **Core Modifications**: Only modify `watch_point.py` for critical fixes
3. **Optional Imports**: Use try/except blocks in `__init__.py`
4. **State Management**: Use file-based persistence for critical state

### Window Management
```python
# Correct pattern for window operations
def safe_window_operation(self, display_idx, operation):
    try:
        self.window_manager.master.after(0, lambda: self._perform_operation(display_idx, operation))
    except Exception as e:
        wp_logger.warning(f"Window operation failed: {e}", "WindowManager")
```

### Debug Mode Handling
```python
# Always check debug state before operations
if self.debug_mode or load_debug_config().get("debug_enabled", False):
    # Perform debug operations
    pass
```

## 🔄 Utility Node Management

### Enabling/Disabling Utilities
Located in `__init__.py`:
```python
try:
    from .nodes.watchpoint_utils import NODE_CLASS_MAPPINGS as UTILS_CLASS, NODE_DISPLAY_NAME_MAPPINGS as UTILS_DISPLAY
    NODE_CLASS_MAPPINGS.update(UTILS_CLASS)
    NODE_DISPLAY_NAME_MAPPINGS.update(UTILS_DISPLAY)
    print("WatchPoint Utils loaded: Debug Toggle and Restore Window available")
except ImportError as e:
    print(f"WatchPoint Utils not available: {e}")
    pass
```

### Safe Modifications
- ✅ Add new utility nodes to `watchpoint_utils.py`
- ✅ Modify utility node functionality
- ✅ Add new optional features
- ❌ Remove core stability features from `watch_point.py`
- ❌ Modify thread safety mechanisms
- ❌ Remove file-based state management

## 🚨 Common Pitfalls to Avoid

1. **Don't Create Direct Tkinter Windows**
   ```python
   # ❌ WRONG - Causes thread issues
   window = tk.Toplevel()
   
   # ✅ CORRECT - Use existing window manager
   self.window_manager.create_window(...)
   ```

2. **Don't Skip Error Handling**
   ```python
   # ❌ WRONG - No error handling
   root.protocol("WM_DELETE_WINDOW", root.iconify)
   
   # ✅ CORRECT - With error handling
   def safe_close():
       try:
           root.iconify()
       except:
           root.withdraw()
   root.protocol("WM_DELETE_WINDOW", safe_close)
   ```

3. **Don't Forget State Persistence**
   ```python
   # ❌ WRONG - State lost on restart
   self.debug_mode = True
   
   # ✅ CORRECT - Persistent state
   save_debug_config({"debug_enabled": True})
   ```

## 🔧 Testing Checklist

Before committing changes:
- [ ] Test window minimization (click X button)
- [ ] Test debug mode persistence (restart ComfyUI)
- [ ] Test with utility nodes enabled/disabled
- [ ] Test multi-monitor setup
- [ ] Check for `Tcl_AsyncDelete` errors
- [ ] Verify no infinite recursion in debug dumps

## 📚 Key Functions Reference

### Window Management
- `safe_close()` - Window close protection
- `window_manager.create_window()` - Safe window creation
- `window_manager.restore_window()` - Window restoration

### Debug System
- `load_debug_config()` - Load persistent debug state
- `save_debug_config()` - Save debug state
- `save_debug_dump()` - Safe debug dump (with recursion protection)

### State Management
- File: `watchpoint_debug_config.json`
- Keys: `debug_enabled`, `debug_data`
- Auto-created on first use

## 🎯 Philosophy

**Conservative Approach**: This project prioritizes stability over features. Every new feature must:
1. Not compromise core stability
2. Be optional when possible
3. Include proper error handling
4. Maintain backward compatibility

**Modular Design**: Separate core functionality from utilities to allow safe experimentation without risking core stability.

---

*Last Updated: 2026-01-23*
*Version: 1.0*
*Purpose: Preserve WatchPoint stability while enabling safe evolution*