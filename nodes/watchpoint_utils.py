import json
import os
from server import PromptServer
from aiohttp import web
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from watch_point import wp_logger, window_manager
except ImportError:
    wp_logger = None
    window_manager = None

DEBUG = True

# --- WatchPoint Debug Toggle Node ---
class WatchPointDebugToggle:
    """Simple node to enable/disable persistent debug mode - One click!"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "debug_activado": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    FUNCTION = "toggle_debug"
    CATEGORY = "WatchPoint/Utils"
    
    def toggle_debug(self, debug_activado):
        if wp_logger:
            wp_logger.set_debug_mode(debug_activado)
        if debug_activado:
            return ("✅ Persistent Debug ACTIVATED\n💾 Dumps will be saved automatically on each execution",)
        else:
            return ("⚪ Persistent Debug DEACTIVATED\n📝 Dumps will be saved manually",)

# --- WatchPoint Restore Window Node ---
class WatchPointRestoreWindow:
    """Node to restore minimized windows - Recover your hidden windows!"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "display_idx": ("INT", {"default": 0, "min": 0, "max": 10}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    FUNCTION = "restore_window"
    CATEGORY = "WatchPoint/Utils"
    
    def restore_window(self, display_idx):
        if window_manager and hasattr(window_manager, 'restore_window'):
            success = window_manager.restore_window(display_idx)
            if success:
                return (f"✅ Window {display_idx} restored successfully\n🪟 Window came back to life!",)
            else:
                return (f"❌ Could not restore window {display_idx}\n📝 Check that it exists and is minimized",)
        else:
            return (f"⚠️ WindowManager not available\n📝 Cannot restore window",)

NODE_CLASS_MAPPINGS = {
    "WatchPointDebugToggle": WatchPointDebugToggle,
    "WatchPointRestoreWindow": WatchPointRestoreWindow,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WatchPointDebugToggle": "🔨 WatchPoint Debug Toggle",
    "WatchPointRestoreWindow": "🪟 WatchPoint Restore Window",
}