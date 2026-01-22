# nodes/signal_scout.py 
from server import  PromptServer 

class WPSignalScout: 
    @classmethod 
    def INPUT_TYPES(s): 
        return  { 
            "required" : { 
                "text": ("STRING", {"forceInput": True }), 
            }, 
        } 

    RETURN_TYPES = ("STRING" ,) 
    RETURN_NAMES = ("text" ,) 
    FUNCTION = "scout_signal" 
    CATEGORY = "WatchPoint/Debug" 

    def scout_signal(self, text): 
        # Intentamos importar WatchPoint desde el archivo raíz 
        try : 
            from ..watch_point import  WatchPoint 
            WatchPoint.update_all_text(text) 
        except Exception as  e: 
            print(f"WP_Scout Error: No se pudo conectar con la ventana: {e}" ) 
            
        return  (text,) 

NODE_CLASS_MAPPINGS = {"WPSignalScout" : WPSignalScout} 
NODE_DISPLAY_NAME_MAPPINGS = {"WPSignalScout": "📡 WP Signal Scout" }