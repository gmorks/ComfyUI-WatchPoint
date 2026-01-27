import os
import json
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
from threading import Thread, Lock
import folder_paths
import io
import time
import threading
try:
    import ctypes
    if sys.platform.startswith("win"):
        from ctypes import wintypes
    CTYPES_AVAILABLE = True
except ImportError:
    CTYPES_AVAILABLE = False

# Global Shutdown Registry
class ShutdownRegistry:
    """Global registry to handle shutdown without atexit"""
    _instance = None
    _nodes = []
    _shutdown_called = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ShutdownRegistry, cls).__new__(cls)
        return cls._instance
    
    def register(self, node):
        """Register a node for cleanup"""
        if not self._shutdown_called:
            self._nodes.append(node)
    
    def shutdown_all(self):
        """Shutdown all registered nodes"""
        if self._shutdown_called:
            return
        self._shutdown_called = True
        
        wp_logger.info(f"Cleaning up {len(self._nodes)} nodes...", "ShutdownRegistry")
        for node in self._nodes[:]:
            try:
                if hasattr(node, 'cleanup'):
                    node.cleanup()
            except Exception as e:
                wp_logger.error(f"Error in cleanup: {e}", "ShutdownRegistry")
        self._nodes.clear()

# Create global instance
shutdown_registry = ShutdownRegistry()

# Logging Structured
class WatchPointLogger:
    """Structured logging system for WatchPoint"""
    
    def __init__(self):
        self.enabled = True
        self.log_level = "INFO"  # DEBUG, INFO, WARNING, ERROR
        self.logs = []
        self.max_logs = 100
    
    def log(self, level, message, component="WatchPoint"):
        """Log a message with level and component"""
        if not self.enabled:
            return
        
        # Check log level
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
        
        # Keep only the latest logs
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
        
        # Always print errors
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
        """Get filtered logs by level and component"""
        filtered_logs = self.logs
        
        if level:
            filtered_logs = [log for log in filtered_logs if log["level"] == level]
        
        if component:
            filtered_logs = [log for log in filtered_logs if log["component"] == component]
        
        return filtered_logs
    
    def clear_logs(self):
        """Clear all logs"""
        self.logs = []


# Create global logger
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


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self._show)
        self.widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", 8),
        )
        label.pack(ipadx=4, ipady=2)

    def _hide(self, event=None):
        if self.tipwindow is not None:
            self.tipwindow.destroy()
            self.tipwindow = None

# Monitor Detection
if sys.platform.startswith("win") and CTYPES_AVAILABLE:
    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

class MonitorTracker:
    """Handles cross-platform monitor detection."""
    def __init__(self):
        self.user32 = None
        if sys.platform.startswith("win") and CTYPES_AVAILABLE:
            try:
                self.user32 = ctypes.windll.user32
            except Exception as e:
                print(f"WatchPoint: Failed to load user32: {e}")

    def get_monitor_geometry(self, widget):
        """
        Returns (x, y, width, height) of the monitor containing the widget's center.
        """
        # 1. Try Windows ctypes (Most accurate for Windows)
        if self.user32:
            try:
                # Need absolute coordinates
                x = widget.winfo_rootx()
                y = widget.winfo_rooty()
                
                # If window coordinates are weird (e.g. -32000 when minimized), fallback
                if x < -10000 or y < -10000:
                     # Use mouse pointer as fallback for detection if window is off-screen/minimized
                     x, y = widget.winfo_pointerxy()
                
                width = widget.winfo_width()
                height = widget.winfo_height()
                
                cx = x + width // 2
                cy = y + height // 2
                
                point = wintypes.POINT(cx, cy)
                MONITOR_DEFAULTTONEAREST = 2
                hMonitor = self.user32.MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST)
                
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                
                if self.user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
                    r = mi.rcMonitor
                    return (r.left, r.top, r.right - r.left, r.bottom - r.top)
            except Exception as e:
                # Silently fail and try next method
                pass
        
        # 2. Try screeninfo (Cross-platform if installed)
        if SCREENINFO_AVAILABLE:
            try:
                # Need absolute coordinates
                x = widget.winfo_rootx()
                y = widget.winfo_rooty()
                cx = x + widget.winfo_width() // 2
                cy = y + widget.winfo_height() // 2
                
                for m in get_monitors():
                    if (m.x <= cx < m.x + m.width) and (m.y <= cy < m.y + m.height):
                        return (m.x, m.y, m.width, m.height)
            except Exception:
                pass
                
        # 3. Fallback to Tkinter screen info (Primary monitor or screen containing widget)
        # Note: winfo_screenwidth/height typically return primary monitor size
        try:
            return (0, 0, widget.winfo_screenwidth(), widget.winfo_screenheight())
        except:
            return (0, 0, 800, 600)

# Settings Management
class SettingsManager:
    """Handles loading and saving of settings to a JSON file."""
    def __init__(self, settings_file):
        self.filepath = settings_file
        self.defaults = {
            "window_width": 800, "window_height": 600,
            "window_x": None, "window_y": None,
            "window_size_mode": "fixed",
            "show_toolbar": True, "save_format": "png", "jpeg_quality": 90,
            "start_fullscreen": False,
            "monitor_index": 0,
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

# Window Management
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
            self._start_time = time.time()  # Start time for statistics
            self.initialized = True
            
            # Iniciar watchdog
            self.watchdog_thread = Thread(target=self._watchdog_loop, daemon=True)
            self.watchdog_thread.start()
            
            wp_logger.info("WindowManager initialized", "WindowManager")

    def show_image(self, pil_img, text=None):
        """Creates or updates THE SINGLE global window to display an image and optional text."""
        
        target_monitor_idx = self.settings_manager.get("monitor_index", 0)
        
        # Check if any window exists, reuse it
        if len(self.windows) > 0:
            # Get the index of the existing window (there should only be 1)
            existing_idx = list(self.windows.keys())[0]
            win_data = self.windows[existing_idx]
            
            # Check that the window is running
            if not win_data.get("running", False):
                # Window exists but is dead, clean up
                wp_logger.warning(f"Window {existing_idx} exists but is not running, cleaning up", "ShowImage")
                self._cleanup_window(existing_idx)
                # Continue to create new window (below)
            else:
                # Window is alive, REUSE
                wp_logger.debug(f"Reusing existing window {existing_idx} for new image", "ShowImage")
                
                # Update image
                with win_data["lock"]:
                    win_data["image"] = pil_img
                
                # Update text if it exists
                if text and win_data.get("instance"):
                    win_data["instance"].update_signal_text(text)
                
                # Update monitor if changed
                if existing_idx != target_monitor_idx:
                    # Monitor changed, move window
                    wp_logger.info(f"Monitor changed from {existing_idx} to {target_monitor_idx} - Moving Window", "ShowImage")
                    
                    # Move data to new key
                    self.windows[target_monitor_idx] = self.windows.pop(existing_idx)
                    win_data = self.windows[target_monitor_idx]
                    
                    if win_data.get("instance"):
                        win_data["instance"].display_idx = target_monitor_idx
                        
                        # Handle fullscreen move
                        was_fullscreen = False
                        if hasattr(win_data["instance"], "fullscreen_active") and win_data["instance"].fullscreen_active:
                            was_fullscreen = True
                            # Disable fullscreen to allow move
                            win_data["instance"]._set_fullscreen(False)

                        # Move the window
                        try:
                            self._apply_geometry(win_data["instance"].root, target_monitor_idx)
                        except Exception as e:
                            wp_logger.error(f"Error moving window: {e}", "ShowImage")
                        
                        # Re-enable fullscreen if needed (now on new monitor)
                        if was_fullscreen:
                            try:
                                win_data["instance"].root.update_idletasks()
                                win_data["instance"]._set_fullscreen(True)
                            except Exception as e:
                                wp_logger.warning(f"Error restoring fullscreen after move: {e}", "ShowImage")
                
                return
        
        # If we reach here, NO window exists, create a new one
        wp_logger.info(f"Creating new global window on Monitor {target_monitor_idx}", "ShowImage")
        display_idx = target_monitor_idx
        
        lock = Lock()
        win_data = {
            "image": pil_img, "lock": lock, "running": True,
            "instance": None, "pending_text": text,
            "minimized": False
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
            
            
            try:
                thread = self.windows[display_idx].get("thread")
                if thread and thread.is_alive():
                    thread.join(timeout=3.0)
                    wp_logger.debug(f"Thread {display_idx} finished successfully", "HideWindow")
            except Exception as e:
                wp_logger.error(f"Error waiting for thread {display_idx}: {e}", "HideWindow")
            
            # Force cleanup if thread is still alive
            if display_idx in self.windows and self.windows[display_idx].get("thread", {}).is_alive():
                wp_logger.warning(f"Forcing cleanup for window {display_idx}", "HideWindow")
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
            # Create main window
            root = tk.Tk()
            root.title("Watch Point")
            
            self._apply_icon(root)
            self._apply_geometry(root, display_idx)

            win_instance = WatchPointWindow(root, display_idx, self)
            self.windows[display_idx]["instance"] = win_instance
            
            # NEW: Close handler that minimizes instead of closing - Accidental close protection!
            def safe_close():
                # Instead of closing, MINIMIZE the window to the taskbar!
                try:
                    root.iconify()  # Minimize to taskbar
                    # Update state: window is still alive but minimized
                    self.windows[display_idx]["minimized"] = True
                    self.windows[display_idx]["running"] = True  # Still running
                    wp_logger.info(f"Window {display_idx} minimized (protected from accidental close)", "WindowLoop")
                except Exception as e:
                    wp_logger.warning(f"Error minimizing window {display_idx}: {e}", "WindowLoop")
                    # Fallback: if cannot minimize, try to hide
                    try:
                        root.withdraw()
                        self.windows[display_idx]["minimized"] = True
                        wp_logger.info(f"Window {display_idx} hidden as fallback", "WindowLoop")
                    except:
                        pass
            
            root.protocol("WM_DELETE_WINDOW", safe_close)
            
            # IMPROVED: Better mainloop exception handling
            try:
                root.mainloop()
            except RuntimeError as e:
                # Common RuntimeError when closing: "main thread is not in main loop"
                if "main thread" not in str(e):
                    wp_logger.error(f"RuntimeError in mainloop: {e}", "WindowLoop")
                    raise
                else:
                    wp_logger.debug(f"Expected RuntimeError in mainloop: {e}", "WindowLoop")
            except Exception as e:
                wp_logger.error(f"Error in Tkinter mainloop: {e}", "WindowLoop")
        
        except Exception as e:
            wp_logger.error(f"Error in window {display_idx}: {e}", "WindowLoop")
        
        finally:
            # IMPROVED: Cleanup with multiple attempts and Tkinter cleanup
            # CRITICAL: Only the main thread can touch Tkinter resources
            import threading
            current_thread = threading.current_thread()
            
            for attempt in range(3):
                try:
                    # TCL PROTECTION: Only clean Tkinter if we're in the main thread
                    if current_thread.name == "MainThread":
                        # Clean Tkinter resources first
                        if win_instance:
                            try:
                                win_instance.cleanup_tkinter_resources()
                            except Exception as e:
                                wp_logger.warning(f"Error cleaning up Tkinter resources: {e}", "WindowLoop")
                        
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
                        # If not in main thread, just log and skip Tkinter cleanup
                        wp_logger.warning(f"Skipping Tkinter cleanup from thread {current_thread.name} - Tcl_AsyncDelete protection", "WindowLoop")
                        continue
                    
                    # If in main thread, try cleanup
                    self._cleanup_window(display_idx)
                    break
                except Exception as e:
                    if attempt == 2:
                        wp_logger.error(f"Cleanup failed after 3 attempts: {e}", "WindowLoop")
                    time.sleep(0.05)

    def restore_window(self, display_idx):
        """Restore a minimized window - To recover it from the taskbar!"""
        if display_idx in self.windows:
            win_data = self.windows[display_idx]
            
            # Check if it's minimized
            if not win_data.get("minimized", False):
                wp_logger.debug(f"Window {display_idx} is not minimized", "RestoreWindow")
                return False
            
            instance = win_data.get("instance")
            if not instance:
                wp_logger.warning(f"Cannot restore window {display_idx}: invalid instance", "RestoreWindow")
                return False
            
            try:
                # Restore the window using the instance's root
                if hasattr(instance, 'root') and instance.root:
                    instance.root.deiconify()  # Make visible again
                    instance.root.lift()  # Bring to front
                    instance.root.focus_force()  # Give focus
                    
                    # Update state
                    win_data["minimized"] = False
                    wp_logger.info(f"Window {display_idx} restored successfully", "RestoreWindow")
                return True
                
            except Exception as e:
                wp_logger.error(f"Error restoring window {display_idx}: {e}", "RestoreWindow")
                return False
        else:
            wp_logger.warning(f"Window {display_idx} does not exist", "RestoreWindow")
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
        """Ensures a window and its resources are properly removed with multiple attempts."""
        if display_idx in self.windows:
            import threading
            current_thread = threading.current_thread()
            
            for attempt in range(3):
                try:
                    win_data = self.windows[display_idx]
                    
                    # THREAD PROTECTION: Only try to join if current thread is NOT the window thread
                    if "thread" in win_data and win_data["thread"].is_alive():
                        # Verificar que no estemos intentando hacer join a nosotros mismos
                        if win_data["thread"] != current_thread:
                            try:
                                win_data["thread"].join(timeout=0.1)
                            except Exception: 
                                pass
                        else:
                            wp_logger.warning(f"Avoiding self-join in cleanup for window {display_idx}", "Cleanup")
                    
                    # Remove from list ALWAYS, even if errors occur
                    try:
                        del self.windows[display_idx]
                    except KeyError:
                        # Already removed, not an error
                        pass
                    
                    # Log success after successful cleanup
                    wp_logger.debug(f"Successfully cleaned up window {display_idx} (attempt {attempt + 1})", "Cleanup")
                    break
                except Exception as e:
                    if attempt == 2:
                        wp_logger.error(f"Cleanup failed after 3 attempts: {e}", "Cleanup")
                    time.sleep(0.05)

    def _watchdog_loop(self):
        """Monitor and clean up dead threads every second"""
        wp_logger.info("Watchdog started", "Watchdog")
        
        while not self.shutdown_event.is_set():
            time.sleep(1.0)
            
            dead_windows = []
            for display_idx, win_data in list(self.windows.items()):
                # Detect dead threads that didn't clean up
                if "thread" in win_data:
                    if not win_data["thread"].is_alive():
                        dead_windows.append(display_idx)
                        wp_logger.warning(f"Dead thread detected for window {display_idx}", "Watchdog")
                    # Detect windows that are taking too long to close
                    elif win_data.get("closing") and win_data.get("close_started"):
                        if time.time() - win_data["close_started"] > 5.0:
                            # Force cleanup after 5 seconds
                            dead_windows.append(display_idx)
                            wp_logger.warning(f"Window {display_idx} taking too long to close", "Watchdog")
            
            # Clean up dead windows
            for idx in dead_windows:
                # Log before force cleanup
                wp_logger.info(f"Force cleaning up dead window {idx}", "Watchdog")
                self._force_cleanup_window(idx)
        
        wp_logger.info("Watchdog finished", "Watchdog")

    def _force_cleanup_window(self, display_idx):
        """Force cleanup of a window without waiting for the thread"""
        if display_idx in self.windows:
            try:
                # No intentar join, solo eliminar
                del self.windows[display_idx]
                # Log success after successful force cleanup
                wp_logger.debug(f"Successfully force cleaned up window {display_idx}", "Cleanup")
            except Exception as e:
                wp_logger.error(f"Error in force cleanup: {e}", "Cleanup")

    def get_health_stats(self):
        """Get health statistics of the system"""
        stats = {
            "total_windows_created": len(self.windows),
            "active_windows": len([w for w in self.windows.values() if w.get("running", False)]),
            "closing_windows": len([w for w in self.windows.values() if w.get("closing", False)]),
            "threads_alive": len([w for w in self.windows.values() if w.get("thread") and w["thread"].is_alive()]),
            "watchdog_status": "running" if hasattr(self, 'watchdog_thread') and self.watchdog_thread.is_alive() else "stopped",
            "shutdown_event": self.shutdown_event.is_set(),
            "uptime": time.time() - getattr(self, '_start_time', time.time())
        }
        
        # Add thread information
        import threading
        stats["total_threads"] = threading.active_count()
        
        return stats
    def shutdown(self):
        """Shutdown global del WindowManager without using atexit"""
        wp_logger.info("Initiating global shutdown...", "WindowManager")
        self.shutdown_event.set()
        
        # Close all active windows
        for display_idx in list(self.windows.keys()):
            try:
                self.hide_window(display_idx)
            except Exception as e:
                # Log error if window closing fails
                wp_logger.error(f"Error closing window {display_idx}: {e}", "WindowManager")
        
        # Wait for the watchdog thread to finish
        try:
            if hasattr(self, 'watchdog_thread') and self.watchdog_thread.is_alive():
                self.watchdog_thread.join(timeout=2.0)
        except Exception as e:
            # Log error if watchdog thread join fails
            wp_logger.error(f"Error waiting for watchdog thread: {e}", "WindowManager")
        
        # Log successful shutdown completion
        wp_logger.info("Global shutdown completed successfully", "WindowManager")

# Global Window Manager Instance
window_manager = WindowManager()

# Main ComfyUI Node
class WatchPoint:
    """The main ComfyUI node class."""
    def __init__(self):
        self.window_manager = window_manager 
        
        # Register for cleanup
        shutdown_registry.register(self)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "floating_preview": ("BOOLEAN", {"default": True}),
                "monitor_preview": ("BOOLEAN", {"default": True}),
            },
            "optional": {"opt_signal_text": ("STRING", {"forceInput": True, "multiline": True})}
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "watch"
    OUTPUT_NODE = True
    CATEGORY = "WatchPoint"

    def watch(self, images, floating_preview=True, monitor_preview=True, opt_signal_text=None):
        if monitor_preview:
            image = 255.0 * images[0].cpu().numpy()
            pil_img = Image.fromarray(np.clip(image, 0, 255).astype(np.uint8))
            self.window_manager.show_image(pil_img, opt_signal_text)
        
        # If monitor_preview is False, we do NOTHING.
        # The window remains open (static) if it was already open.
        # We do NOT call hide_window().

        ui_images = self._prepare_preview(images) if floating_preview else []
        
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
        """Get system logging logs"""
        return wp_logger.get_logs(level, component)
    
    def clear_logs(self):
        """Clear all logs"""
        wp_logger.clear_logs()
        wp_logger.info("Logs cleared", "WatchPoint")

# Tkinter UI Classes
class WatchPointWindow:
    """The main UI for a preview window."""
    def __init__(self, root, display_idx, manager):
        self.root = root
        self.display_idx = display_idx
        self.manager = manager
        self.settings = manager.settings_manager
        self.monitor_tracker = MonitorTracker()
        
        # UI State
        self.zoom_level, self.pan_x, self.pan_y = 1.0, 0, 0
        self.is_dragging, self.drag_start_x, self.drag_start_y = False, 0, 0
        self.zoom_1to1_active = False
        self.drawer_visible = True
        self.fullscreen_active = False
        self.toolbar_visible = self.settings.get("show_toolbar", True)
        self.current_pil_image, self.photo_image = None, None
        
        self.size_var = tk.StringVar()
        
        self._create_ui()
        self._bind_events()
        self._set_initial_state()
        self._update_image_loop()

    def cleanup_tkinter_resources(self):
        """Safe cleanup of Tkinter resources to prevent destruction errors"""
        # TCL PROTECTION: Only execute in main thread
        import threading
        current_thread = threading.current_thread()
        
        if current_thread.name != "MainThread":
            wp_logger.warning(f"Skipping cleanup_tkinter_resources from thread {current_thread.name} - Tcl_AsyncDelete protection", "WatchPointWindow")
            return
        
        try:
            # Clear Tkinter variables
            if hasattr(self, 'size_var'):
                try:
                    self.size_var.set('')  # Clear value before destroying
                except:
                    pass
                self.size_var = None
            
            # Clear images
            if hasattr(self, 'photo_image') and self.photo_image:
                try:
                    self.photo_image = None
                except:
                    pass
            
            # Clean up canvas
            if hasattr(self, 'canvas') and self.canvas:
                try:
                    self.canvas.delete("all")
                except:
                    pass
            
            # Log successful cleanup
            wp_logger.debug(f"Successfully cleaned up Tkinter resources for window {self.display_idx}", "WatchPointWindow")
        except Exception as e:
            wp_logger.warning(f"Error cleaning up Tkinter resources: {e}", "WatchPointWindow")

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
        tk.Button(self.toolbar, text="↻ Reset", command=self._reset_zoom, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(self.toolbar, text="⊕ Zoom In", command=self._zoom_in, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(self.toolbar, text="⊖ Zoom Out", command=self._zoom_out, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(self.toolbar, text="1:1", command=self._zoom_1to1, **btn_style).pack(side=tk.LEFT, padx=2)
        self.fullscreen_btn = tk.Button(self.toolbar, text="⛶", command=self._toggle_fullscreen, **btn_style)
        self.fullscreen_btn.pack(side=tk.LEFT, padx=2)
        Tooltip(self.fullscreen_btn, "Toggle fullscreen (F11)")
        
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
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_initial_state(self):
        # Set size dropdown
        size_mode = self.settings.get("window_size_mode")
        if size_mode in ["Half Vertical", "Half Horizontal", "Quarter"]:
            self.size_var.set(size_mode)
        else:
            self.size_var.set(f'{self.settings.get("window_width")}x{self.settings.get("window_height")}')
        
        if self.settings.get("start_fullscreen", False):
            self._set_fullscreen(True)
        
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

    # Event Handlers
    def _on_size_change(self, size_str):
        geom_str = self.manager.calculate_geometry_string(self.root, size_str, 800, 600)
        if geom_str: self.root.geometry(geom_str)

    def _on_close(self):
        # Persist final window state
        self.settings.set("window_size_mode", self.size_var.get())
        self.settings.set("window_x", self.root.winfo_x())
        self.settings.set("window_y", self.root.winfo_y())
        self.settings.set("show_toolbar", self.toolbar_visible)
        self.settings.set("start_fullscreen", self.fullscreen_active)
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

    def _set_fullscreen(self, value):
        target_fullscreen = bool(value)
        current_fullscreen = bool(self.root.attributes("-fullscreen"))
        
        # Avoid redundant operations if state matches
        if target_fullscreen == current_fullscreen:
            self.fullscreen_active = target_fullscreen
            self._update_fullscreen_btn_style()
            return

        # Prevent multiple activations during transition
        if hasattr(self, '_fullscreen_pending') and self._fullscreen_pending:
            wp_logger.debug("Fullscreen transition already in progress, ignoring request", "WatchPointWindow")
            return

        self.fullscreen_active = target_fullscreen
        
        if self.fullscreen_active:
            # ENTER FULLSCREEN
            self._fullscreen_pending = True
            
            # 1. Save previous geometry ONLY if we are coming from a non-fullscreen state
            if not current_fullscreen:
                self.pre_fullscreen_geometry = self.root.geometry()
                wp_logger.debug(f"Fullscreen: Saved geometry {self.pre_fullscreen_geometry}", "WatchPointWindow")

            try:
                # 2. Prepare window: Force 'normal' state
                self.root.state('normal')
                self.root.update_idletasks()
                
                # 3. Detect target monitor USING CURRENT WINDOW POSITION
                # Get the window's current position before moving
                current_x = self.root.winfo_x()
                current_y = self.root.winfo_y()
                current_w = self.root.winfo_width()
                current_h = self.root.winfo_height()
                
                # Calculate center point of window
                center_x = current_x + current_w // 2
                center_y = current_y + current_h // 2
                
                wp_logger.info(f"Fullscreen: Window center at ({center_x}, {center_y})", "WatchPointWindow")
                
                # Find which monitor contains this center point
                target_monitor = None
                
                # Try screeninfo first (most reliable)
                if SCREENINFO_AVAILABLE:
                    try:
                        from screeninfo import get_monitors
                        for m in get_monitors():
                            if (m.x <= center_x < m.x + m.width) and (m.y <= center_y < m.y + m.height):
                                target_monitor = (m.x, m.y, m.width, m.height)
                                wp_logger.info(f"Fullscreen: Found monitor via screeninfo: {target_monitor}", "WatchPointWindow")
                                break
                    except Exception as e:
                        wp_logger.warning(f"Screeninfo failed: {e}", "WatchPointWindow")
                
                # Fallback to Windows API
                if not target_monitor and sys.platform.startswith("win") and CTYPES_AVAILABLE:
                    try:
                        user32 = ctypes.windll.user32
                        point = wintypes.POINT(center_x, center_y)
                        MONITOR_DEFAULTTONEAREST = 2
                        hMonitor = user32.MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST)
                        
                        mi = MONITORINFO()
                        mi.cbSize = ctypes.sizeof(MONITORINFO)
                        
                        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
                            r = mi.rcMonitor
                            target_monitor = (r.left, r.top, r.right - r.left, r.bottom - r.top)
                            wp_logger.info(f"Fullscreen: Found monitor via Windows API: {target_monitor}", "WatchPointWindow")
                    except Exception as e:
                        wp_logger.warning(f"Windows API failed: {e}", "WatchPointWindow")
                
                # Final fallback
                if not target_monitor:
                    target_monitor = (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
                    wp_logger.warning(f"Fullscreen: Using fallback monitor: {target_monitor}", "WatchPointWindow")
                
                mx, my, mw, mh = target_monitor

                # 4. Move window to exact monitor coordinates
                # Use overrideredirect temporarily to bypass window manager
                self.root.geometry(f"{mw}x{mh}+{mx}+{my}")
                
                # Force multiple updates
                for _ in range(3):
                    self.root.update_idletasks()
                    self.root.update()
                
                # 5. Delayed activation with verification
                def activate_fullscreen():
                    if not self.fullscreen_active:
                        self._fullscreen_pending = False
                        return
                    
                    try:
                        # Final position check
                        final_x = self.root.winfo_x()
                        final_y = self.root.winfo_y()
                        wp_logger.info(f"Fullscreen: Activating at position ({final_x}, {final_y})", "WatchPointWindow")
                        
                        self.root.attributes("-fullscreen", True)
                        wp_logger.info(f"Fullscreen activated on monitor at ({mx}, {my})", "WatchPointWindow")
                    except tk.TclError as e:
                        wp_logger.error(f"Failed to activate fullscreen: {e}", "WatchPointWindow")
                    finally:
                        self._fullscreen_pending = False
                        self._update_fullscreen_btn_style()
                
                # Wait 150ms instead of 100ms for better reliability
                self.root.after(150, activate_fullscreen)
                
            except Exception as e:
                wp_logger.error(f"Fullscreen setup error: {e}", "WatchPointWindow")
                # Fallback: try immediate activation if logic fails
                try:
                    self.root.attributes("-fullscreen", True)
                except:
                    pass
                self._fullscreen_pending = False
                self._update_fullscreen_btn_style()
        else:
            # EXIT FULLSCREEN
            try:
                self.root.attributes("-fullscreen", False)
                self.root.update_idletasks()
            except tk.TclError:
                pass

            # Restore geometry logic
            restored = False
            
            # 1. Try to restore from pre-fullscreen snapshot
            if hasattr(self, 'pre_fullscreen_geometry') and self.pre_fullscreen_geometry:
                try:
                    # Basic validation: ensure width > 100 to avoid restoring 1x1 windows
                    w_check = int(self.pre_fullscreen_geometry.split('x')[0])
                    if w_check > 100:
                        self.root.state('normal')
                        self.root.geometry(self.pre_fullscreen_geometry)
                        wp_logger.debug(f"Fullscreen: Restored geometry {self.pre_fullscreen_geometry}", "WatchPointWindow")
                        self.pre_fullscreen_geometry = None
                        restored = True
                except Exception:
                    pass
            
            # 2. Fallback to settings if snapshot failed or was invalid (e.g. start_fullscreen=True case)
            if not restored:
                try:
                    self.root.state('normal')
                    
                    # Get saved preferences
                    size_mode = self.settings.get("window_size_mode", "800x600")
                    sx = self.settings.get("window_x", 0)
                    sy = self.settings.get("window_y", 0)
                    
                    # Calculate geometry
                    if "x" in str(size_mode) and size_mode not in ["Half Vertical", "Half Horizontal", "Quarter"]:
                        # Standard WxH format
                        sw = self.settings.get("window_width", 800)
                        sh = self.settings.get("window_height", 600)
                        geom_str = f"{sw}x{sh}+{sx}+{sy}"
                    else:
                        # Special modes
                        geom_base = self.manager.calculate_geometry_string(self.root, size_mode, 800, 600)
                        if "+" in geom_base:
                            size_part = geom_base.split("+")[0]
                            geom_str = f"{size_part}+{sx}+{sy}"
                        else:
                            geom_str = f"{geom_base}+{sx}+{sy}"
                            
                    self.root.geometry(geom_str)
                    wp_logger.info(f"Fullscreen: Restored from settings: {geom_str}", "WatchPointWindow")
                except Exception as e:
                    wp_logger.warning(f"Error restoring geometry from settings: {e}", "WatchPointWindow")
                    # Last resort
                    self.root.geometry("800x600+100+100")

            # Update button style immediately when exiting fullscreen
            self._update_fullscreen_btn_style()


    def _update_fullscreen_btn_style(self):
        if hasattr(self, "fullscreen_btn"):
            if self.fullscreen_active:
                self.fullscreen_btn.config(relief=tk.SUNKEN, bg="#505050")
            else:
                self.fullscreen_btn.config(relief=tk.FLAT, bg="#3a3a3a")

    def _toggle_fullscreen(self):
        self._set_fullscreen(not self.fullscreen_active)

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

    def _open_settings(self): WatchPointSettingsDialog(self.root, self.settings, self)
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
    def __init__(self, parent, settings_manager, window_instance=None):
        self.settings = settings_manager
        self.window_instance = window_instance
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        self.show_toolbar_var = tk.BooleanVar(value=self.settings.get("show_toolbar"))
        self.start_fullscreen_var = tk.BooleanVar(value=self.settings.get("start_fullscreen", False))
        self.save_format_var = tk.StringVar(value=self.settings.get("save_format"))
        self.jpeg_quality_var = tk.IntVar(value=self.settings.get("jpeg_quality"))

        frame = tk.Frame(self.dialog, padx=15, pady=15)
        frame.pack(fill="both", expand=True)
        
        # Monitor Selection
        if SCREENINFO_AVAILABLE:
            try:
                monitors = [f"Monitor {i} ({m.width}x{m.height})" for i, m in enumerate(get_monitors())]
                if monitors:
                    m_frame = tk.LabelFrame(frame, text="Monitor", padx=10, pady=10)
                    m_frame.pack(anchor="w", fill="x", pady=(0, 10))
                    
                    current_idx = self.settings.get("monitor_index", 0)
                    self.monitor_var = tk.StringVar()
                    try:
                        self.monitor_var.set(monitors[current_idx])
                    except IndexError:
                        self.monitor_var.set(monitors[0])
                        
                    tk.OptionMenu(m_frame, self.monitor_var, *monitors, command=self._on_monitor_change).pack(anchor="w")
            except Exception as e:
                print(f"Watch Point: Error listing monitors: {e}")

        tk.Checkbutton(frame, text="Show Toolbar on Startup", variable=self.show_toolbar_var).pack(anchor="w")
        tk.Checkbutton(frame, text="Start in Fullscreen Mode", variable=self.start_fullscreen_var).pack(anchor="w")
        
        fmt_frame = tk.LabelFrame(frame, text="Default Save Format", padx=10, pady=10)
        fmt_frame.pack(anchor="w", fill="x", pady=(10, 5))
        tk.Radiobutton(fmt_frame, text="PNG (lossless)", variable=self.save_format_var, value="png", command=self._toggle_quality).pack(anchor="w")
        tk.Radiobutton(fmt_frame, text="JPEG (compressed)", variable=self.save_format_var, value="jpeg", command=self._toggle_quality).pack(anchor="w")

        self.q_frame = tk.LabelFrame(frame, text="JPEG Quality", padx=10, pady=10)
        self.q_frame.pack(anchor="w", fill="x", pady=(0, 10))
        
        tk.Scale(self.q_frame, from_=10, to=100, orient=tk.HORIZONTAL, variable=self.jpeg_quality_var).pack(fill="x")
        self._toggle_quality()

        btn_frame = tk.Frame(self.dialog, pady=10)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Save & Close", command=self._save_and_close, bg="#4a4a4a", fg="white").pack(side="right")

    def _on_monitor_change(self, selected_str):
        try:
            idx = int(selected_str.split(" ")[1])
            self.settings.set("monitor_index", idx)
            self.settings.save()
            
            # Live update if possible
            if self.window_instance and self.window_instance.current_pil_image:
                 self.window_instance.manager.show_image(self.window_instance.current_pil_image)
        except Exception as e:
            print(f"Watch Point: Error changing monitor: {e}")

    def _toggle_quality(self):
        if self.save_format_var.get() == "jpeg":
            self.q_frame.pack(anchor="w", fill="x", pady=(0, 10), after=self.dialog.winfo_children()[0].winfo_children()[-2])
        else:
            self.q_frame.pack_forget()

    def _save_and_close(self):
        self.settings.set("show_toolbar", self.show_toolbar_var.get())
        self.settings.set("start_fullscreen", self.start_fullscreen_var.get())
        self.settings.set("save_format", self.save_format_var.get())
        self.settings.set("jpeg_quality", self.jpeg_quality_var.get())
        self.settings.save()
        self.dialog.destroy()

# Node Registration
NODE_CLASS_MAPPINGS = {"WatchPoint": WatchPoint}
NODE_DISPLAY_NAME_MAPPINGS = {"WatchPoint": "👁️ Watch Point"}

# Global Shutdown Function
def cleanup_all_watchpoints():
    """Function to clean up all WatchPoint nodes without using atexit"""
    shutdown_registry.shutdown_all()

# Add the function to the module so it's available
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "cleanup_all_watchpoints"]
