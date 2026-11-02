import type { GraphData, GraphNode } from "../api";

const COLUMN_GAP = 190;
const ROW_GAP = 110;
const LEVEL_GAP = 50;

export function layoutGraph(data: GraphData, width: number, height: number) {
    const depths = new Map<string, number>();
    const root = data.nodes.find((node) => node.type === "Project");
    const queue = root ? [root.id] : [];

    if (root) {
        depths.set(root.id, 0);
    }

    // Recorrer por niveles desde el proyecto
    for (let index = 0; index < queue.length; index++) {
        const source = queue[index];
        const depth = depths.get(source) ?? 0;

        for (const edge of data.edges.filter((edge) => edge.source === source)) {
            if (!depths.has(edge.target)) {
                depths.set(edge.target, depth + 1);
                queue.push(edge.target);
            }
        }
    }

    const levels: GraphNode[][] = [];

    for (const node of data.nodes) {
        const depth = depths.get(node.id) ?? 0;

        if (!levels[depth]) {
            levels[depth] = [];
        }

        levels[depth].push(node);
    }

    // Equilibrar filas y columnas con la proporción del panel
    const aspect = width / Math.max(height, 1);
    const columns = Math.max(1, Math.ceil(Math.sqrt((data.nodes.length * aspect * ROW_GAP) / COLUMN_GAP)));
    const positions: Record<string, { x: number; y: number }> = {};
    let top = 0;

    for (const nodes of levels) {
        nodes.sort((a, b) => a.id.localeCompare(b.id));
        nodes.forEach((node, index) => {
            const row = Math.floor(index / columns);
            const column = index % columns;
            const rowSize = Math.min(columns, nodes.length - row * columns);
            positions[node.id] = {
                x: (column - (rowSize - 1) / 2) * COLUMN_GAP,
                y: top + row * ROW_GAP
            };
        });
        top += Math.ceil(nodes.length / columns) * ROW_GAP + LEVEL_GAP;
    }

    return positions;
}
