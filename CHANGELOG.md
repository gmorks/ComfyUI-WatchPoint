# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-01-26

### Removed
- Removed temporary WatchPointDebug node.
- Removed standalone Signal Scout node (functionality integrated into main node).
- Removed watchpoint_utils.py and watchpoint_debug_config.json.
- Removed debug-specific logging and dump features.

### Added
- Global monitor configuration via `watchpoint_settings.json` using `monitor_index`.
- Monitor selection UI inside the Tkinter settings dialog (⚙), with live window repositioning.
- Added dynamic multi-monitor fullscreen support:
    - Automatically detects the current monitor when toggling fullscreen.
    - Expands correctly to the monitor where the window is located.
    - Cross-platform detection using `ctypes` (Windows) with Tkinter fallbacks.

### Changed
- Simplified WatchPoint node structure.
- Integrated text input (formerly Signal Scout) directly into WatchPoint node.
- External monitor selection moved from the node dropdown to the global settings file.
- `monitor_preview` now controls whether the image updates, instead of creating/destroying the Tkinter window.
- Optimized WatchPointLogger for standard logging only.
- Updated documentation to reflect cleanup and new monitor configuration.

### Fixed
- Reduced `main thread is not in main loop` and `Tcl_AsyncDelete` errors by keeping a single persistent Tkinter window instance.
- Avoided dead preview threads by no longer destroying the window when `monitor_preview` is disabled.
- Ensured stable fullscreen toggling (toolbar button and F11) without losing window state.

## [1.0.0] - 2026-01-24

### Added
- Initial release of ComfyUI Watch Point.
- Dual preview system: External Monitor (Tkinter) and Floating (JS).
- Signal Scout node for text debugging.
- Window minimization protection to prevent threading crashes.
- MIT License and standardized documentation.
---
