import type { StylesheetJson } from "cytoscape";

export function graphStyles(): StylesheetJson {
    const palette = getComputedStyle(document.documentElement);
    const color = (name: string) => palette.getPropertyValue(name).trim();

    return [
        {
            selector: "node",
            style: {
                label: "data(label)",
                color: color("--text"),
                "font-family": "IBM Plex Sans",
                "font-size": 13,
                "text-wrap": "wrap",
                "text-max-width": "160px",
                "text-valign": "bottom",
                "text-margin-y": 6,
                "text-background-color": color("--canvas"),
                "text-background-opacity": 0.9,
                "text-background-padding": "2px",
                "background-color": color("--package-fill"),
                "border-width": 2,
                "border-color": color("--package-stroke"),
                width: 28,
                height: 28,
                shape: "round-rectangle",
                "overlay-opacity": 0
            }
        },
        {
            selector: "node[type = 'Project']",
            style: {
                "background-color": color("--project-fill"),
                "border-color": color("--project-stroke"),
                width: 36,
                height: 36,
                shape: "round-rectangle",
                "font-weight": 600
            }
        },
        {
            selector: "node[type = 'Vulnerability']",
            style: {
                "background-color": color("--vulnerability-fill"),
                "border-color": color("--vulnerability-stroke"),
                shape: "diamond",
                width: 28,
                height: 28,
                color: color("--danger")
            }
        },
        {
            selector: "edge",
            style: {
                width: 1.5,
                "line-color": color("--edge"),
                "target-arrow-color": color("--edge"),
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                "arrow-scale": 0.8
            }
        },
        {
            selector: "edge[type = 'AFFECTED_BY']",
            style: {
                "line-color": color("--vulnerability-stroke"),
                "target-arrow-color": color("--vulnerability-stroke"),
                "line-style": "dashed"
            }
        },
        { selector: ".dimmed", style: { display: "none" } },
        { selector: "node.highlighted", style: { "border-width": 4, "border-color": color("--route") } },
        {
            selector: "edge.highlighted",
            style: { width: 3, "line-color": color("--route"), "target-arrow-color": color("--route") }
        },
        { selector: "node:selected", style: { "border-width": 4, "border-color": color("--text") } }
    ];
}

