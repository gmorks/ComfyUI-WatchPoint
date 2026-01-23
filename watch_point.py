import os
import json
import sys  # NUEVO: Importar sys para debug dumps
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
from threading import Thread, Lock
import folder_paths
import io
import time
import threading

# --- Global Shutdown Registry ---
class ShutdownRegistry:
    """Registro global para manejar shutdown sin atexit"""
    _instance = None
    _nodes = []
    _shutdown_called = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ShutdownRegistry, cls).__new__(cls)
        return cls._instance
    
    def register(self, node):
        """Registrar un nodo para cleanup"""
        if not self._shutdown_called:
            self._nodes.append(node)
    
    def shutdown_all(self):
        """Shutdown todos los nodos registrados"""
        if self._shutdown_called:
            return
        self._shutdown_called = True
        
        wp_logger.info(f"Limpiando {len(self._nodes)} nodos...", "ShutdownRegistry")
        for node in self._nodes[:]:
            try:
                if hasattr(node, 'cleanup'):
                    node.cleanup()
            except Exception as e:
                wp_logger.error(f"Error en cleanup: {e}", "ShutdownRegistry")
        self._nodes.clear()

# Crear instancia global
shutdown_registry = ShutdownRegistry()

# --- Logging Estructurado ---
class WatchPointLogger:
    """Sistema de logging estructurado para WatchPoint"""
    
    def __init__(self):
        self.enabled = True
        self.log_level = "INFO"  # DEBUG, INFO, WARNING, ERROR
        self.logs = []
        self.max_logs = 100
        self.debug_mode = False  # NUEVO: Modo debug
        self.debug_log_dir = "debug_logs"  # NUEVO: Directorio para logs de debug
        self.debug_session_id = None  # NUEVO: ID única para sesión de debug
        self.config_file = os.path.join(os.path.dirname(__file__), "watchpoint_debug_config.json")
        self.load_debug_config()  # Cargar configuración persistente
    
    def log(self, level, message, component="WatchPoint"):
        """Log un mensaje con nivel y componente"""
        if not self.enabled:
            return
        
        # Verificar nivel de log
        levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        if levels.get(level, 1) < levels.get(self.log_level, 1):
            return
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "component": component,
            "message": message
        }
        
        self.logs.append(log_entry)
        
        # Mantener solo los últimos logs
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
        
        # Imprimir siempre errores
        if level == "ERROR":
            print(f"WatchPoint [{timestamp}] {level}: {message}")
        elif level == "WARNING":
            print(f"WatchPoint [{timestamp}] {level}: {message}")
    
    def debug(self, message, component="WatchPoint"):
        self.log("DEBUG", message, component)
    
    def info(self, message, component="WatchPoint"):
        self.log("INFO", message, component)
    
    def warning(self, message, component="WatchPoint"):
        self.log("WARNING", message, component)
    
    def error(self, message, component="WatchPoint"):
        self.log("ERROR", message, component)
    
    def get_logs(self, level=None, component=None):
        """Obtener logs filtrados por nivel y componente"""
        filtered_logs = self.logs
        
        if level:
            filtered_logs = [log for log in filtered_logs if log["level"] == level]
        
        if component:
            filtered_logs = [log for log in filtered_logs if log["component"] == component]
        
        return filtered_logs
    
    def clear_logs(self):
        """Limpiar todos los logs"""
        self.logs = []
    
    def set_debug_mode(self, enabled=True):
        """Activar/desactivar modo debug"""
        self.debug_mode = enabled
        if enabled:
            self.debug_session_id = time.strftime("%Y%m%d_%H%M%S")
            # Crear directorio de debug si no existe
            os.makedirs(self.debug_log_dir, exist_ok=True)
            self.info(f"Modo debug activado - Sesión: {self.debug_session_id}", "Debug")
        else:
            self.info("Modo debug desactivado", "Debug")
        
        # Guardar configuración persistente
        self.save_debug_config()
    
    def load_debug_config(self):
        """Cargar configuración de debug desde archivo"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.debug_mode = config.get('debug_mode', False)
                    if self.debug_mode:
                        self.debug_session_id = time.strftime("%Y%m%d_%H%M%S")
                        self.info(f"Modo debug persistente activado - Sesión: {self.debug_session_id}", "Debug")
        except Exception as e:
            self.error(f"Error cargando config de debug: {e}", "Debug")
    
    def save_debug_config(self):
        """Guardar configuración de debug a archivo"""
        try:
            config = {
                'debug_mode': self.debug_mode,
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.error(f"Error guardando config de debug: {e}", "Debug")
    
    def save_debug_dump(self, watch_point_instance=None):
        """Guardar dump completo de debug con stats, threads y logs"""
        if not self.debug_mode:
            return
        
        # Prevenir recursión infinita
        if hasattr(self, '_saving_dump') and self._saving_dump:
            return None
        
        try:
            self._saving_dump = True
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"debug_dump_{self.debug_session_id}_{timestamp}.log"
            filepath = os.path.join(self.debug_log_dir, filename)
            
            debug_data = {
                "timestamp": timestamp,
                "session_id": self.debug_session_id,
                "system_info": {
                    "python_version": sys.version,
                    "platform": sys.platform,
                    "threading_active": threading.active_count()
                }
            }
            
            # Agregar stats del WatchPoint si está disponible
            if watch_point_instance and hasattr(watch_point_instance, 'get_health_stats'):
                debug_data["health_stats"] = watch_point_instance.get_health_stats()
            
            # Agregar info de threads SI ESTÁ DISPONIBLE Y NO ESTAMOS EN RECURSIÓN
            if watch_point_instance and hasattr(watch_point_instance, 'debug_threads'):
                # Llamar directamente a la función sin pasar por el logger para evitar recursión
                debug_data["thread_info"] = watch_point_instance.debug_threads()
            
            # Agregar logs recientes
            debug_data["recent_logs"] = self.get_logs()[-50:]  # Últimos 50 logs
            
            # Guardar a archivo
            with open(filepath, 'w', encoding='utf-8') as f:
                import json
                json.dump(debug_data, f, indent=2, default=str)
            
            self.info(f"Debug dump guardado: {filename}", "Debug")
            return filepath
            
        except Exception as e:
            self.error(f"Error guardando debug dump: {e}", "Debug")
            return None
        finally:
            # Limpiar bandera de recursión
            self._saving_dump = False

# Crear logger global
wp_logger = WatchPointLogger()

try:
    import win32clipboard
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


try:
    from screeninfo import get_monitors
    SCREENINFO_AVAILABLE = True
except ImportError:
    SCREENINFO_AVAILABLE = False

# --- Settings Management ---
class SettingsManager:
    """Handles loading and saving of settings to a JSON file."""
    def __init__(self, settings_file):
        self.filepath = settings_file
        self.defaults = {
            "window_width": 800, "window_height": 600,
            "window_x": None, "window_y": None,
            "window_size_mode": "fixed",
            "show_toolbar": True, "save_format": "png", "jpeg_quality": 90,
        }
        self.settings = self.load()

    def load(self):
        """Loads settings from the file, merging with defaults."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r') as f:
                    return {**self.defaults, **json.load(f)}
        except Exception as e:
            print(f"Watch Point: Error loading settings, using defaults. Error: {e}")
        return self.defaults.copy()

    def save(self):
        """Saves the current settings to the file."""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Watch Point: Could not save settings. Error: {e}")

    def get(self, key, default=None):
        """Gets a setting value by key."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Sets a setting value."""
        self.settings[key] = value

# --- Window Management ---
class WindowManager:
    """Manages the lifecycle and state of all Tkinter preview windows."""
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(WindowManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, settings_manager=None):
        if not hasattr(self, 'initialized'):
            self.windows = {}
            self.settings_manager = settings_manager or SettingsManager(
                os.path.join(os.path.dirname(__file__), "watchpoint_settings.json")
            )
            self.shutdown_event = threading.Event()
            self._start_time = time.time()  # Tiempo de inicio para estadísticas
            self.initialized = True
            
            # Iniciar watchdog
            self.watchdog_thread = Thread(target=self._watchdog_loop, daemon=True)
            self.watchdog_thread.start()
            
            wp_logger.info("WindowManager inicializado", "WindowManager")

    def show_image(self, display_idx, pil_img, text=None):
        """Creates or updates a window to display an image and optional text."""
        if display_idx in self.windows:
            win_data = self.windows[display_idx]
            if not win_data.get("running", False):
                self._cleanup_window(display_idx)
            else:
                with win_data["lock"]:
                    win_data["image"] = pil_img
                if text and win_data.get("instance"):
                    win_data["instance"].update_signal_text(text)
                return

        lock = Lock()
        win_data = {
            "image": pil_img, "lock": lock, "running": True,
            "instance": None, "pending_text": text,
            "minimized": False  # NUEVO: Estado de minimización
        }
        self.windows[display_idx] = win_data
        
        thread = Thread(target=self._window_loop, args=(display_idx,), daemon=True)
        win_data["thread"] = thread
        thread.start()

    def hide_window(self, display_idx):
        """Signals a window to close with timeout garantizado."""
        if display_idx in self.windows:
            self.windows[display_idx]["running"] = False
            self.windows[display_idx]["closing"] = True
            self.windows[display_idx]["close_started"] = time.time()
            
            # MEJORADO: Esperar hasta 3 segundos con timeout
            try:
                thread = self.windows[display_idx].get("thread")
                if thread and thread.is_alive():
                    thread.join(timeout=3.0)
                    wp_logger.debug(f"Thread {display_idx} finalizado correctamente", "HideWindow")
            except Exception as e:
                wp_logger.error(f"Error esperando thread {display_idx}: {e}", "HideWindow")
            
            # Forzar cleanup si sigue vivo
            if display_idx in self.windows and self.windows[display_idx].get("thread", {}).is_alive():
                wp_logger.warning(f"Forzando cleanup para ventana {display_idx}", "HideWindow")
                self._force_cleanup_window(display_idx)

    def update_all_text(self, text):
        """Updates the text in all currently open windows."""
        for win_data in self.windows.values():
            if win_data.get("running") and win_data.get("instance"):
                win_data["instance"].update_signal_text(text)

    def _window_loop(self, display_idx):
        """The main loop for a Tkinter window thread with robust error handling."""
        root = None
        win_instance = None
        try:
            # === CÓDIGO EXISTENTE SE MANTIENE IGUAL ===
            root = tk.Tk()
            root.title(f"Watch Point - Monitor {display_idx}")
            
            self._apply_icon(root)
            self._apply_geometry(root, display_idx)

            win_instance = WatchPointWindow(root, display_idx, self)
            self.windows[display_idx]["instance"] = win_instance
            
            # NUEVO: Handler de cierre que minimiza en lugar de cerrar - ¡Protección anti-cierre accidental!
            def safe_close():
                # En lugar de cerrar, ¡MINIMIZAMOS la ventana a la barra de tareas!
                try:
                    root.iconify()  # Minimizar a barra de tareas
                    # Actualizar estado: la ventana sigue viva pero minimizada
                    self.windows[display_idx]["minimized"] = True
                    self.windows[display_idx]["running"] = True  # Sigue ejecutándose
                    wp_logger.info(f"Ventana {display_idx} minimizada (protegida de cierre accidental)", "WindowLoop")
                except Exception as e:
                    wp_logger.warning(f"Error minimizando ventana {display_idx}: {e}", "WindowLoop")
                    # Fallback: si no puede minimizar, intentar ocultar
                    try:
                        root.withdraw()
                        self.windows[display_idx]["minimized"] = True
                        wp_logger.info(f"Ventana {display_idx} oculta como fallback", "WindowLoop")
                    except:
                        pass
            
            root.protocol("WM_DELETE_WINDOW", safe_close)
            # === FIN CÓDIGO EXISTENTE ===
            
            # MEJORADO: Mejor manejo de excepciones de mainloop
            try:
                root.mainloop()
            except RuntimeError as e:
                # RuntimeError común al cerrar: "main thread is not in main loop"
                if "main thread" not in str(e):
                    wp_logger.error(f"RuntimeError en mainloop: {e}", "WindowLoop")
                    # Trigger debug dump en error crítico
                    if wp_logger.debug_mode:
                        wp_logger.save_debug_dump()
                    raise
                else:
                    wp_logger.debug(f"RuntimeError esperado en mainloop: {e}", "WindowLoop")
                    # Trigger debug dump en error de thread (Tcl_AsyncDelete)
                    if wp_logger.debug_mode and ("Tcl_AsyncDelete" in str(e) or "async handler" in str(e)):
                        wp_logger.save_debug_dump()
            except Exception as e:
                wp_logger.error(f"Error en mainloop de Tkinter: {e}", "WindowLoop")
        
        except Exception as e:
            wp_logger.error(f"Error en ventana {display_idx}: {e}", "WindowLoop")
            # Trigger debug dump en error crítico de ventana
            if wp_logger.debug_mode:
                wp_logger.save_debug_dump()
        
        finally:
            # MEJORADO: Cleanup con múltiples intentos y limpieza de Tkinter
            # CRÍTICO: Solo el hilo principal puede tocar recursos Tkinter
            import threading
            current_thread = threading.current_thread()
            
            for attempt in range(3):
                try:
                    # PROTECCIÓN TCL: Solo limpiar Tkinter si estamos en el hilo principal
                    if current_thread.name == "MainThread":
                        # Limpiar recursos de Tkinter primero
                        if win_instance:
                            try:
                                win_instance.cleanup_tkinter_resources()
                            except Exception as e:
                                wp_logger.warning(f"Error limpiando recursos Tkinter: {e}", "WindowLoop")
                        
                        if root:
                            try:
                                root.quit()
                            except:
                                pass
                            try:
                                root.destroy()
                            except:
                                pass
                    else:
                        # Si no estamos en el hilo principal, solo loggear y saltar Tkinter
                        wp_logger.warning(f"Skipping Tkinter cleanup desde hilo {current_thread.name} - protección Tcl_AsyncDelete", "WindowLoop")
                    
                    self._cleanup_window(display_idx)
                    break
                except Exception as e:
                    if attempt == 2:
                        wp_logger.error(f"Cleanup falló después de 3 intentos: {e}", "WindowLoop")
                    time.sleep(0.05)

    def restore_window(self, display_idx):
        """Restaura una ventana minimizada - ¡Para recuperarla desde la barra de tareas!"""
        if display_idx in self.windows:
            win_data = self.windows[display_idx]
            
            # Verificar si está minimizada
            if not win_data.get("minimized", False):
                wp_logger.debug(f"Ventana {display_idx} no está minimizada", "RestoreWindow")
                return False
            
            instance = win_data.get("instance")
            if not instance:
                wp_logger.warning(f"No se puede restaurar ventana {display_idx}: instancia no válida", "RestoreWindow")
                return False
            
            try:
                # Restaurar la ventana usando el root de la instancia
                if hasattr(instance, 'root') and instance.root:
                    instance.root.deiconify()  # Hacer visible de nuevo
                    instance.root.lift()  # Traer al frente
                    instance.root.focus_force()  # Dar foco
                    
                    # Actualizar estado
                    win_data["minimized"] = False
                    wp_logger.info(f"Ventana {display_idx} restaurada exitosamente", "RestoreWindow")
                return True
                
            except Exception as e:
                wp_logger.error(f"Error restaurando ventana {display_idx}: {e}", "RestoreWindow")
                return False
        else:
            wp_logger.warning(f"Ventana {display_idx} no existe", "RestoreWindow")
            return False

    def _apply_icon(self, root):
        """Applies the icon from a file to the window."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, "preview_monitor_icon.png")
            if os.path.exists(icon_path):
                icon_img = tk.PhotoImage(file=icon_path)
                root.iconphoto(True, icon_img)
        except tk.TclError:
            print("Watch Point: Could not apply icon. Ensure it's a valid PNG/GIF.")

    def _apply_geometry(self, root, display_idx):
        """Calculates and applies the window's initial size and position."""
        size_mode = self.settings_manager.get("window_size_mode")
        width = self.settings_manager.get("window_width")
        height = self.settings_manager.get("window_height")
        
        geom_str = self.calculate_geometry_string(root, size_mode, width, height)
        if geom_str:
            root.geometry(geom_str)

        # Prioritize monitor selection, then fallback to saved position
        position_set = False
        if SCREENINFO_AVAILABLE:
            try:
                m = get_monitors()[display_idx]
                root.geometry(f"+{m.x + 50}+{m.y + 50}")
                position_set = True
            except IndexError:
                print(f"Watch Point: Monitor index {display_idx} is out of range. Falling back.")

        if not position_set and self.settings_manager.get("use_last_known_position", False):
            x = self.settings_manager.get("window_x")
            y = self.settings_manager.get("window_y")
            if x is not None and y is not None:
                root.geometry(f"+{x}+{y}")

    def calculate_geometry_string(self, root, size_mode, default_w, default_h):
        """Returns a geometry string (e.g., '800x600') based on the size mode."""
        try:
            if size_mode in ["Half Vertical", "Half Horizontal", "Quarter"]:
                screen_w = root.winfo_screenwidth()
                screen_h = root.winfo_screenheight()
                if size_mode == "Half Vertical":
                    return f"{screen_w // 2}x{screen_h - 100}"
                if size_mode == "Half Horizontal":
                    return f"{screen_w}x{screen_h // 2 - 50}"
                if size_mode == "Quarter":
                    return f"{screen_w // 2}x{screen_h // 2}"
            elif 'x' in str(size_mode): # Handles "800x600" etc.
                return size_mode
        except Exception as e:
            print(f"Watch Point: Error calculating geometry: {e}")
        
        return f"{default_w}x{default_h}"

    def _cleanup_window(self, display_idx):
        """Ensures a window and its resources are properly removed with múltiples intentos."""
        if display_idx in self.windows:
            import threading
            current_thread = threading.current_thread()
            
            for attempt in range(3):
                try:
                    win_data = self.windows[display_idx]
                    
                    # PROTECCIÓN THREAD: Solo intentar join si el thread actual NO es el thread de la ventana
                    if "thread" in win_data and win_data["thread"].is_alive():
                        # Verificar que no estemos intentando hacer join a nosotros mismos
                        if win_data["thread"] != current_thread:
                            try:
                                win_data["thread"].join(timeout=0.1)
                            except Exception: 
                                pass
                        else:
                            wp_logger.warning(f"Evitando auto-join en cleanup para ventana {display_idx}", "Cleanup")
                    
                    # Eliminar de la lista SIEMPRE, incluso si hay errores
                    try:
                        del self.windows[display_idx]
                    except KeyError:
                        # Ya fue eliminado, no es error
                        pass
                    
                    wp_logger.debug(f"Cleanup exitoso para ventana {display_idx} (intento {attempt + 1})", "Cleanup")
                    break
                except Exception as e:
                    if attempt == 2:
                        wp_logger.error(f"Cleanup falló después de 3 intentos: {e}", "Cleanup")
                    time.sleep(0.05)

    def _watchdog_loop(self):
        """Monitorea y limpia threads muertos cada segundo"""
        wp_logger.info("Watchdog iniciado", "Watchdog")
        
        while not self.shutdown_event.is_set():
            time.sleep(1.0)
            
            dead_windows = []
            for display_idx, win_data in list(self.windows.items()):
                # Detectar threads que murieron sin cleanup
                if "thread" in win_data:
                    if not win_data["thread"].is_alive():
                        dead_windows.append(display_idx)
                        wp_logger.warning(f"Thread muerto detectado para ventana {display_idx}", "Watchdog")
                    # Detectar ventanas que llevan mucho tiempo cerrándose
                    elif win_data.get("closing") and win_data.get("close_started"):
                        if time.time() - win_data["close_started"] > 5.0:
                            # Forzar cleanup después de 5 segundos
                            dead_windows.append(display_idx)
                            wp_logger.warning(f"Ventana {display_idx} tardando demasiado en cerrar", "Watchdog")
            
            # Limpiar ventanas muertas
            for idx in dead_windows:
                wp_logger.info(f"Limpiando ventana muerta {idx}", "Watchdog")
                self._force_cleanup_window(idx)
        
        wp_logger.info("Watchdog finalizado", "Watchdog")

    def _force_cleanup_window(self, display_idx):
        """Cleanup forzado sin esperar al thread"""
        if display_idx in self.windows:
            try:
                # No intentar join, solo eliminar
                del self.windows[display_idx]
                wp_logger.debug(f"Force cleanup exitoso para ventana {display_idx}", "Cleanup")
            except Exception as e:
                wp_logger.error(f"Error en force cleanup: {e}", "Cleanup")

    def get_health_stats(self):
        """Obtener estadísticas de salud del sistema"""
        stats = {
            "total_windows_created": len(self.windows),
            "active_windows": len([w for w in self.windows.values() if w.get("running", False)]),
            "closing_windows": len([w for w in self.windows.values() if w.get("closing", False)]),
            "threads_alive": len([w for w in self.windows.values() if w.get("thread") and w["thread"].is_alive()]),
            "watchdog_status": "running" if hasattr(self, 'watchdog_thread') and self.watchdog_thread.is_alive() else "stopped",
            "shutdown_event": self.shutdown_event.is_set(),
            "uptime": time.time() - getattr(self, '_start_time', time.time())
        }
        
        # Agregar información de threads
        import threading
        stats["total_threads"] = threading.active_count()
        
        return stats
        """Shutdown global del WindowManager sin usar atexit"""
        wp_logger.info("Iniciando shutdown global...", "WindowManager")
        self.shutdown_event.set()
        
        # Cerrar todas las ventanas activas
        for display_idx in list(self.windows.keys()):
            try:
                self.hide_window(display_idx)
            except Exception as e:
                wp_logger.error(f"Error cerrando ventana {display_idx}: {e}", "WindowManager")
        
        # Esperar al watchdog
        try:
            if hasattr(self, 'watchdog_thread') and self.watchdog_thread.is_alive():
                self.watchdog_thread.join(timeout=2.0)
        except Exception as e:
            wp_logger.error(f"Error esperando watchdog: {e}", "WindowManager")
        
        wp_logger.info("Shutdown completado", "WindowManager")

# --- Global Window Manager Instance ---
# Instancia global para que los nodos puedan acceder al WindowManager
window_manager = WindowManager()

# --- Main ComfyUI Node ---
class WatchPoint:
    """The main ComfyUI node class."""
    def __init__(self):
        self.window_manager = window_manager  # Usar la instancia global
        self.last_display_idx = -1
        
        # Registrar en el registro global para cleanup
        shutdown_registry.register(self)

    @classmethod
    def INPUT_TYPES(cls):
        monitors = ["Monitor 0 (Default)"]
        if SCREENINFO_AVAILABLE:
            try:
                monitors = [f"Monitor {i} ({m.width}x{m.height})" for i, m in enumerate(get_monitors())]
            except Exception: pass
        return {
            "required": {
                "images": ("IMAGE",),
                "floating_preview": ("BOOLEAN", {"default": True}),
                "monitor_preview": ("BOOLEAN", {"default": True}),
                "monitor": (monitors, {"default": monitors[0]}),
            },
            "optional": {"opt_signal_text": ("STRING", {"forceInput": True, "multiline": True})}
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "watch"
    OUTPUT_NODE = True
    CATEGORY = "WatchPoint"

    def watch(self, images, floating_preview=True, monitor_preview=True, monitor="Monitor 0", opt_signal_text=None):
        try:
            display_idx = int(monitor.split(" ")[1])
        except (ValueError, IndexError):
            display_idx = 0

        # Close the previous window if the monitor has changed
        if self.last_display_idx != -1 and self.last_display_idx != display_idx:
            wp_logger.info(f"Cambiando de monitor {self.last_display_idx} a {display_idx}", "WatchPoint")
            self.window_manager.hide_window(self.last_display_idx)

        self.last_display_idx = display_idx

        if monitor_preview:
            wp_logger.debug(f"Mostrando preview en monitor {display_idx}", "WatchPoint")
            image = 255.0 * images[0].cpu().numpy()
            pil_img = Image.fromarray(np.clip(image, 0, 255).astype(np.uint8))
            self.window_manager.show_image(display_idx, pil_img, opt_signal_text)
        else:
            wp_logger.debug(f"Ocultando preview en monitor {display_idx}", "WatchPoint")
            self.window_manager.hide_window(display_idx)

        ui_images = self._prepare_preview(images) if floating_preview else []
        
        # NUEVO: Guardar dump automáticamente si debug está activado
        if wp_logger.debug_mode:
            wp_logger.info("Guardando dump automático - WatchPoint ejecutado", "WatchPoint")
            wp_logger.save_debug_dump(self)
        
        return {"ui": {"images": ui_images}, "result": (images,)}

    def _prepare_preview(self, images):
        """Creates temporary files for ComfyUI's floating preview."""
        import time
        output_dir = folder_paths.get_temp_directory()
        results = []
        for i, tensor in enumerate(images):
            array = 255.0 * tensor.cpu().numpy()
            img = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
            ts = int(time.time() * 1000)
            filename = f"watchpoint_{ts}_{i}.png"
            img.save(os.path.join(output_dir, filename), compress_level=4)
            results.append({"filename": filename, "subfolder": "", "type": "temp"})
        return results

    def cleanup(self):
        """Cleanup del nodo WatchPoint sin usar atexit"""
        if hasattr(self, 'window_manager'):
            self.window_manager.shutdown()
    
    def get_logs(self, level=None, component=None):
        """Obtener logs del sistema de logging"""
        return wp_logger.get_logs(level, component)
    
    def clear_logs(self):
        """Limpiar todos los logs"""
        wp_logger.clear_logs()
        wp_logger.info("Logs limpiados", "WatchPoint")
    
    def set_debug_mode(self, enabled=True):
        """Activar/desactivar modo debug"""
        wp_logger.set_debug_mode(enabled)
        if enabled:
            wp_logger.info("Modo debug activado para WatchPoint", "WatchPoint")
        else:
            wp_logger.info("Modo debug desactivado para WatchPoint", "WatchPoint")
    
    def save_debug_dump(self):
        """Guardar dump completo de debug"""
        filepath = wp_logger.save_debug_dump(self)
        if filepath:
            wp_logger.info(f"Debug dump guardado en: {filepath}", "WatchPoint")
        return filepath
    
    def get_health_stats(self):
        """Obtener estadísticas de salud del sistema"""
        return self.window_manager.get_health_stats()
    
    def debug_threads(self):
        """Comando de debug para inspeccionar threads"""
        import threading
        
        debug_info = {
            "total_threads": threading.active_count(),
            "threads": [],
            "window_threads": [],
            "daemon_threads": []
        }
        
        # Inspeccionar todos los threads
        for thread in threading.enumerate():
            thread_info = {
                "name": thread.name,
                "ident": thread.ident,
                "is_alive": thread.is_alive(),
                "is_daemon": thread.daemon,
                "thread_type": type(thread).__name__
            }
            
            debug_info["threads"].append(thread_info)
            
            if thread.daemon:
                debug_info["daemon_threads"].append(thread_info)
        
        # Inspeccionar threads de ventanas
        if hasattr(self, 'window_manager') and hasattr(self.window_manager, 'windows'):
            for window_id, window_data in self.window_manager.windows.items():
                if window_data.get('thread'):
                    thread = window_data['thread']
                    window_thread_info = {
                        "window_id": window_id,
                        "thread_name": thread.name,
                        "thread_ident": thread.ident,
                        "is_alive": thread.is_alive(),
                        "running": window_data.get('running', False),
                        "closing": window_data.get('closing', False)
                    }
                    debug_info["window_threads"].append(window_thread_info)
        
        # Agregar información del watchdog
        if hasattr(self.window_manager, 'watchdog_thread'):
            watchdog = self.window_manager.watchdog_thread
            debug_info["watchdog"] = {
                "name": watchdog.name,
                "ident": watchdog.ident,
                "is_alive": watchdog.is_alive(),
                "is_daemon": watchdog.daemon
            }
        
        wp_logger.info(f"Debug threads ejecutado: {debug_info['total_threads']} threads activos", "WatchPoint")
        return debug_info

# --- Tkinter UI Classes ---
class WatchPointWindow:
    """The main UI for a preview window."""
    def __init__(self, root, display_idx, manager):
        self.root = root
        self.display_idx = display_idx
        self.manager = manager
        self.settings = manager.settings_manager
        
        # UI State
        self.zoom_level, self.pan_x, self.pan_y = 1.0, 0, 0
        self.is_dragging, self.drag_start_x, self.drag_start_y = False, 0, 0
        self.zoom_1to1_active = False
        self.drawer_visible = True
        self.toolbar_visible = self.settings.get("show_toolbar", True)
        self.current_pil_image, self.photo_image = None, None
        
        self.size_var = tk.StringVar()
        
        self._create_ui()
        self._bind_events()
        self._set_initial_state()
        self._update_image_loop()

    def cleanup_tkinter_resources(self):
        """Limpieza segura de recursos de Tkinter para prevenir errores de destrucción"""
        # PROTECCIÓN TCL: Solo ejecutar en el hilo principal
        import threading
        current_thread = threading.current_thread()
        
        if current_thread.name != "MainThread":
            wp_logger.warning(f"Skipping cleanup_tkinter_resources desde hilo {current_thread.name} - protección Tcl_AsyncDelete", "WatchPointWindow")
            return
        
        try:
            # Limpiar variables de Tkinter
            if hasattr(self, 'size_var'):
                try:
                    self.size_var.set('')  # Limpiar valor antes de destruir
                except:
                    pass
                self.size_var = None
            
            # Limpiar imágenes
            if hasattr(self, 'photo_image') and self.photo_image:
                try:
                    self.photo_image = None
                except:
                    pass
            
            # Limpiar referencias a widgets
            if hasattr(self, 'canvas') and self.canvas:
                try:
                    self.canvas.delete("all")
                except:
                    pass
            
            wp_logger.debug(f"Recursos de Tkinter limpiados para ventana {self.display_idx}", "WatchPointWindow")
        except Exception as e:
            wp_logger.warning(f"Error limpiando recursos de Tkinter: {e}", "WatchPointWindow")

    def _create_ui(self):
        # Drawer (Signal Scout)
        self.drawer_frame = tk.Frame(self.root, bg="#1c1c1c", width=300)
        self.drawer_frame.pack(side="right", fill="y")
        self.drawer_frame.pack_propagate(False)
        tk.Label(self.drawer_frame, text="PROMPT", bg="#1c1c1c", fg="#666", font=("Arial", 8, "bold"), pady=5).pack(fill="x")
        self.signal_text = tk.Text(self.drawer_frame, bg="#1c1c1c", fg="#00ff99", insertbackground="white", font=("Consolas", 10), wrap="word", padx=10, pady=10, borderwidth=0, highlightthickness=0)
        self.signal_text.pack(fill="both", expand=True)
        self.signal_text.insert("1.0", "Waiting for prompt...")
        self.signal_text.config(state="disabled")

        # Main Area
        self.main_frame = tk.Frame(self.root, bg='#1a1a1a')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_toolbar()
        
        self.canvas = tk.Canvas(self.main_frame, bg='#000000', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self._create_context_menu()

    def _create_toolbar(self):
        self.toolbar = tk.Frame(self.main_frame, bg='#2a2a2a', height=40)
        btn_style = {'bg': '#3a3a3a', 'fg': 'white', 'relief': tk.FLAT, 'padx': 8, 'pady': 4}
        
        for text, cmd in [("↻ Reset", self._reset_zoom), ("⊕ Zoom In", self._zoom_in), ("⊖ Zoom Out", self._zoom_out), ("1:1", self._zoom_1to1)]:
            tk.Button(self.toolbar, text=text, command=cmd, **btn_style).pack(side=tk.LEFT, padx=2)
        
        size_opts = ["800x600", "1024x768", "1920x1080", "Half Vertical", "Half Horizontal", "Quarter"]
        size_menu = tk.OptionMenu(self.toolbar, self.size_var, *size_opts, command=self._on_size_change)
        size_menu.config(bg='#3a3a3a', fg='white', relief=tk.FLAT)
        size_menu.pack(side=tk.LEFT, padx=2)
        
        tk.Button(self.toolbar, text="⚙", command=self._open_settings, **btn_style).pack(side=tk.LEFT, padx=2)
        
        if self.toolbar_visible:
            self.toolbar.pack(side=tk.TOP, fill=tk.X)

    def _create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Save Image As...", command=self._save_image)
        if WIN32_AVAILABLE:
            self.context_menu.add_command(label="Copy Image to Clipboard", command=self._copy_to_clipboard)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Toggle Drawer", command=self._toggle_drawer)

    def _copy_to_clipboard(self):
        """Copies the current image to the system clipboard."""
        if not self.current_pil_image or not WIN32_AVAILABLE:
            return

        try:
            output = io.BytesIO()
            # Convert to RGB for BMP format, as RGBA might not be supported.
            self.current_pil_image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # The BMP header is 14 bytes
            output.close()

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, data)
            win32clipboard.CloseClipboard()
        except Exception as e:
            # This will silently fail, as requested.
            print(f"Watch Point: Could not copy to clipboard. Error: {e}")

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-3>", self._show_context_menu)
        self.root.bind("<r>", lambda e: self._reset_zoom())
        self.root.bind("<t>", lambda e: self._toggle_toolbar())
        self.root.bind("<p>", lambda e: self._toggle_drawer())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_initial_state(self):
        # Set size dropdown
        size_mode = self.settings.get("window_size_mode")
        if size_mode in ["Half Vertical", "Half Horizontal", "Quarter"]:
            self.size_var.set(size_mode)
        else:
            self.size_var.set(f'{self.settings.get("window_width")}x{self.settings.get("window_height")}')
        
        # Process pending text
        win_data = self.manager.windows.get(self.display_idx, {})
        if win_data.get("pending_text"):
            self.update_signal_text(win_data["pending_text"])
            win_data["pending_text"] = None

    def _update_image_loop(self):
        win_data = self.manager.windows.get(self.display_idx)
        if not win_data or not win_data.get("running"):
            try: self.root.quit()
            except tk.TclError: pass
            return

        with win_data["lock"]:
            pil_img = win_data.get("image")
        
        if pil_img and pil_img != self.current_pil_image:
            self.current_pil_image = pil_img
            self._render_image()
        
        self.root.after(33, self._update_image_loop)

    def _render_image(self):
        if not self.current_pil_image: return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1: return self.root.after(50, self._render_image)
        
        iw, ih = self.current_pil_image.size
        scale = min(cw/iw, ch/ih) * self.zoom_level if not self.zoom_1to1_active else 1.0
        nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
        
        resized = self.current_pil_image.resize((nw, nh), Image.LANCZOS)
        xp, yp = (cw - nw)//2 + self.pan_x, (ch - nh)//2 + self.pan_y
        
        self.photo_image = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(xp, yp, anchor=tk.NW, image=self.photo_image)

    def update_signal_text(self, text):
        def _update():
            self.signal_text.config(state="normal")
            self.signal_text.delete("1.0", tk.END)
            self.signal_text.insert("1.0", str(text))
            self.signal_text.config(state="disabled")
        if self.root.winfo_exists():
            self.root.after(0, _update)

    # --- Event Handlers ---
    def _on_size_change(self, size_str):
        geom_str = self.manager.calculate_geometry_string(self.root, size_str, 800, 600)
        if geom_str: self.root.geometry(geom_str)

    def _on_close(self):
        # Persist final window state
        self.settings.set("window_size_mode", self.size_var.get())
        self.settings.set("window_x", self.root.winfo_x())
        self.settings.set("window_y", self.root.winfo_y())
        self.settings.set("show_toolbar", self.toolbar_visible)
        if 'x' in self.size_var.get():
            try:
                w, h = map(int, self.size_var.get().split('x'))
                self.settings.set("window_width", w)
                self.settings.set("window_height", h)
            except ValueError: pass
        self.settings.save()
        
        # Signal manager to close
        self.manager.hide_window(self.display_idx)
        try: self.root.destroy()
        except tk.TclError: pass

    def _toggle_toolbar(self):
        self.toolbar_visible = not self.toolbar_visible
        if self.toolbar_visible: self.toolbar.pack(side=tk.TOP, fill=tk.X, before=self.canvas)
        else: self.toolbar.pack_forget()

    def _toggle_drawer(self):
        self.drawer_visible = not self.drawer_visible
        if self.drawer_visible: self.drawer_frame.pack(side="right", fill="y", before=self.main_frame)
        else: self.drawer_frame.pack_forget()

    def _save_image(self):
        if not self.current_pil_image: return
        fmt = self.settings.get("save_format", "png")
        ext = f".{fmt}"
        filetypes = [(fmt.upper(), f"*{ext}")]
        if fmt == "jpeg": filetypes.append(("All files", "*.*"))
        
        f_path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=filetypes)
        if f_path:
            try:
                if fmt == "jpeg":
                    self.current_pil_image.convert("RGB").save(f_path, quality=self.settings.get("jpeg_quality", 90))
                else:
                    self.current_pil_image.save(f_path)
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save image:\n{e}")

    def _open_settings(self): WatchPointSettingsDialog(self.root, self.settings)
    def _on_mouse_wheel(self, e): self._zoom_in() if e.delta > 0 else self._zoom_out()
    def _on_mouse_down(self, e): self.is_dragging, self.drag_start_x, self.drag_start_y = True, e.x, e.y
    def _on_mouse_up(self, e): self.is_dragging = False
    def _show_context_menu(self, e): self.context_menu.tk_popup(e.x_root, e.y_root)
    def _on_mouse_drag(self, e):
        if self.is_dragging:
            self.pan_x += e.x - self.drag_start_x
            self.pan_y += e.y - self.drag_start_y
            self.drag_start_x, self.drag_start_y = e.x, e.y
            self._render_image()
    def _zoom_in(self): self.zoom_1to1_active=False; self.zoom_level=min(10.0,self.zoom_level*1.2); self._render_image()
    def _zoom_out(self): self.zoom_1to1_active=False; self.zoom_level=max(0.1,self.zoom_level/1.2); self._render_image()
    def _zoom_1to1(self): self.zoom_1to1_active=True; self.pan_x=0; self.pan_y=0; self._render_image()
    def _reset_zoom(self): self.zoom_1to1_active=False; self.zoom_level=1.0; self.pan_x=0; self.pan_y=0; self._render_image()

class WatchPointSettingsDialog:
    """A dialog for changing application settings."""
    def __init__(self, parent, settings_manager):
        self.settings = settings_manager
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        self.show_toolbar_var = tk.BooleanVar(value=self.settings.get("show_toolbar"))
        self.save_format_var = tk.StringVar(value=self.settings.get("save_format"))
        self.jpeg_quality_var = tk.IntVar(value=self.settings.get("jpeg_quality"))

        frame = tk.Frame(self.dialog, padx=15, pady=15)
        frame.pack(fill="both", expand=True)
        tk.Checkbutton(frame, text="Show Toolbar on Startup", variable=self.show_toolbar_var).pack(anchor="w")
        
        fmt_frame = tk.LabelFrame(frame, text="Default Save Format", padx=10, pady=10)
        fmt_frame.pack(anchor="w", fill="x", pady=(10, 5))
        tk.Radiobutton(fmt_frame, text="PNG (lossless)", variable=self.save_format_var, value="png", command=self._toggle_quality).pack(anchor="w")
        tk.Radiobutton(fmt_frame, text="JPEG (compressed)", variable=self.save_format_var, value="jpeg", command=self._toggle_quality).pack(anchor="w")

        self.q_frame = tk.LabelFrame(frame, text="JPEG Quality", padx=10, pady=10)
        self.q_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.q_scale = tk.Scale(self.q_frame, from_=1, to=100, orient="horizontal", variable=self.jpeg_quality_var)
        self.q_scale.pack(anchor="w", fill="x")
        self._toggle_quality()

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x", side="bottom")
        tk.Button(btn_frame, text="Save", command=self._save_close).pack(side="right", padx=(5,0))
        tk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side="right")
        self.dialog.wait_window()

    def _toggle_quality(self):
        state = "normal" if self.save_format_var.get() == "jpeg" else "disabled"
        for child in self.q_frame.winfo_children(): child.configure(state=state)

    def _save_close(self):
        self.settings.set("show_toolbar", self.show_toolbar_var.get())
        self.settings.set("save_format", self.save_format_var.get())
        self.settings.set("jpeg_quality", self.jpeg_quality_var.get())
        self.settings.save()
        self.dialog.destroy()

# --- Node Registration ---
NODE_CLASS_MAPPINGS = {"WatchPoint": WatchPoint}
NODE_DISPLAY_NAME_MAPPINGS = {"WatchPoint": "👁️ Watch Point"}

# --- Signal Scout Integration ---
class WPSignalScout:
    """A simple node to send text to all Watch Point windows."""
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": ("STRING", {"multiline": True, "default": ""})}}
    RETURN_TYPES = ("STRING",)
    FUNCTION = "scout_signal"
    CATEGORY = "WatchPoint"

    def scout_signal(self, text):
        try:
            WindowManager().update_all_text(text)
        except Exception as e:
            print(f"WP_Scout Error: Could not connect to Watch Point window: {e}")

# --- Función de Shutdown Global ---
def cleanup_all_watchpoints():
    """Función para limpiar todos los nodos WatchPoint sin usar atexit"""
    shutdown_registry.shutdown_all()

# Agregar la función al módulo para que esté disponible
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "cleanup_all_watchpoints"]

NODE_CLASS_MAPPINGS["WPSignalScout"] = WPSignalScout
NODE_DISPLAY_NAME_MAPPINGS["WPSignalScout"] = "📡 WP Signal Scout"

# --- Debug Node ---
class WatchPointDebug:
    """Nodo de debug para WatchPoint - Controla modo debug y captura dumps"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "action": (["enable_debug", "disable_debug", "save_dump", "get_stats", "get_threads"],),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    FUNCTION = "execute_debug_action"
    CATEGORY = "WatchPoint"
    
    def execute_debug_action(self, action):
        """Ejecutar acción de debug y retornar resultado"""
        
        if action == "enable_debug":
            wp_logger.set_debug_mode(True)
            return ("✅ Modo debug activado",)
            
        elif action == "disable_debug":
            wp_logger.set_debug_mode(False)
            return ("⚪ Modo debug desactivado",)
            
        elif action == "save_dump":
            # Buscar una instancia WatchPoint activa
            watchpoint_instance = self._find_watchpoint_instance()
            filepath = wp_logger.save_debug_dump(watchpoint_instance)
            if filepath:
                return (f"💾 Debug dump guardado: {os.path.basename(filepath)}",)
            else:
                return ("❌ Error al guardar debug dump (modo debug desactivado?)",)
                
        elif action == "get_stats":
            watchpoint_instance = self._find_watchpoint_instance()
            if watchpoint_instance and hasattr(watchpoint_instance, 'get_health_stats'):
                stats = watchpoint_instance.get_health_stats()
                stats_text = json.dumps(stats, indent=2, default=str)
                return (f"📊 Estadísticas:\n{stats_text}",)
            else:
                return ("ℹ️ No hay instancia WatchPoint activa encontrada",)
                
        elif action == "get_threads":
            watchpoint_instance = self._find_watchpoint_instance()
            if watchpoint_instance and hasattr(watchpoint_instance, 'debug_threads'):
                threads = watchpoint_instance.debug_threads()
                threads_text = json.dumps(threads, indent=2, default=str)
                return (f"🧵 Información de threads:\n{threads_text}",)
            else:
                return ("ℹ️ No hay instancia WatchPoint activa encontrada",)
        
        return ("❌ Acción no reconocida",)
    
    def _find_watchpoint_instance(self):
        """Buscar una instancia WatchPoint activa en el registro global"""
        try:
            for node in shutdown_registry._nodes:
                if isinstance(node, WatchPoint):
                    return node
        except Exception:
            pass
        return None

# Agregar el nodo de debug a los mappings
NODE_CLASS_MAPPINGS["WatchPointDebug"] = WatchPointDebug
NODE_DISPLAY_NAME_MAPPINGS["WatchPointDebug"] = "🔧 Watch Point Debug"