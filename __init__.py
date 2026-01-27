from .watch_point import NODE_CLASS_MAPPINGS as WP_CLASS, NODE_DISPLAY_NAME_MAPPINGS as WP_DISPLAY, cleanup_all_watchpoints

# Merge node mappings
NODE_CLASS_MAPPINGS = {**WP_CLASS}
NODE_DISPLAY_NAME_MAPPINGS = {**WP_DISPLAY}

# JS directory for floating preview functionality
WEB_DIRECTORY = "js" 

# Export symbols
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY", "cleanup_all_watchpoints"]