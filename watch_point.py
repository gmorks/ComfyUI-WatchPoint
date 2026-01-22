import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
from threading import Thread, Lock
import io
import folder_paths

ICON_BASE64 = ""

try:
    from screeninfo import get_monitors
    SCREENINFO_AVAILABLE = True
except ImportError:
    SCREENINFO_AVAILABLE = False


class WatchPoint:
    """
    Watch Point - Dual Preview Monitor
    """
    _windows = {}  # monitor_idx -> window data

    @classmethod
    def INPUT_TYPES(cls):
        monitor_list = cls.get_monitors()
        return {
            "required": {
                "images": ("IMAGE",),
                "floating_preview": ("BOOLEAN", {"default": True}),
                "monitor_preview": ("BOOLEAN", {"default": True}),
                "monitor": (monitor_list, {"default": monitor_list[0]}),
            },
            "optional": {
                # Nueva entrada opcional para el texto
                "opt_signal_text": ("STRING", {"forceInput": True, "multiline": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "watch"
    OUTPUT_NODE = True
    CATEGORY = "WatchPoint"

    @classmethod
    def get_monitors(cls):
        monitors = []
        if SCREENINFO_AVAILABLE:
            try:
                actual_monitors = get_monitors()
                for i, m in enumerate(actual_monitors):
                    monitors.append(f"Monitor {i} ({m.width}x{m.height})")
            except Exception:
                pass
        if not monitors:
            monitors = ["Monitor 0 (1920x1080)"]
        return monitors

    def watch(self, images, floating_preview=True, monitor_preview=True, monitor="Monitor 0 (1920x1080)", opt_signal_text=None):
        try:
            display_idx = int(monitor.split(" ")[1])
        except Exception:
            display_idx = 0

        # Handle Monitor Preview (Tkinter)
        if monitor_preview:
            self._show_monitor_preview(images, display_idx)
            
            # --- INTEGRACIÓN SIGNAL SCOUT ---
            # Si recibimos texto, intentamos actualizar la ventana inmediatamente
            if opt_signal_text is not None and display_idx in self._windows:
                win_data = self._windows[display_idx]
                if win_data.get("window"):
                    # Si la ventana ya existe, actualizamos directo
                    win_data["window"].update_signal_text(opt_signal_text)
                else:
                    # Si la ventana se está creando (thread), guardamos el texto como pendiente
                    win_data["pending_text"] = opt_signal_text
        else:
            self._hide_monitor_preview(display_idx)

        # Handle Floating Preview
        result = []
        if floating_preview:
            result = self._prepare_preview(images)
        
        return {"ui": {"images": result}, "result": (images,)}

    def _show_monitor_preview(self, images, display_idx):
        image = images[0]
        image = 255.0 * image.cpu().numpy()
        pil_img = Image.fromarray(np.clip(image, 0, 255).astype(np.uint8))

        if display_idx in self._windows:
            if not self._windows[display_idx].get("running", False):
                try:
                    if "thread" in self._windows[display_idx]:
                        self._windows[display_idx]["thread"].join(timeout=0.1)
                except: pass
                del self._windows[display_idx]
        
        if display_idx not in self._windows:
            lock = Lock()
            self._windows[display_idx] = {
                "image": pil_img,
                "lock": lock,
                "running": True,
                "root": None,
                "window": None, # Referencia a la instancia de la clase UI
                "pending_text": None # Buffer para texto antes de init
            }
            t = Thread(target=self._window_loop, args=(display_idx,), daemon=True)
            self._windows[display_idx]["thread"] = t
            t.start()
        else:
            try:
                with self._windows[display_idx]["lock"]:
                    self._windows[display_idx]["image"] = pil_img
            except:
                del self._windows[display_idx]
                self._show_monitor_preview(images, display_idx)

    def _hide_monitor_preview(self, display_idx):
        if display_idx in self._windows:
            self._windows[display_idx]["running"] = False

    def _prepare_preview(self, images):
        results = []
        import time
        for i, tensor in enumerate(images):
            array = 255.0 * tensor.cpu().numpy()
            img = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
            output_dir = folder_paths.get_temp_directory()
            timestamp = int(time.time() * 1000)
            filename = f"watchpoint_{timestamp:013d}_{i:02d}.png"
            file_path = os.path.join(output_dir, filename)
            img.save(file_path, compress_level=4)
            results.append({"filename": filename, "subfolder": "", "type": "temp"})
        return results

    def _window_loop(self, display_idx):
        settings = self._load_settings()
        root = tk.Tk()
        root.title(f"Watch Point - Monitor {display_idx}")

        if ICON_BASE64:
            try:
                icon_img = tk.PhotoImage(data=ICON_BASE64)
                root.iconphoto(True, icon_img)
            except Exception: pass
        
        window_size_mode = settings.get("window_size_mode", "fixed")
        if window_size_mode in ["Half Vertical", "Half Horizontal", "Quarter"]:
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            if window_size_mode == "Half Vertical":
                root.geometry(f"{screen_w // 2}x{screen_h - 100}")
            elif window_size_mode == "Half Horizontal":
                root.geometry(f"{screen_w - 100}x{screen_h // 2}")
            elif window_size_mode == "Quarter":
                root.geometry(f"{screen_w // 2}x{screen_h // 2}")
        else:
            w = settings.get("window_width", 800)
            h = settings.get("window_height", 600)
            root.geometry(f"{w}x{h}")
        
        self._windows[display_idx]["root"] = root
        
        # Instanciar la UI
        preview = WatchPointWindow(root, display_idx, self._windows, settings)
        self._windows[display_idx]["window"] = preview
        
        # Restaurar posición
        wx = settings.get("window_x", None)
        wy = settings.get("window_y", None)
        if wx is not None and wy is not None:
            root.geometry(f"+{wx}+{wy}")
        elif SCREENINFO_AVAILABLE:
            try:
                m = get_monitors()[display_idx]
                root.geometry(f"+{m.x + 50}+{m.y + 50}")
            except: pass
        
        try:
            root.mainloop()
        except Exception as e:
            print(f"Watch Point error: {e}")
        finally:
            self._windows[display_idx]["running"] = False

    def _load_settings(self):
        settings_file = os.path.join(os.path.dirname(__file__), "watchpoint_settings.json")
        default = {
            "window_width": 800, "window_height": 600,
            "window_x": None, "window_y": None,
            "show_toolbar": True, "save_format": "png", "jpeg_quality": 90,
        }
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    return {**default, **json.load(f)}
        except: pass
        return default


class WatchPointWindow:
    def __init__(self, root, display_idx, windows_dict, settings):
        self.root = root
        self.display_idx = display_idx
        self.windows = windows_dict
        self.settings = settings
        
        # State
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.zoom_1to1_active = False
        self.drawer_visible = True
        self.current_pil_image = None
        self.photo_image = None
        
        self._create_ui()
        self._bind_events()
        
        # Check for pending text (Race condition fix)
        pending = self.windows[self.display_idx].get("pending_text")
        if pending:
            self.update_signal_text(pending)
            self.windows[self.display_idx]["pending_text"] = None

        self._update_image()
    
    def _create_ui(self):
        # 1. Drawer (Panel Lateral de Texto)
        self.drawer_width = 300
        self.drawer_frame = tk.Frame(self.root, bg="#1c1c1c", width=self.drawer_width)
        self.drawer_frame.pack(side="right", fill="y")
        self.drawer_frame.pack_propagate(False)

        self.label_scout = tk.Label(
            self.drawer_frame, text="📡 SIGNAL SCOUT", 
            bg="#1c1c1c", fg="#666", font=("Arial", 8, "bold"), pady=5
        )
        self.label_scout.pack(fill="x")

        self.signal_text = tk.Text(
            self.drawer_frame, bg="#1c1c1c", fg="#00ff99", 
            insertbackground="white", font=("Consolas", 10), wrap="word",
            padx=10, pady=10, borderwidth=0, highlightthickness=0
        )
        self.signal_text.pack(fill="both", expand=True)
        self.signal_text.insert("1.0", "Waiting for signal...")
        self.signal_text.config(state="disabled")

        # 2. Main Area
        self.main_frame = tk.Frame(self.root, bg='#1a1a1a')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.toolbar_visible = self.settings.get("show_toolbar", True)
        self._create_toolbar()
        
        self.canvas = tk.Canvas(self.main_frame, bg='#000000', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self._create_context_menu()
    
    def update_signal_text(self, text):
        def _update():
            self.signal_text.config(state="normal")
            self.signal_text.delete("1.0", tk.END)
            self.signal_text.insert("1.0", text)
            self.signal_text.config(state="disabled")
        self.root.after(0, _update)

    def _create_toolbar(self):
        self.toolbar = tk.Frame(self.main_frame, bg='#2a2a2a', height=40)
        btn_style = {'bg': '#3a3a3a', 'fg': 'white', 'relief': tk.FLAT, 'padx': 8, 'pady': 4}
        
        tk.Button(self.toolbar, text="↻ Reset", command=self._reset_zoom, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(self.toolbar, text="⊕ Zoom In", command=self._zoom_in, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(self.toolbar, text="⊖ Zoom Out", command=self._zoom_out, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(self.toolbar, text="1:1", command=self._zoom_1to1, **btn_style).pack(side=tk.LEFT, padx=2)
        
        self.size_var = tk.StringVar(value="Current")
        size_menu = tk.OptionMenu(self.toolbar, self.size_var, "800x600", "1024x768", "1920x1080", "Half Vertical", "Half Horizontal", "Quarter", command=self._change_window_size)
        size_menu.config(bg='#3a3a3a', fg='white', relief=tk.FLAT)
        size_menu.pack(side=tk.LEFT, padx=2)
        
        tk.Button(self.toolbar, text="⚙", command=self._open_settings, **btn_style).pack(side=tk.LEFT, padx=2)
        
        if self.toolbar_visible:
            self.toolbar.pack(side=tk.TOP, fill=tk.X)
    
    def _create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Save Image As...", command=self._save_image)
        self.context_menu.add_command(label="Copy to Clipboard", command=self._copy_to_clipboard)
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
        self.root.protocol("WM_DELETE_WINDOW", self._close_window)
    
    def _update_image(self):
        try:
            if not self.windows[self.display_idx]["running"]:
                try: self.root.quit()
                except: pass
                return
            
            with self.windows[self.display_idx]["lock"]:
                pil_img = self.windows[self.display_idx]["image"]
            
            if pil_img is not None and pil_img != self.current_pil_image:
                self.current_pil_image = pil_img
                self._render_image()
            
            self.root.after(33, self._update_image)
        except:
            self.windows[self.display_idx]["running"] = False
            try: self.root.quit()
            except: pass
    
    def _render_image(self):
        if not self.current_pil_image: return
        self.canvas.update_idletasks()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1: 
            self.root.after(100, self._render_image)
            return
        
        iw, ih = self.current_pil_image.size
        scale = 1.0 if self.zoom_1to1_active else min(cw/iw, ch/ih) * self.zoom_level
        nw, nh = max(1, int(iw*scale)), max(1, int(ih*scale))
        
        resized = self.current_pil_image.resize((nw, nh), Image.LANCZOS)
        xp = (cw - nw)//2 + int(self.pan_x)
        yp = (ch - nh)//2 + int(self.pan_y)
        
        self.photo_image = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(xp, yp, anchor=tk.NW, image=self.photo_image)

    def _on_mouse_wheel(self, event):
        if event.delta > 0: self._zoom_in()
        else: self._zoom_out()
    
    def _on_mouse_down(self, event):
        self.is_dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def _on_mouse_drag(self, event):
        if self.is_dragging:
            self.pan_x += event.x - self.drag_start_x
            self.pan_y += event.y - self.drag_start_y
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self._render_image()
    
    def _on_mouse_up(self, event): self.is_dragging = False
    def _show_context_menu(self, event): self.context_menu.tk_popup(event.x_root, event.y_root)
    def _zoom_in(self): 
        self.zoom_1to1_active = False
        self.zoom_level = min(10.0, self.zoom_level * 1.2)
        self._render_image()
    def _zoom_out(self):
        self.zoom_1to1_active = False
        self.zoom_level = max(0.1, self.zoom_level / 1.2)
        self._render_image()
    def _zoom_1to1(self):
        self.zoom_1to1_active = True
        self.pan_x = 0; self.pan_y = 0
        self._render_image()
    def _reset_zoom(self):
        self.zoom_1to1_active = False
        self.zoom_level = 1.0
        self.pan_x = 0; self.pan_y = 0
        self._render_image()
    
    def _toggle_toolbar(self):
        if self.toolbar_visible: self.toolbar.pack_forget(); self.toolbar_visible = False
        else: self.toolbar.pack(side=tk.TOP, fill=tk.X, before=self.canvas); self.toolbar_visible = True

    def _toggle_drawer(self):
        if self.drawer_visible: self.drawer_frame.pack_forget(); self.drawer_visible = False
        else: self.drawer_frame.pack(side="right", fill="y", before=self.main_frame); self.drawer_visible = True
    
    def _change_window_size(self, size_str):
        # Simplificado para el ejemplo
        try:
            w, h = map(int, size_str.split('x'))
            self.root.geometry(f"{w}x{h}")
        except: pass
        
    def _save_image(self):
        if not self.current_pil_image: return
        f = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if f: self.current_pil_image.save(f)
    
    def _copy_to_clipboard(self):
        # Requiere pywin32, omitido por simplicidad si no está instalado
        pass
    
    def _open_settings(self):
        WatchPointSettingsDialog(self.root, self.settings, self)
    
    def _close_window(self):
        self.windows[self.display_idx]["running"] = False
        try:
            # Save window geometry and state before closing
            size_mode = self.size_var.get()
            if size_mode in ["Half Vertical", "Half Horizontal", "Quarter"]:
                self.settings['window_size_mode'] = size_mode
            else:
                self.settings['window_size_mode'] = "fixed"
                self.settings['window_width'] = self.root.winfo_width()
                self.settings['window_height'] = self.root.winfo_height()

            self.settings['window_x'] = self.root.winfo_x()
            self.settings['window_y'] = self.root.winfo_y()
            self.settings['show_toolbar'] = self.toolbar_visible 

            settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchpoint_settings.json")
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e: 
            print(f"Watch Point: Could not save window settings on close: {e}")

        try: self.root.destroy()
        except: pass

class WatchPointSettingsDialog:
    def __init__(self, parent, settings, window_instance):
        self.settings = settings
        self.window_instance = window_instance
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        # Variables
        self.show_toolbar_var = tk.BooleanVar(value=self.settings.get("show_toolbar", True))
        self.save_format_var = tk.StringVar(value=self.settings.get("save_format", "png"))
        self.jpeg_quality_var = tk.IntVar(value=self.settings.get("jpeg_quality", 90))

        # UI
        frame = tk.Frame(self.dialog, padx=15, pady=15)
        frame.pack(fill="both", expand=True)

        tk.Checkbutton(frame, text="Show Toolbar on Startup", variable=self.show_toolbar_var).pack(anchor="w")

        format_frame = tk.LabelFrame(frame, text="Default Save Format", padx=10, pady=10)
        format_frame.pack(anchor="w", fill="x", pady=(10, 5))
        tk.Radiobutton(format_frame, text="PNG (lossless)", variable=self.save_format_var, value="png", command=self._toggle_jpeg_quality).pack(anchor="w")
        tk.Radiobutton(format_frame, text="JPEG (compressed)", variable=self.save_format_var, value="jpeg", command=self._toggle_jpeg_quality).pack(anchor="w")

        self.quality_frame = tk.LabelFrame(frame, text="JPEG Quality", padx=10, pady=10)
        self.quality_frame.pack(anchor="w", fill="x", pady=(0, 10))
        self.quality_scale = tk.Scale(self.quality_frame, from_=1, to=100, orient="horizontal", variable=self.jpeg_quality_var)
        self.quality_scale.pack(anchor="w", fill="x")
        self._toggle_jpeg_quality()

        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x", side="bottom")
        tk.Button(button_frame, text="Save", command=self._save_and_close).pack(side="right", padx=(5,0))
        tk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side="right")

        self.dialog.wait_window()

    def _toggle_jpeg_quality(self):
        state = "normal" if self.save_format_var.get() == "jpeg" else "disabled"
        if hasattr(self, 'quality_frame'):
            for child in self.quality_frame.winfo_children():
                child.configure(state=state)

    def _save_and_close(self):
        new_show_toolbar = self.show_toolbar_var.get()
        if self.window_instance.toolbar_visible != new_show_toolbar:
            self.window_instance._toggle_toolbar()

        self.settings["show_toolbar"] = new_show_toolbar
        self.settings["save_format"] = self.save_format_var.get()
        self.settings["jpeg_quality"] = self.jpeg_quality_var.get()

        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchpoint_settings.json")
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings:\n{e}", parent=self.dialog)

        self.dialog.destroy()

# Node registration
NODE_CLASS_MAPPINGS = {
    "WatchPoint": WatchPoint
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WatchPoint": "👁️ Watch Point"
}