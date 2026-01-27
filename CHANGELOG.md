# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-01-26

### Changed
- Simplified `WatchPoint` node: Removed internal debug systems and complex logging.
- Integrated text display functionality directly into `WatchPoint` node (replaced Signal Scout).
- Refactored `WindowManager` for better performance while maintaining thread safety.

### Removed
- `WatchPointDebugToggle` node and associated debug logic.
- `WatchPointRestoreWindow` node (functionality cleaned up).
- `WPSignalScout` node (functionality merged).
- `nodes/` directory and utility files to reduce codebase size.

## [1.0.0] - 2026-01-24

### Added
- Initial release of ComfyUI Watch Point.
- Dual preview system: External Monitor (Tkinter) and Floating (JS).
- Signal Scout node for text debugging.
- Window minimization protection to prevent threading crashes.
- MIT License and standardized documentation.

---