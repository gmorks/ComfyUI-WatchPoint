from .watch_point import NODE_CLASS_MAPPINGS as WP_CLASS, NODE_DISPLAY_NAME_MAPPINGS as WP_DISPLAY, cleanup_all_watchpoints

# Combine the basics
NODE_CLASS_MAPPINGS = {**WP_CLASS}
NODE_DISPLAY_NAME_MAPPINGS = {**WP_DISPLAY}

# Import utility nodes optionally (can be disabled if not needed)
try:
    from .nodes.watchpoint_utils import NODE_CLASS_MAPPINGS as UTILS_CLASS, NODE_DISPLAY_NAME_MAPPINGS as UTILS_DISPLAY
    # Add utility nodes to the mappings
    NODE_CLASS_MAPPINGS.update(UTILS_CLASS)
    NODE_DISPLAY_NAME_MAPPINGS.update(UTILS_DISPLAY)
    print("WatchPoint Utils loaded: Debug Toggle and Restore Window available")
except ImportError as e:
    print(f"WatchPoint Utils not available: {e}")
    pass  # Utility nodes are optional, not a critical error

# JS is needed for the floating preview functionality
WEB_DIRECTORY = "js" 

# Export the cleanup function for external use
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY", "cleanup_all_watchpoints"]