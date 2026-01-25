from .watch_point import NODE_CLASS_MAPPINGS as WP_CLASS, NODE_DISPLAY_NAME_MAPPINGS as WP_DISPLAY, cleanup_all_watchpoints

# Combinamos lo básico
NODE_CLASS_MAPPINGS = {**WP_CLASS}
NODE_DISPLAY_NAME_MAPPINGS = {**WP_DISPLAY}

# Importar nodos utils de forma opcional (pueden ser desactivados si no se necesitan)
try:
    from .nodes.watchpoint_utils import NODE_CLASS_MAPPINGS as UTILS_CLASS, NODE_DISPLAY_NAME_MAPPINGS as UTILS_DISPLAY
    # Agregar los nodos utils a los mappings
    NODE_CLASS_MAPPINGS.update(UTILS_CLASS)
    NODE_DISPLAY_NAME_MAPPINGS.update(UTILS_DISPLAY)
    print("WatchPoint Utils cargados: Debug Toggle y Restore Window disponibles")
except ImportError as e:
    print(f"WatchPoint Utils no disponibles: {e}")
    pass  # Los nodos utils son opcionales, no es un error crítico

# El JS sigue siendo necesario para los botones del List Cycler
WEB_DIRECTORY = "js" 

# Exportar la función de cleanup para uso externo
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY", "cleanup_all_watchpoints"]