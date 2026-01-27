from .watch_point import NODE_CLASS_MAPPINGS as WP_CLASS, NODE_DISPLAY_NAME_MAPPINGS as WP_DISPLAY, cleanup_all_watchpoints

# Combine the basics
NODE_CLASS_MAPPINGS = {**WP_CLASS}
NODE_DISPLAY_NAME_MAPPINGS = {**WP_DISPLAY}

# JS is needed for the floating preview functionality
WEB_DIRECTORY = "js" 

# Export the cleanup function for external use
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY", "cleanup_all_watchpoints"]