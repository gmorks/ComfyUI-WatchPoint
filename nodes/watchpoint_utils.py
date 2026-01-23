import json
import os
from server import PromptServer
from aiohttp import web

# Importar el logger global de watch_point
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
    """Nodo simple para activar/desactivar debug persistente - ¡Solo un click!"""
    
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
            return ("✅ Debug persistente ACTIVADO\n💾 Se guardarán dumps automáticamente en cada ejecución",)
        else:
            return ("⚪ Debug persistente DESACTIVADO\n📝 Los dumps se guardarán manualmente",)

# --- WatchPoint Restore Window Node ---
class WatchPointRestoreWindow:
    """Nodo para restaurar ventanas minimizadas - ¡Recupera tus ventanas escondidas!"""
    
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
                return (f"✅ Ventana {display_idx} restaurada exitosamente\n🪟 La ventana volvió a la vida!",)
            else:
                return (f"❌ No se pudo restaurar ventana {display_idx}\n📝 Verifica que exista y esté minimizada",)
        else:
            return (f"⚠️ WindowManager no disponible\n📝 No se puede restaurar la ventana",)

NODE_CLASS_MAPPINGS = {
    "WatchPointDebugToggle": WatchPointDebugToggle,
    "WatchPointRestoreWindow": WatchPointRestoreWindow,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WatchPointDebugToggle": "🔨 WatchPoint Debug Toggle",
    "WatchPointRestoreWindow": "🪟 WatchPoint Restore Window",
}