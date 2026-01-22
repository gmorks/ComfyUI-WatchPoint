from .watch_point import NODE_CLASS_MAPPINGS as WP_CLASS, NODE_DISPLAY_NAME_MAPPINGS as WP_DISPLAY
from .nodes.list_cycler import NODE_CLASS_MAPPINGS as LC_CLASS, NODE_DISPLAY_NAME_MAPPINGS as LC_DISPLAY

# Combinamos solo lo necesario
NODE_CLASS_MAPPINGS = {**WP_CLASS, **LC_CLASS}
NODE_DISPLAY_NAME_MAPPINGS = {**WP_DISPLAY, **LC_DISPLAY}

# El JS sigue siendo necesario para los botones del List Cycler
WEB_DIRECTORY = "js" 

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]