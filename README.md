# 👁️ ComfyUI Watch Point

**Dual preview system for ComfyUI workflows**

Watch Point provides two simultaneous preview methods:
- 🖥️ **Monitor Preview**: External Tkinter window on any monitor
- 🖼️ **Floating Preview**: ComfyUI's built-in preview system

## Features

### Monitor Preview (Tkinter)
- 🎯 Display on any connected monitor
- 🔍 Zoom/Pan controls with mouse
- ⌨️ Keyboard shortcuts
- 💾 Save images directly from preview
- 📋 Copy to clipboard
- ⚙️ Customizable settings
- 📡 **Signal Scout Panel**: Display text from your workflow in a side panel.

### Floating Preview (JavaScript)
- 📌 Uses ComfyUI's native preview system
- 🎨 Works with existing preview extensions
- 🔄 Auto-updates during workflow execution

## Installation

1. Clone into your ComfyUI custom_nodes directory:
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yourusername/ComfyUI-WatchPoint.git
```

2. Install dependencies (if needed):
```bash
pip install pillow screeninfo
```

3. Restart ComfyUI

## Nodes

### 👁️ Watch Point
The main preview node.
1. Add **Watch Point** to your workflow.
2. Connect an `IMAGE` input.
3. Enable/disable previews:
   - `floating_preview`: Enable ComfyUI's built-in preview.
   - `monitor_preview`: Enable the external monitor window.
4. Select the target `monitor` from the dropdown.
5. The node acts as a pass-through for the `IMAGE` output.

### 📡 WP Signal Scout
A debug node to send text to the Monitor Preview window.
1. Add **WP Signal Scout** to your workflow (found in `WatchPoint/Debug`).
2. Connect any `STRING` input.
3. The text will appear in the side panel of the external window.

### Example Workflow
```
[Primitive] → [WP Signal Scout]
   (text)          ↓ (sends text to window)

[Load Image] → [Watch Point] → [Upscale] → [Save Image]
                     ↓
              (Dual Preview)
```

## Controls (Monitor Preview)

### Mouse
- **Scroll wheel**: Zoom in/out
- **Left click + drag**: Pan image
- **Right click**: Context menu

### Keyboard
- **R**: Reset zoom and pan
- **T**: Toggle toolbar
- **P**: Toggle Signal Scout panel
- **1**: Zoom 1:1 (100% actual size)
- **ESC**: Close window

### Toolbar Buttons
- **↻ Reset**: Reset zoom and pan
- **⊕ Zoom In**: Increase zoom level
- **⊖ Zoom Out**: Decrease zoom level
- **1:1 (100%)**: View image at actual size
- **Window Size**: Quick resize presets
- **⛶ Fullscreen**: Toggle fullscreen mode
- **⚙ Settings**: Open settings dialog

## Settings

Access settings via the **⚙ Settings** button in the toolbar.

### Window Size
- Fixed sizes: 800x600, 1024x768, 1280x720, 1920x1080
- Dynamic sizes:
  - **Half Vertical**: Half screen width, full height
  - **Half Horizontal**: Full width, half screen height
  - **Quarter**: Half width, half height

### Window Position
- Set exact X, Y coordinates for window placement
- Leave empty for automatic positioning
- Example: X=0, Y=0 for top-left corner

### Save Options
- Default format: PNG, JPEG, or WebP
- JPEG quality slider (10-100)

### UI Options
- Show/hide toolbar by default

All settings are saved to `watchpoint_settings.json`

## Configuration File

Edit `watchpoint_settings.json` to customize defaults:

```json
{
  "window_width": 800,
  "window_height": 600,
  "window_x": null,
  "window_y": null,
  "window_size_mode": "fixed",
  "show_toolbar": true,
  "save_format": "png",
  "jpeg_quality": 90
}
```

### Settings Explained
- `window_x`, `window_y`: Window position (null = auto)
- `window_size_mode`: "fixed", "Half Vertical", "Half Horizontal", or "Quarter"
- `show_toolbar`: Show toolbar on startup
- `save_format`: Default save format ("png", "jpeg", "webp")
- `jpeg_quality`: JPEG compression quality (10-100)

## Use Cases

### Dual Monitor Setup
Perfect for users with multiple monitors:
- Work on ComfyUI on main monitor
- View live preview on secondary monitor
- No need to switch windows or tabs

### Quality Control
Use 1:1 zoom to inspect:
- Image quality at pixel level
- Upscaling artifacts
- Detail preservation

### Live Monitoring
Watch your workflow progress in real-time:
- Both previews update simultaneously
- Choose the view that works best for your setup
- Keep an eye on intermediate results

## Requirements

- Python 3.7+
- tkinter (usually included with Python)
- PIL/Pillow
- screeninfo (optional, for multi-monitor detection)

## Optional Dependencies

For clipboard support (Windows):
```bash
pip install pywin32
```

## Troubleshooting

### Window doesn't appear
- Check if `monitor_preview` is enabled (True)
- Try different monitor selection
- Check console for error messages

### Window appears in wrong location
- Set explicit X, Y coordinates in settings
- Use `window_x: 0, window_y: 0` for top-left

### Image not updating
- Ensure workflow is executing
- Check that image is connected to Watch Point input
- Try disabling/re-enabling monitor preview

### Floating preview not working
- Ensure `floating_preview` is enabled (True)
- Check if other preview extensions are conflicting
- Restart ComfyUI

## Credits

Created for ComfyUI by [Your Name]

## License

MIT License - Feel free to use and modify!