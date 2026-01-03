import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
from threading import Thread, Lock
import io
import folder_paths
import torch

# Icon Base64 (opcional, pega tu icono aquí)
ICON_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAACXBIWXMAAAsSAAALEgHS3X78AAAH40lEQVR4nO2dX0xb1x3Hv9exjamHr0GRNzRMAFXrGgztolQFVXRWI5VJCwp9yNI401SpKJOWvoSX9Q"

try:
    from screeninfo import get_monitors
    SCREENINFO_AVAILABLE = True
except ImportError:
    SCREENINFO_AVAILABLE = False


class WatchPoint:
    """
    Watch Point - Dual Preview Monitor
    Shows image in external monitor (Tkinter) and/or floating preview (ComfyUI built-in)
    
    Controls (Monitor Preview):
    - Mouse wheel: Zoom in/out
    - Left click + drag: Pan image
    - Right click: Context menu
    - T key: Toggle toolbar
    - R key: Reset zoom and position
    - 1 key: Zoom 1:1 (100%)
    - ESC: Close window
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
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "watch"
    OUTPUT_NODE = True
    CATEGORY = "image/preview"

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

    def watch(self, images, floating_preview=True, monitor_preview=True, monitor="Monitor 0 (1920x1080)"):
        
        # Determine monitor index
        try:
            display_idx = int(monitor.split(" ")[1])
        except Exception:
            display_idx = 0

        # Handle Monitor Preview (Tkinter)
        if monitor_preview:
            self._show_monitor_preview(images, display_idx)
        else:
            self._hide_monitor_preview(display_idx)

        # Handle Floating Preview (ComfyUI built-in)
        # For floating preview to work, we need to save the image temporarily
        # and return it in the expected format
        result = []
        if floating_preview:
            # Save preview images so ComfyUI's preview system can pick them up
            result = self._prepare_preview(images)
        
        return {"ui": {"images": result}, "result": (images,)}

    def _show_monitor_preview(self, images, display_idx):
        """Show image in external monitor using Tkinter"""
        
        # Convert tensor to PIL Image
        image = images[0]
        image = 255.0 * image.cpu().numpy()
        pil_img = Image.fromarray(np.clip(image, 0, 255).astype(np.uint8))

        # Check if window exists and is still running
        if display_idx in self._windows:
            # Check if the window is actually alive
            if not self._windows[display_idx].get("running", False):
                # Window was closed, remove it and create new one
                try:
                    if "thread" in self._windows[display_idx]:
                        self._windows[display_idx]["thread"].join(timeout=0.1)
                except:
                    pass
                del self._windows[display_idx]
        
        # Create or update window
        if display_idx not in self._windows:
            lock = Lock()
            self._windows[display_idx] = {
                "image": pil_img,
                "lock": lock,
                "running": True,
                "root": None,
            }
            t = Thread(target=self._window_loop, args=(display_idx,), daemon=True)
            self._windows[display_idx]["thread"] = t
            t.start()
        else:
            # Update existing window
            try:
                with self._windows[display_idx]["lock"]:
                    self._windows[display_idx]["image"] = pil_img
            except:
                # If lock fails, window might be dead, recreate it
                del self._windows[display_idx]
                self._show_monitor_preview(images, display_idx)

    def _hide_monitor_preview(self, display_idx):
        """Hide monitor preview"""
        if display_idx in self._windows:
            self._windows[display_idx]["running"] = False

    def _prepare_preview(self, images):
        """Prepare images for ComfyUI's preview system (enables floating preview)"""
        results = []
        for i, tensor in enumerate(images):
            # Convert tensor to numpy
            array = 255.0 * tensor.cpu().numpy()
            img = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
            
            # Save to temp directory with unique timestamp
            output_dir = folder_paths.get_temp_directory()
            
            # Generate unique filename with timestamp to avoid caching issues
            import time
            timestamp = int(time.time() * 1000)  # milliseconds
            filename = f"watchpoint_{timestamp:013d}_{i:02d}.png"
            
            file_path = os.path.join(output_dir, filename)
            img.save(file_path, compress_level=4)
            
            results.append({
                "filename": filename,
                "subfolder": "",
                "type": "temp"
            })
        
        return results

    def _window_loop(self, display_idx):
        """Main window loop with Tkinter"""
        
        # Load settings
        settings = self._load_settings()
        
        # Create Tkinter window
        root = tk.Tk()
        root.title(f"Watch Point - Monitor {display_idx}")

        # Configure window icon if exists
        if ICON_BASE64:
            try:
                icon_img = tk.PhotoImage(data=ICON_BASE64)
                root.iconphoto(True, icon_img)
            except Exception as e:
                print(f"Could not set window icon: {e}")
        
        # Set window size from settings
        window_size_mode = settings.get("window_size_mode", "fixed")
        
        if window_size_mode in ["Half Vertical", "Half Horizontal", "Quarter"]:
            # Get screen dimensions
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            
            # Calculate dynamic size
            if window_size_mode == "Half Vertical":
                window_width = screen_w // 2
                window_height = screen_h - 100
            elif window_size_mode == "Half Horizontal":
                window_width = screen_w - 100
                window_height = screen_h // 2
            elif window_size_mode == "Quarter":
                window_width = screen_w // 2
                window_height = screen_h // 2
        else:
            # Use fixed size from settings
            window_width = settings.get("window_width", 800)
            window_height = settings.get("window_height", 600)
        
        root.geometry(f"{window_width}x{window_height}")
        
        # Store root reference
        self._windows[display_idx]["root"] = root
        
        # Create preview window instance
        preview = WatchPointWindow(root, display_idx, self._windows, settings)
        
        # Position window based on settings or monitor position
        window_x = settings.get("window_x", None)
        window_y = settings.get("window_y", None)
        
        if window_x is not None and window_y is not None:
            # Use saved position from settings
            root.geometry(f"+{window_x}+{window_y}")
        elif SCREENINFO_AVAILABLE:
            # Fallback to monitor position
            try:
                monitor_info = get_monitors()[display_idx]
                x = monitor_info.x + 50
                y = monitor_info.y + 50
                root.geometry(f"+{x}+{y}")
            except Exception:
                pass
        
        # Start Tkinter main loop
        try:
            root.mainloop()
        except Exception as e:
            print(f"Watch Point window error: {e}")
        finally:
            self._windows[display_idx]["running"] = False

    def _load_settings(self):
        """Load settings from JSON file"""
        settings_file = os.path.join(os.path.dirname(__file__), "watchpoint_settings.json")
        
        default_settings = {
            "window_width": 800,
            "window_height": 600,
            "window_x": None,
            "window_y": None,
            "show_toolbar": True,
            "save_format": "png",
            "jpeg_quality": 90,
        }
        
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    user_settings = json.load(f)
                    return {**default_settings, **user_settings}
        except Exception as e:
            print(f"Could not load settings: {e}")
        
        return default_settings


class WatchPointWindow:
    """Tkinter-based preview window with zoom/pan"""
    
    def __init__(self, root, display_idx, windows_dict, settings):
        self.root = root
        self.display_idx = display_idx
        self.windows = windows_dict
        self.settings = settings
        
        # Zoom/Pan state
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.zoom_1to1_active = False
        
        # Current image
        self.current_pil_image = None
        self.photo_image = None
        
        # Setup UI
        self._create_ui()
        self._bind_events()
        
        # Start update loop
        self._update_image()
    
    def _create_ui(self):
        """Create UI elements"""
        
        # Main container
        self.main_frame = tk.Frame(self.root, bg='#1a1a1a')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        self.toolbar_visible = self.settings.get("show_toolbar", True)
        self._create_toolbar()
        
        # Canvas for image display
        self.canvas = tk.Canvas(self.main_frame, bg='#000000', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Create context menu
        self._create_context_menu()
    
    def _create_toolbar(self):
        """Create toolbar with buttons"""
        self.toolbar = tk.Frame(self.main_frame, bg='#2a2a2a', height=40)
        
        # Buttons
        btn_style = {'bg': '#3a3a3a', 'fg': 'white', 'relief': tk.FLAT, 'padx': 8, 'pady': 4}
        
        tk.Button(self.toolbar, text="↻ Reset", command=self._reset_zoom, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(self.toolbar, text="⊕ Zoom In", command=self._zoom_in, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(self.toolbar, text="⊖ Zoom Out", command=self._zoom_out, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(self.toolbar, text="1:1 (100%)", command=self._zoom_1to1, **btn_style).pack(side=tk.LEFT, padx=2)
        
        # Window size dropdown
        self.size_var = tk.StringVar(value="Current")
        size_options = [
            "800x600",
            "1024x768", 
            "1280x720",
            "1920x1080",
            "---",
            "Half Vertical",
            "Half Horizontal",
            "Quarter"
        ]
        
        size_menu = tk.OptionMenu(self.toolbar, self.size_var, *size_options, 
                                  command=self._change_window_size)
        size_menu.config(bg='#3a3a3a', fg='white', relief=tk.FLAT)
        size_menu.pack(side=tk.LEFT, padx=2)
        
        tk.Button(self.toolbar, text="⛶ Fullscreen", command=self._toggle_fullscreen, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(self.toolbar, text="⚙ Settings", command=self._open_settings, **btn_style).pack(side=tk.LEFT, padx=2)
        
        if self.toolbar_visible:
            self.toolbar.pack(side=tk.TOP, fill=tk.X)
    
    def _create_context_menu(self):
        """Create right-click context menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Save Image As...", command=self._save_image)
        self.context_menu.add_command(label="Copy to Clipboard", command=self._copy_to_clipboard)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Zoom 1:1 (100%)", command=self._zoom_1to1)
        self.context_menu.add_command(label="Reset Zoom", command=self._reset_zoom)
    
    def _bind_events(self):
        """Bind keyboard and mouse events"""
        
        # Mouse events
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-3>", self._show_context_menu)
        
        # Keyboard events
        self.root.bind("<KeyPress-r>", lambda e: self._reset_zoom())
        self.root.bind("<KeyPress-R>", lambda e: self._reset_zoom())
        self.root.bind("<KeyPress-t>", lambda e: self._toggle_toolbar())
        self.root.bind("<KeyPress-T>", lambda e: self._toggle_toolbar())
        self.root.bind("<KeyPress-1>", lambda e: self._zoom_1to1())
        self.root.bind("<Escape>", lambda e: self._close_window())
        
        # Window close event
        self.root.protocol("WM_DELETE_WINDOW", self._close_window)
    
    def _update_image(self):
        """Update displayed image from shared state"""
        try:
            if not self.windows[self.display_idx]["running"]:
                # Window is closing, stop the loop gracefully
                try:
                    self.root.quit()
                except:
                    pass
                return
            
            with self.windows[self.display_idx]["lock"]:
                pil_img = self.windows[self.display_idx]["image"]
            
            if pil_img is not None:
                if pil_img != self.current_pil_image:
                    self.current_pil_image = pil_img
                    self._render_image()
            
            self.root.after(33, self._update_image)  # ~30 FPS
        except Exception as e:
            print(f"Update image error: {e}")
            # If error, mark as not running and stop
            self.windows[self.display_idx]["running"] = False
            try:
                self.root.quit()
            except:
                pass
    
    def _render_image(self):
        """Render image on canvas with zoom/pan"""
        if not self.current_pil_image:
            return
        
        self.canvas.update_idletasks()
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, self._render_image)
            return
        
        try:
            img_w, img_h = self.current_pil_image.size
            
            if self.zoom_1to1_active:
                scale = 1.0
            else:
                scale = min(canvas_width / img_w, canvas_height / img_h) * self.zoom_level
            
            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))
            
            resized = self.current_pil_image.resize((new_w, new_h), Image.LANCZOS)
            
            x_pos = (canvas_width - new_w) // 2 + int(self.pan_x)
            y_pos = (canvas_height - new_h) // 2 + int(self.pan_y)
            
            self.photo_image = ImageTk.PhotoImage(resized)
            
            self.canvas.delete("all")
            self.canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=self.photo_image)
        except Exception as e:
            print(f"Render error: {e}")
    
    def _on_mouse_wheel(self, event):
        """Handle mouse wheel for zoom"""
        if not self.zoom_1to1_active:
            if event.delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
    
    def _on_mouse_down(self, event):
        """Start dragging"""
        self.is_dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def _on_mouse_drag(self, event):
        """Handle dragging for pan"""
        if self.is_dragging:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.pan_x += dx
            self.pan_y += dy
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self._render_image()
    
    def _on_mouse_up(self, event):
        """Stop dragging"""
        self.is_dragging = False
    
    def _show_context_menu(self, event):
        """Show context menu on right click"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def _zoom_in(self):
        """Zoom in"""
        self.zoom_1to1_active = False
        self.zoom_level = min(10.0, self.zoom_level * 1.2)
        self._render_image()
    
    def _zoom_out(self):
        """Zoom out"""
        self.zoom_1to1_active = False
        self.zoom_level = max(0.1, self.zoom_level / 1.2)
        self._render_image()
    
    def _zoom_1to1(self):
        """Zoom to 1:1 (100% actual size)"""
        self.zoom_1to1_active = True
        self.pan_x = 0
        self.pan_y = 0
        self._render_image()
    
    def _reset_zoom(self):
        """Reset zoom and pan"""
        self.zoom_1to1_active = False
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._render_image()
    
    def _toggle_toolbar(self):
        """Toggle toolbar visibility"""
        if self.toolbar_visible:
            self.toolbar.pack_forget()
            self.toolbar_visible = False
        else:
            self.toolbar.pack(side=tk.TOP, fill=tk.X, before=self.canvas)
            self.toolbar_visible = True
    
    def _change_window_size(self, size_str):
        """Change window size"""
        if size_str == "---":
            return
        
        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            
            if size_str == "Half Vertical":
                w = screen_w // 2
                h = screen_h - 100
                self.root.geometry(f"{w}x{h}")
            elif size_str == "Half Horizontal":
                w = screen_w - 100
                h = screen_h // 2
                self.root.geometry(f"{w}x{h}")
            elif size_str == "Quarter":
                w = screen_w // 2
                h = screen_h // 2
                self.root.geometry(f"{w}x{h}")
            else:
                w, h = map(int, size_str.split('x'))
                self.root.geometry(f"{w}x{h}")
        except Exception as e:
            print(f"Error changing window size: {e}")
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        current_state = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not current_state)
    
    def _save_image(self):
        """Save current image to file"""
        if not self.current_pil_image:
            messagebox.showwarning("No Image", "No image to save")
            return
        
        save_format = self.settings.get("save_format", "png").upper()
        
        filetypes = [
            ("PNG Image", "*.png"),
            ("JPEG Image", "*.jpg"),
            ("WebP Image", "*.webp"),
            ("All Files", "*.*")
        ]
        
        filename = filedialog.asksaveasfilename(
            defaultextension=f".{save_format.lower()}",
            filetypes=filetypes,
            title="Save Image As"
        )
        
        if filename:
            try:
                if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                    quality = self.settings.get("jpeg_quality", 90)
                    self.current_pil_image.save(filename, "JPEG", quality=quality)
                else:
                    self.current_pil_image.save(filename)
                messagebox.showinfo("Success", f"Image saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image:\n{str(e)}")
    
    def _copy_to_clipboard(self):
        """Copy image to clipboard"""
        if not self.current_pil_image:
            messagebox.showwarning("No Image", "No image to copy")
            return
        
        try:
            output = io.BytesIO()
            self.current_pil_image.convert('RGB').save(output, 'BMP')
            data = output.getvalue()[14:]
            output.close()
            
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            messagebox.showinfo("Success", "Image copied to clipboard")
        except ImportError:
            messagebox.showerror("Error", "pywin32 not installed. Install with: pip install pywin32")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy:\n{str(e)}")
    
    def _open_settings(self):
        """Open settings dialog"""
        WatchPointSettingsDialog(self.root, self.settings)
    
    def _close_window(self):
        """Close window properly"""
        self.windows[self.display_idx]["running"] = False
        try:
            self.root.destroy()
        except:
            pass


class WatchPointSettingsDialog:
    """Settings dialog window"""
    
    def __init__(self, parent, settings):
        self.settings = settings
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Watch Point Settings")
        self.dialog.geometry("450x650")
        self.dialog.resizable(True, True)
        
        self._create_ui()
    
    def _create_ui(self):
        """Create settings UI"""
        
        # Window Size section
        size_frame = tk.LabelFrame(self.dialog, text="Default Window Size", padx=10, pady=10)
        size_frame.pack(fill=tk.X, padx=10, pady=10)
        
        current_mode = self.settings.get("window_size_mode", "fixed")
        if current_mode in ["Half Vertical", "Half Horizontal", "Quarter"]:
            initial_value = current_mode
        else:
            initial_value = f"{self.settings.get('window_width', 800)}x{self.settings.get('window_height', 600)}"
            
        self.size_var = tk.StringVar(value=initial_value)
        
        sizes = [
            "800x600",
            "1024x768",
            "1280x720",
            "1920x1080",
            "Half Vertical",
            "Half Horizontal",
            "Quarter"
        ]
        
        for size in sizes:
            tk.Radiobutton(size_frame, text=size, variable=self.size_var, value=size).pack(anchor=tk.W)
        
        # Window Position section
        position_frame = tk.LabelFrame(self.dialog, text="Window Position", padx=10, pady=10)
        position_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(position_frame, text="X coordinate:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.pos_x_var = tk.StringVar(value=str(self.settings.get("window_x", "")))
        tk.Entry(position_frame, textvariable=self.pos_x_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)
        tk.Label(position_frame, text="(leave empty for auto)").grid(row=0, column=2, sticky=tk.W)
        
        tk.Label(position_frame, text="Y coordinate:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.pos_y_var = tk.StringVar(value=str(self.settings.get("window_y", "")))
        tk.Entry(position_frame, textvariable=self.pos_y_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5)
        tk.Label(position_frame, text="(leave empty for auto)").grid(row=1, column=2, sticky=tk.W)
        
        # Save Format section
        format_frame = tk.LabelFrame(self.dialog, text="Save Settings", padx=10, pady=10)
        format_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(format_frame, text="Default Format:").grid(row=0, column=0, sticky=tk.W)
        self.format_var = tk.StringVar(value=self.settings.get("save_format", "png").upper())
        format_menu = tk.OptionMenu(format_frame, self.format_var, "PNG", "JPEG", "WEBP")
        format_menu.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        tk.Label(format_frame, text="JPEG Quality:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.quality_var = tk.IntVar(value=self.settings.get("jpeg_quality", 90))
        quality_scale = tk.Scale(format_frame, from_=10, to=100, orient=tk.HORIZONTAL, 
                                variable=self.quality_var, length=200)
        quality_scale.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # UI Options
        ui_frame = tk.LabelFrame(self.dialog, text="UI Options", padx=10, pady=10)
        ui_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.toolbar_var = tk.BooleanVar(value=self.settings.get("show_toolbar", True))
        tk.Checkbutton(ui_frame, text="Show toolbar by default", variable=self.toolbar_var).pack(anchor=tk.W)
        
        # Buttons at bottom
        btn_frame = tk.Frame(self.dialog, pady=10)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10)
        
        tk.Button(btn_frame, text="Cancel", command=self.dialog.destroy, width=10, 
                 bg='#666', fg='white').pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Save", command=self._save, width=10,
                 bg='#4a9eff', fg='white').pack(side=tk.RIGHT, padx=5)
    
    def _save(self):
        """Save settings"""
        size_value = self.size_var.get()
        
        if size_value in ["Half Vertical", "Half Horizontal", "Quarter"]:
            self.settings["window_size_mode"] = size_value
        else:
            try:
                w, h = map(int, size_value.split('x'))
                self.settings["window_width"] = w
                self.settings["window_height"] = h
                self.settings["window_size_mode"] = "fixed"
            except:
                pass
        
        try:
            x_str = self.pos_x_var.get().strip()
            y_str = self.pos_y_var.get().strip()
            
            if x_str and y_str:
                self.settings["window_x"] = int(x_str)
                self.settings["window_y"] = int(y_str)
            else:
                self.settings["window_x"] = None
                self.settings["window_y"] = None
        except ValueError:
            messagebox.showwarning("Invalid Input", "X and Y coordinates must be valid numbers")
            return
        
        self.settings["save_format"] = self.format_var.get().lower()
        self.settings["jpeg_quality"] = self.quality_var.get()
        self.settings["show_toolbar"] = self.toolbar_var.get()
        
        settings_file = os.path.join(os.path.dirname(__file__), "watchpoint_settings.json")
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            messagebox.showinfo("Success", "Settings saved!")
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings:\n{str(e)}")


# Node registration
NODE_CLASS_MAPPINGS = {
    "WatchPoint": WatchPoint
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WatchPoint": "👁️ Watch Point"
}