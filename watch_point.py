import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
from threading import Thread, Lock
import folder_paths

# --- Constants and Globals ---
ICON_BASE64 = ""
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
            self.initialized = True

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
            "instance": None, "pending_text": text
        }
        self.windows[display_idx] = win_data
        
        thread = Thread(target=self._window_loop, args=(display_idx,), daemon=True)
        win_data["thread"] = thread
        thread.start()

    def hide_window(self, display_idx):
        """Signals a window to close."""
        if display_idx in self.windows:
            self.windows[display_idx]["running"] = False

    def update_all_text(self, text):
        """Updates the text in all currently open windows."""
        for win_data in self.windows.values():
            if win_data.get("running") and win_data.get("instance"):
                win_data["instance"].update_signal_text(text)

    def _window_loop(self, display_idx):
        """The main loop for a Tkinter window thread."""
        root = tk.Tk()
        root.title(f"Watch Point - Monitor {display_idx}")
        
        self._apply_icon(root)
        self._apply_geometry(root, display_idx)

        win_instance = WatchPointWindow(root, display_idx, self)
        self.windows[display_idx]["instance"] = win_instance
        
        try:
            root.mainloop()
        except Exception as e:
            print(f"Watch Point: Tkinter loop error: {e}")
        finally:
            self._cleanup_window(display_idx)

    def _apply_icon(self, root):
        """Applies the base64 icon to the window if available."""
        if ICON_BASE64:
            try:
                icon_img = tk.PhotoImage(data=ICON_BASE64)
                root.iconphoto(True, icon_img)
            except tk.TclError:
                print("Watch Point: Could not apply icon.")

    def _apply_geometry(self, root, display_idx):
        """Calculates and applies the window's initial size and position."""
        size_mode = self.settings_manager.get("window_size_mode")
        width = self.settings_manager.get("window_width")
        height = self.settings_manager.get("window_height")
        
        geom_str = self.calculate_geometry_string(root, size_mode, width, height)
        if geom_str:
            root.geometry(geom_str)

        x = self.settings_manager.get("window_x")
        y = self.settings_manager.get("window_y")

        if x is not None and y is not None:
            root.geometry(f"+{x}+{y}")
        elif SCREENINFO_AVAILABLE:
            try:
                m = get_monitors()[display_idx]
                root.geometry(f"+{m.x + 50}+{m.y + 50}")
            except IndexError:
                pass # Fallback to default position

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
        """Ensures a window and its resources are properly removed."""
        if display_idx in self.windows:
            win_data = self.windows[display_idx]
            if "thread" in win_data and win_data["thread"].is_alive():
                try:
                    win_data["thread"].join(timeout=0.1)
                except Exception: pass
            del self.windows[display_idx]

# --- Main ComfyUI Node ---
class WatchPoint:
    """The main ComfyUI node class."""
    def __init__(self):
        self.window_manager = WindowManager()

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

        if monitor_preview:
            image = 255.0 * images[0].cpu().numpy()
            pil_img = Image.fromarray(np.clip(image, 0, 255).astype(np.uint8))
            self.window_manager.show_image(display_idx, pil_img, opt_signal_text)
        else:
            self.window_manager.hide_window(display_idx)

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

    def _create_ui(self):
        # Drawer (Signal Scout)
        self.drawer_frame = tk.Frame(self.root, bg="#1c1c1c", width=300)
        self.drawer_frame.pack(side="right", fill="y")
        self.drawer_frame.pack_propagate(False)
        tk.Label(self.drawer_frame, text="📡 SIGNAL SCOUT", bg="#1c1c1c", fg="#666", font=("Arial", 8, "bold"), pady=5).pack(fill="x")
        self.signal_text = tk.Text(self.drawer_frame, bg="#1c1c1c", fg="#00ff99", insertbackground="white", font=("Consolas", 10), wrap="word", padx=10, pady=10, borderwidth=0, highlightthickness=0)
        self.signal_text.pack(fill="both", expand=True)
        self.signal_text.insert("1.0", "Waiting for signal...")
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
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Toggle Drawer", command=self._toggle_drawer)

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
        return (text,)

NODE_CLASS_MAPPINGS["WPSignalScout"] = WPSignalScout
NODE_DISPLAY_NAME_MAPPINGS["WPSignalScout"] = "📡 WP Signal Scout"
