// watchpoint_floating.js
// Watch Point Floating Preview Integration
// Only captures images from Watch Point nodes
// Configuration via localStorage

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Default configuration
const DEFAULT_CONFIG = {
    window: {
        defaultWidth: 320,
        defaultHeight: 320,
        defaultPosition: "middle-right",
        defaultOpacity: 100
    },
    opacity: {
        levels: [20, 40, 60, 80, 100],
        showIndicator: true,
        indicatorDuration: 1000
    },
    positioning: {
        mode: "snap",
        snapPositions: {
            "top-left": { x: 20, y: 20 },
            "top-center": { x: "center", y: 20 },
            "top-right": { x: "right", y: 20 },
            "middle-left": { x: 20, y: "center" },
            "middle-center": { x: "center", y: "center" },
            "middle-right": { x: "right", y: "center" },
            "bottom-left": { x: 20, y: "bottom" },
            "bottom-center": { x: "center", y: "bottom" },
            "bottom-right": { x: "right", y: "bottom" }
        },
        showPositionIndicator: true,
        positionIndicatorDuration: 800
    },
    ui: {
        showHeader: true,
        showTitle: true,
        showCloseButton: true,
        dragFromAnywhere: false
    },
    shortcuts: {
        toggle: "Ctrl+Alt+KeyW",
        increaseOpacity: "Ctrl+Alt+Equal",
        decreaseOpacity: "Ctrl+Alt+Minus",
        snapUp: "Ctrl+Alt+ArrowUp",
        snapDown: "Ctrl+Alt+ArrowDown",
        snapLeft: "Ctrl+Alt+ArrowLeft",
        snapRight: "Ctrl+Alt+ArrowRight",
        snapToPosition1: "Ctrl+Alt+Numpad1",
        snapToPosition2: "Ctrl+Alt+Numpad2",
        snapToPosition3: "Ctrl+Alt+Numpad3",
        snapToPosition4: "Ctrl+Alt+Numpad4",
        snapToPosition5: "Ctrl+Alt+Numpad5",
        snapToPosition6: "Ctrl+Alt+Numpad6",
        snapToPosition7: "Ctrl+Alt+Numpad7",
        snapToPosition8: "Ctrl+Alt+Numpad8",
        snapToPosition9: "Ctrl+Alt+Numpad9"
    },
    behavior: {
        autoShow: true,
        rememberPosition: false
    }
};

// Configuration loader with localStorage support
function loadConfig() {
    try {
        const saved = localStorage.getItem('watchpoint-floating-config');
        if (saved) {
            const userConfig = JSON.parse(saved);
            console.log("✅ Watch Point Floating: Loaded config from localStorage");
            // Deep merge user config with defaults
            return deepMerge(DEFAULT_CONFIG, userConfig);
        }
    } catch (e) {
        console.warn("⚠️ Watch Point Floating: Error loading localStorage config:", e);
    }
    
    console.log("ℹ️ Watch Point Floating: Using default config");
    return DEFAULT_CONFIG;
}

// Save configuration to localStorage
function saveConfig(config) {
    try {
        localStorage.setItem('watchpoint-floating-config', JSON.stringify(config));
        console.log("✅ Watch Point Floating: Config saved to localStorage");
        return true;
    } catch (e) {
        console.error("❌ Watch Point Floating: Could not save config:", e);
        return false;
    }
}

// Deep merge helper
function deepMerge(target, source) {
    const output = Object.assign({}, target);
    if (isObject(target) && isObject(source)) {
        Object.keys(source).forEach(key => {
            if (isObject(source[key])) {
                if (!(key in target))
                    Object.assign(output, { [key]: source[key] });
                else
                    output[key] = deepMerge(target[key], source[key]);
            } else {
                Object.assign(output, { [key]: source[key] });
            }
        });
    }
    return output;
}

function isObject(item) {
    return item && typeof item === 'object' && !Array.isArray(item);
}

// Main extension
app.registerExtension({
    name: "WatchPoint.FloatingPreview",
    
    async setup() {
        console.log("👁️ Watch Point Floating: Initializing...");
        
        // Load configuration
        const config = loadConfig();
        
        // Create the floating preview window
        const pip = new WatchPointFloatingWindow(config);
        pip.create();
        
        // Listen for execution events
        api.addEventListener("executed", (event) => {
            const { node, output } = event.detail;
            
            // Get the actual node from the workflow
            const workflowNode = app.graph.getNodeById(node);
            
            // Only capture if this is a WatchPoint node
            if (workflowNode && workflowNode.type === "WatchPoint") {
                // Check if floating_preview is enabled
                const floatingEnabled = workflowNode.widgets?.find(w => w.name === "floating_preview")?.value;
                
                if (floatingEnabled && output && output.images && output.images.length > 0) {
                    const imageInfo = output.images[0];
                    pip.updateImage(imageInfo);
                    console.log("👁️ Watch Point Floating: Updated from node", node);
                }
            }
        });
        
        // Add keyboard shortcuts
        window.addEventListener("keydown", (e) => {
            // Check if we're not typing in an input field
            const activeElement = document.activeElement;
            const isTyping = activeElement && (
                activeElement.tagName === 'INPUT' || 
                activeElement.tagName === 'TEXTAREA' || 
                activeElement.isContentEditable
            );
            
            if (isTyping) return;
            
            const key = e.code;
            const shortcut = `${e.ctrlKey ? 'Ctrl+' : ''}${e.altKey ? 'Alt+' : ''}${e.shiftKey ? 'Shift+' : ''}${key}`;
            
            // Toggle preview
            if (shortcut === config.shortcuts.toggle) {
                e.preventDefault();
                e.stopPropagation();
                pip.toggle();
                console.log("🎹 Watch Point Floating: Toggled via", config.shortcuts.toggle);
            }
            
            // Opacity controls
            else if (shortcut === config.shortcuts.increaseOpacity || (e.ctrlKey && e.altKey && e.key === '+')) {
                e.preventDefault();
                e.stopPropagation();
                pip.increaseOpacity();
            }
            else if (shortcut === config.shortcuts.decreaseOpacity || (e.ctrlKey && e.altKey && e.key === '-')) {
                e.preventDefault();
                e.stopPropagation();
                pip.decreaseOpacity();
            }
            
            // Snap positioning - Arrows
            else if (shortcut === config.shortcuts.snapUp) {
                e.preventDefault();
                e.stopPropagation();
                pip.moveRelative('up');
            }
            else if (shortcut === config.shortcuts.snapDown) {
                e.preventDefault();
                e.stopPropagation();
                pip.moveRelative('down');
            }
            else if (shortcut === config.shortcuts.snapLeft) {
                e.preventDefault();
                e.stopPropagation();
                pip.moveRelative('left');
            }
            else if (shortcut === config.shortcuts.snapRight) {
                e.preventDefault();
                e.stopPropagation();
                pip.moveRelative('right');
            }
            
            // Snap positioning - Numpad (absolute)
            else if (shortcut === config.shortcuts.snapToPosition1) {
                e.preventDefault();
                pip.snapToPosition('bottom-left');
            }
            else if (shortcut === config.shortcuts.snapToPosition2) {
                e.preventDefault();
                pip.snapToPosition('bottom-center');
            }
            else if (shortcut === config.shortcuts.snapToPosition3) {
                e.preventDefault();
                pip.snapToPosition('bottom-right');
            }
            else if (shortcut === config.shortcuts.snapToPosition4) {
                e.preventDefault();
                pip.snapToPosition('middle-left');
            }
            else if (shortcut === config.shortcuts.snapToPosition5) {
                e.preventDefault();
                pip.snapToPosition('middle-center');
            }
            else if (shortcut === config.shortcuts.snapToPosition6) {
                e.preventDefault();
                pip.snapToPosition('middle-right');
            }
            else if (shortcut === config.shortcuts.snapToPosition7) {
                e.preventDefault();
                pip.snapToPosition('top-left');
            }
            else if (shortcut === config.shortcuts.snapToPosition8) {
                e.preventDefault();
                pip.snapToPosition('top-center');
            }
            else if (shortcut === config.shortcuts.snapToPosition9) {
                e.preventDefault();
                pip.snapToPosition('top-right');
            }
        }, true);
        
        console.log("⌨️ Watch Point Floating: Keyboard shortcuts registered");
        console.log("   - Toggle:", config.shortcuts.toggle);
        console.log("   - Opacity: Ctrl+Alt+[+/-]");
        console.log("   - Position: Ctrl+Alt+[Arrows] or Ctrl+Alt+[Numpad1-9]");
        
        // Expose global API for configuration
        window.WatchPointFloating = {
            getConfig: () => loadConfig(),
            setConfig: (newConfig) => {
                const merged = deepMerge(DEFAULT_CONFIG, newConfig);
                if (saveConfig(merged)) {
                    console.log("✅ Configuration saved. Reload page to apply changes.");
                    return merged;
                }
                return null;
            },
            resetConfig: () => {
                try {
                    localStorage.removeItem('watchpoint-floating-config');
                    console.log("✅ Watch Point Floating: Config reset to defaults. Reload page to apply.");
                    return true;
                } catch (e) {
                    console.error("❌ Could not reset config:", e);
                    return false;
                }
            },
            showHelp: () => {
                console.log(`
🎨 Watch Point Floating Configuration Help
==========================================

View current config:
  WatchPointFloating.getConfig()

Change settings:
  WatchPointFloating.setConfig({
      window: { 
          defaultWidth: 500, 
          defaultHeight: 500,
          defaultPosition: "top-right",
          defaultOpacity: 80
      },
      shortcuts: {
          toggle: "Ctrl+Alt+KeyP"
      }
  })

Reset to defaults:
  WatchPointFloating.resetConfig()

Available positions:
  top-left, top-center, top-right
  middle-left, middle-center, middle-right
  bottom-left, bottom-center, bottom-right

Note: Reload page after changing config to apply changes.
                `);
            },
            instance: pip
        };
        
        console.log("🔧 Watch Point Floating: Global API exposed as window.WatchPointFloating");
        console.log("   Run WatchPointFloating.showHelp() for configuration help");
    }
});

// Floating Preview Window Class
class WatchPointFloatingWindow {
    constructor(config) {
        this.config = config;
        this.container = null;
        this.img = null;
        this.visible = false;
        this.isDragging = false;
        this.initialX = 0;
        this.initialY = 0;
        
        // Size from config
        this.size = {
            width: config.window.defaultWidth,
            height: config.window.defaultHeight
        };
        
        // Position from config
        this.currentPosition = config.window.defaultPosition;
        const pos = this.calculatePosition(this.currentPosition);
        this.position = pos;
        this.currentX = pos.x;
        this.currentY = pos.y;
        
        // Opacity from config
        this.opacityLevels = config.opacity.levels.map(l => l / 100);
        this.currentOpacityIndex = this.opacityLevels.indexOf(config.window.defaultOpacity / 100);
        if (this.currentOpacityIndex === -1) this.currentOpacityIndex = this.opacityLevels.length - 1;
        
        this.opacityIndicator = null;
        this.positionIndicator = null;
        
        // Snap positions grid (for relative movement)
        this.positionGrid = [
            ['top-left', 'top-center', 'top-right'],
            ['middle-left', 'middle-center', 'middle-right'],
            ['bottom-left', 'bottom-center', 'bottom-right']
        ];
    }
    
    calculatePosition(positionName) {
        const snapPos = this.config.positioning.snapPositions[positionName];
        if (!snapPos) return { x: 20, y: window.innerHeight / 2 - this.size.height / 2 };
        
        let x = snapPos.x;
        let y = snapPos.y;
        
        // Calculate relative positions
        if (x === "center") {
            x = (window.innerWidth - this.size.width) / 2;
        } else if (x === "right") {
            x = window.innerWidth - this.size.width - 20;
        }
        
        if (y === "center") {
            y = (window.innerHeight - this.size.height) / 2;
        } else if (y === "bottom") {
            y = window.innerHeight - this.size.height - 20;
        }
        
        return { x, y };
    }
    
    getCurrentGridPosition() {
        // Find current position in grid
        for (let row = 0; row < this.positionGrid.length; row++) {
            for (let col = 0; col < this.positionGrid[row].length; col++) {
                if (this.positionGrid[row][col] === this.currentPosition) {
                    return { row, col };
                }
            }
        }
        return { row: 1, col: 2 }; // Default to middle-right
    }
    
    moveRelative(direction) {
        const current = this.getCurrentGridPosition();
        let newRow = current.row;
        let newCol = current.col;
        
        switch(direction) {
            case 'up':
                newRow = Math.max(0, current.row - 1);
                break;
            case 'down':
                newRow = Math.min(this.positionGrid.length - 1, current.row + 1);
                break;
            case 'left':
                newCol = Math.max(0, current.col - 1);
                break;
            case 'right':
                newCol = Math.min(this.positionGrid[0].length - 1, current.col + 1);
                break;
        }
        
        const newPosition = this.positionGrid[newRow][newCol];
        this.snapToPosition(newPosition);
    }
    
    snapToPosition(positionName) {
        this.currentPosition = positionName;
        const pos = this.calculatePosition(positionName);
        
        this.currentX = pos.x;
        this.currentY = pos.y;
        
        if (this.container) {
            this.container.style.left = pos.x + "px";
            this.container.style.top = pos.y + "px";
            
            if (this.config.positioning.showPositionIndicator) {
                this.showPositionIndicator(positionName);
            }
        }
    }
    
    showPositionIndicator(positionName) {
        // Remove existing indicator if any
        if (this.positionIndicator) {
            this.positionIndicator.remove();
        }
        
        // Format position name for display
        const displayName = positionName.split('-').map(w => 
            w.charAt(0).toUpperCase() + w.slice(1)
        ).join(' ');
        
        // Create position indicator
        this.positionIndicator = document.createElement("div");
        this.positionIndicator.textContent = displayName;
        this.positionIndicator.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 14px;
            font-weight: bold;
            z-index: 10000;
            pointer-events: none;
        `;
        
        this.container.appendChild(this.positionIndicator);
        
        // Remove indicator after duration
        setTimeout(() => {
            if (this.positionIndicator) {
                this.positionIndicator.remove();
                this.positionIndicator = null;
            }
        }, this.config.positioning.positionIndicatorDuration);
    }
    
    create() {
        // Create container
        this.container = document.createElement("div");
        this.container.id = "watchpoint-floating-preview";
        this.container.style.cssText = `
            position: fixed;
            width: ${this.size.width}px;
            height: ${this.size.height}px;
            left: ${this.position.x}px;
            top: ${this.position.y}px;
            background: #1a1a1a;
            border: 2px solid #444;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            z-index: 9999;
            display: none;
            overflow: hidden;
            resize: both;
            min-width: 160px;
            min-height: 120px;
        `;
        
        let imageContainer;
        
        // Create header if enabled
        if (this.config.ui.showHeader) {
            const header = document.createElement("div");
            header.style.cssText = `
                background: #2a2a2a;
                padding: 8px;
                cursor: move;
                display: flex;
                justify-content: space-between;
                align-items: center;
                user-select: none;
            `;
            
            if (this.config.ui.showTitle) {
                const title = document.createElement("span");
                title.textContent = "👁️ Watch Point";
                title.style.cssText = `
                    color: #fff;
                    font-size: 12px;
                    font-weight: bold;
                `;
                header.appendChild(title);
            }
            
            if (this.config.ui.showCloseButton) {
                const closeBtn = document.createElement("button");
                closeBtn.textContent = "×";
                closeBtn.style.cssText = `
                    background: none;
                    border: none;
                    color: #fff;
                    font-size: 20px;
                    cursor: pointer;
                    padding: 0;
                    width: 20px;
                    height: 20px;
                    line-height: 16px;
                `;
                closeBtn.onclick = () => this.hide();
                header.appendChild(closeBtn);
            }
            
            this.container.appendChild(header);
            this.setupDragging(header);
            
            imageContainer = document.createElement("div");
            imageContainer.style.cssText = `
                width: 100%;
                height: calc(100% - 36px);
                display: flex;
                align-items: center;
                justify-content: center;
                background: #000;
                overflow: hidden;
            `;
        } else {
            // No header - full window is image
            imageContainer = document.createElement("div");
            imageContainer.style.cssText = `
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #000;
                overflow: hidden;
            `;
            
            if (this.config.ui.dragFromAnywhere) {
                this.setupDragging(this.container);
            }
        }
        
        // Create image element
        this.img = document.createElement("img");
        this.img.style.cssText = `
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        `;
        
        // Placeholder text
        const placeholder = document.createElement("div");
        placeholder.id = "watchpoint-placeholder";
        placeholder.textContent = "Waiting for Watch Point...";
        placeholder.style.cssText = `
            color: #666;
            font-size: 14px;
        `;
        
        imageContainer.appendChild(placeholder);
        imageContainer.appendChild(this.img);
        this.container.appendChild(imageContainer);
        document.body.appendChild(this.container);
        
        console.log("✅ Watch Point Floating: Created");
    }
    
    setupDragging(dragElement) {
        dragElement.addEventListener("mousedown", (e) => {
            this.isDragging = true;
            
            const rect = this.container.getBoundingClientRect();
            this.currentX = rect.left;
            this.currentY = rect.top;
            
            this.initialX = e.clientX - this.currentX;
            this.initialY = e.clientY - this.currentY;
            
            document.addEventListener("mousemove", this.drag);
            document.addEventListener("mouseup", this.stopDrag);
        });
    }
    
    drag = (e) => {
        if (!this.isDragging) return;
        
        e.preventDefault();
        this.currentX = e.clientX - this.initialX;
        this.currentY = e.clientY - this.initialY;
        
        this.container.style.left = this.currentX + "px";
        this.container.style.top = this.currentY + "px";
    }
    
    stopDrag = () => {
        this.isDragging = false;
        document.removeEventListener("mousemove", this.drag);
        document.removeEventListener("mouseup", this.stopDrag);
        
        this.position.x = this.currentX;
        this.position.y = this.currentY;
    }
    
    updateImage(imageInfo) {
        if (!this.container) return;
        
        const url = api.apiURL(
            `/view?filename=${encodeURIComponent(imageInfo.filename)}&type=${imageInfo.type}&subfolder=${encodeURIComponent(imageInfo.subfolder || '')}`
        );
        
        this.img.src = url;
        this.img.style.display = "block";
        
        const placeholder = document.getElementById("watchpoint-placeholder");
        if (placeholder) {
            placeholder.style.display = "none";
        }
        
        if (!this.visible && this.config.behavior.autoShow) {
            this.show();
        }
        
        console.log("👁️ Watch Point Floating: Updated image");
    }
    
    show() {
        if (!this.container) return;
        this.container.style.display = "block";
        this.visible = true;
    }
    
    hide() {
        if (!this.container) return;
        this.container.style.display = "none";
        this.visible = false;
    }
    
    toggle() {
        if (this.visible) {
            this.hide();
        } else {
            this.show();
        }
    }
    
    increaseOpacity() {
        if (this.currentOpacityIndex < this.opacityLevels.length - 1) {
            this.currentOpacityIndex++;
            this.applyOpacity();
        }
    }
    
    decreaseOpacity() {
        if (this.currentOpacityIndex > 0) {
            this.currentOpacityIndex--;
            this.applyOpacity();
        }
    }
    
    applyOpacity() {
        if (!this.container) return;
        
        const opacity = this.opacityLevels[this.currentOpacityIndex];
        this.container.style.opacity = opacity;
        
        if (this.config.opacity.showIndicator) {
            this.showOpacityIndicator(opacity);
        }
    }
    
    showOpacityIndicator(opacity) {
        if (this.opacityIndicator) {
            this.opacityIndicator.remove();
        }
        
        this.opacityIndicator = document.createElement("div");
        this.opacityIndicator.textContent = `Opacity: ${Math.round(opacity * 100)}%`;
        this.opacityIndicator.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            z-index: 10000;
            pointer-events: none;
        `;
        
        this.container.appendChild(this.opacityIndicator);
        
        setTimeout(() => {
            if (this.opacityIndicator) {
                this.opacityIndicator.remove();
                this.opacityIndicator = null;
            }
        }, this.config.opacity.indicatorDuration);
    }
}

console.log("✅ Watch Point Floating Extension Loaded");