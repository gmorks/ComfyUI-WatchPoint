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

### Changed
- Simplified WatchPoint node structure.
- Integrated text input (formerly Signal Scout) directly into WatchPoint node.
- Optimized WatchPointLogger for standard logging only.
- Updated documentation to reflect cleanup.

## [1.0.0] - 2026-01-24

### Added
- Initial release of ComfyUI Watch Point.
- Dual preview system: External Monitor (Tkinter) and Floating (JS).
- Signal Scout node for text debugging.
- Window minimization protection to prevent threading crashes.
- MIT License and standardized documentation.

---