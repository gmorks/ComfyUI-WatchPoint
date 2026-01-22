import json
import os
import random
from server import PromptServer
from aiohttp import web

DEBUG = True

class WPSmartListCycler:
    def __init__(self):
        self.data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "list_state.json")
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "list_string": ("STRING", {"default": "0,1,2,3,4,5"}),
                "mode": (["increment-wrap", "random-shuffled", "fixed"],),
                "fixed_index": ("INT", {"default": 0, "min": 0, "max": 1000}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("index", "index_as_string")
    FUNCTION = "get_next_value"
    CATEGORY = "WatchPoint/Logic"

    @classmethod
    def IS_CHANGED(s, **kwargs):
        """
        Forzamos a ComfyUI a que ignore la caché de este nodo devolviendo 
        un valor distinto en cada consulta.
        """
        return random.random()

    def load_state(self):
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception: pass
        return {}

    def save_state(self, state):
        try:
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            if DEBUG:
                print(f"WP_Error: Fallo al guardar JSON: {e}")

    def get_next_value(self, list_string, mode, fixed_index, seed, unique_id):
        # 1. Preparar items
        items = [int(x.strip()) for x in list_string.split(",") if x.strip()] or [0]
        state = self.load_state()
        
        if unique_id not in state:
            state[unique_id] = {"last_idx": -1, "shuffled_list": []}
        
        node_state = state[unique_id]
        out_value = items[0]

        # 2. Lógica de selección
        if mode == "fixed":
            idx = fixed_index % len(items)
            out_value = items[idx]
            node_state["last_idx"] = idx

        elif mode == "increment-wrap":
            new_idx = (node_state.get("last_idx", -1) + 1) % len(items)
            out_value = items[new_idx]
            node_state["last_idx"] = new_idx

        elif mode == "random-shuffled":
            shuffled = node_state.get("shuffled_list", [])
            
            # Regenerar bolsa si está vacía o el tamaño de la lista cambió
            if DEBUG:
                print(f"WP_Log: Nodo {unique_id} estado actual: {node_state}")
            if not shuffled or max(shuffled, default=-1) >= len(items):
                shuffled = list(range(len(items)))
                random.shuffle(shuffled)
                if DEBUG:
                    print(f"WP_Log: Nodo {unique_id} barajando nueva lista: {shuffled}" )
            
            idx_to_use = shuffled.pop(0)
            out_value = items[idx_to_use]
            node_state["shuffled_list"] = shuffled
            node_state["last_idx"] = idx_to_use

        # 3. Guardado inmediato
        state[unique_id] = node_state
        self.save_state(state)
        if DEBUG:
            print(f"WP_Log: Nodo {unique_id} ejecutado. Resultado: {out_value}")
        return (int(out_value), str(out_value))

# --- API ENDPOINT (Mismo de antes) ---
@PromptServer.instance.routes.post("/wp/list_cycler/reset")
async def reset_node_state(request):
    json_data = await request.json()
    node_id = str(json_data.get("node_id"))
    temp_instance = WPSmartListCycler()
    state = temp_instance.load_state()
    if node_id in state:
        del state[node_id]
        temp_instance.save_state(state)
        return web.json_response({"status": "success"})
    return web.json_response({"status": "not_found"})

NODE_CLASS_MAPPINGS = {"WPSmartListCycler": WPSmartListCycler}
NODE_DISPLAY_NAME_MAPPINGS = {"WPSmartListCycler": "🔄 Smart List Cycler (WP)"}
