from .watch_point import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS, cleanup_all_watchpoints

# JS is needed for the floating preview functionality
WEB_DIRECTORY = "js" 

# Export the cleanup function for external use
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY", "cleanup_all_watchpoints"]
