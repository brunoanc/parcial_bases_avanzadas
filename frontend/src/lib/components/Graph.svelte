<script lang="ts">
    // Importar las herramientas y los componentes necesarios
    import { onMount } from "svelte";
    import cytoscape, { type Core } from "cytoscape";
    import { graphStyles } from "../graph/styles";
    import { layoutGraph } from "../graph/layout";
    import { nodeLabel, type Finding, type GraphData, type GraphNode } from "../api";

    // Recibir los datos y acciones del componente
    let {
        data,
        highlighted,
        onselect
    }: {
        data: GraphData;
        highlighted: Finding | null;
        onselect: (node: GraphNode | null) => void;
    } = $props();

    // Guardar los datos y el estado de esta vista
    let container: HTMLDivElement;
    let cy = $state.raw<Core | null>(null);
    let overviewPositions: Record<string, { x: number; y: number }> = {};

    // Crear el grafo y registrar sus gestos
    onMount(() => {
        // Acercar o alejar el mapa con la pinza del trackpad
        function zoomTrackpad(event: WheelEvent) {
            // Dejar que Cytoscape maneje la rueda normal
            if (!event.ctrlKey) {
                return;
            }

            event.preventDefault();
            event.stopImmediatePropagation();
            const bounds = container.getBoundingClientRect();
            let delta = event.deltaY;

            // Convertir el desplazamiento por líneas a píxeles
            if (event.deltaMode === 1) {
                delta *= 16;
            }
            else if (event.deltaMode === 2) {
                // Convertir el desplazamiento por páginas a píxeles
                delta *= bounds.height;
            }

            const level = Math.max(
                graph.minZoom(),
                Math.min(graph.maxZoom(), graph.zoom() * Math.exp(-delta * 0.01))
            );
            graph.zoom({
                level,
                renderedPosition: { x: event.clientX - bounds.left, y: event.clientY - bounds.top }
            });
        }

        // Interceptar la pinza del trackpad antes del ajuste de rueda de Cytoscape
        container.addEventListener("wheel", zoomTrackpad, { capture: true, passive: false });
        const graph = cytoscape({
            container,
            style: graphStyles(),
            minZoom: 0.04,
            maxZoom: 2.5,
            wheelSensitivity: 0.2,
            userZoomingEnabled: true,
            userPanningEnabled: true
        });
        cy = graph;
        graph.on("tap", "node", (event) => onselect(event.target.data("node")));
        graph.on("tap", (event) => {
            // Revisar si se tocó un nodo o el fondo
            if (event.target === graph) {
                onselect(null);
            }
        });
        const observer = new ResizeObserver(() => graph.resize());
        observer.observe(container);

        return () => {
            // Liberar los eventos y el grafo al cerrar el componente
            observer.disconnect();
            container.removeEventListener("wheel", zoomTrackpad, true);
            graph.destroy();
        };
    });

    // Encuadrar el mapa o la ruta seleccionada
    function fitView(routeOnly = false) {
        // Esperar a que el grafo esté listo
        if (!cy) {
            return;
        }

        const elements = routeOnly ? cy.elements(".highlighted") : cy.elements();
        cy.fit(elements, 28);

        // Evitar un acercamiento excesivo al encuadrar
        if (cy.zoom() > 1) {
            cy.zoom(1);
            cy.center(elements);
        }
    }

    // Actualizar los nodos y relaciones del mapa
    $effect(() => {
        // Esperar a que el grafo esté listo
        if (!cy) {
            return;
        }

        cy.elements().remove();
        cy.add([
            ...data.nodes.map((node) => ({
                data: {
                    ...node,
                    node,
                    label: node.version
                        ? `${(node.name || node.id).slice(0, 25)}\n${node.version.slice(0, 20)}`
                        : nodeLabel(node).slice(0, 30)
                }
            })),
            ...data.edges.map((edge) => ({ data: { ...edge } }))
        ]);
        overviewPositions = layoutGraph(data, container.clientWidth, container.clientHeight);
        cy.nodes().positions((node) => overviewPositions[node.id()]);
        fitView();
    });

    // Actualizar el camino resaltado al cambiar la selección
    $effect(() => {
        // Esperar a que el grafo esté listo
        if (!cy) {
            return;
        }

        // Reaplicar la selección al cambiar los elementos del grafo
        data;
        cy.elements().removeClass("dimmed highlighted");
        cy.nodes().positions((node) => overviewPositions[node.id()]);

        // Mostrar solo los nodos y conexiones de la ruta
        if (highlighted) {
            const ids = new Set([...highlighted.pathNodeIds, ...highlighted.pathEdgeIds]);
            cy.elements().forEach((element) => {
                // Ocultar los elementos que no pertenecen a la ruta
                element.addClass(ids.has(element.id()) ? "highlighted" : "dimmed");
            });
            highlighted.pathNodeIds.forEach((id, index) => {
                // Colocar cada paso de la ruta de arriba hacia abajo
                cy?.getElementById(id).position({ x: 0, y: index * 110 });
            });
        }

        fitView(Boolean(highlighted));
    });
</script>

<!-- Reservar el espacio donde Cytoscape dibuja el grafo -->
<div
    class="graph-canvas"
    bind:this={container}
    role="img"
    aria-label="Grafo de dependencias interactivo. Selecciona un elemento para ver sus detalles."
></div>
<!-- Ofrecer los controles de zoom y encuadre -->
<div class="graph-controls" aria-label="Controles del grafo">
    <button
        class="tool"
        onclick={() =>
            cy?.zoom({
                level: cy.zoom() * 1.2,
                renderedPosition: { x: container.clientWidth / 2, y: container.clientHeight / 2 }
            })}
        aria-label="Acercar"
    >
        +
    </button>
    <button
        class="tool"
        onclick={() =>
            cy?.zoom({
                level: cy.zoom() / 1.2,
                renderedPosition: { x: container.clientWidth / 2, y: container.clientHeight / 2 }
            })}
        aria-label="Alejar"
    >
        −
    </button>
    <button class="tool fit" onclick={() => fitView(Boolean(highlighted))}>Ajustar vista</button>
</div>
