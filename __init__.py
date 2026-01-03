"""
ComfyUI Watch Point
Dual preview system: External monitor (Tkinter) + Floating preview (JavaScript)
"""

from .watch_point import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Indicate that we have JavaScript files
WEB_DIRECTORY = "js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

print("✅ Watch Point Extension: Loaded")
print("   👁️  Dual Preview System")
print("   📺 Monitor Preview: Tkinter window on external monitor")
print("   🖼️  Floating Preview: JavaScript floating window")
print("   ⌨️  Shortcuts: Ctrl+Alt+W (toggle floating)")
print("   📁 JavaScript extension registered")
