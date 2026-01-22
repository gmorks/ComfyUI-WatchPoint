import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "WatchPoint.ListCyclerButtons",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "WPSmartListCycler") {
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                onNodeCreated?.apply(this, arguments);

                // Crear el botón de Reset
                const btn = this.addWidget("button", "RESET STATE", "reset", () => {
                    const node_id = this.id;
                    
                    // Llamar a nuestra API personalizada en el servidor
                    api.fetchApi("/wp/list_cycler/reset", {
                        method: "POST",
                        body: JSON.stringify({ node_id }),
                    }).then(response => {
                        if (response.ok) {
                            if (DEBUG) {
                                //alert(`Nodo ${node_id}: Estado del JSON limpiado. En la próxima ejecución se regenerará la lista.`);
                                this.color = "#225522"; // Feedback visual momentáneo
                                setTimeout(() => { this.color = ""; }, 1000);
                            }
                        }
                    });
                });
                
                btn.serialize = false; // No necesitamos guardar el estado del botón
            };
        }
    }
});