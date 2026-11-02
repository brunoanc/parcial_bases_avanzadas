<script lang="ts">
    // Usar los datos del nodo para mostrar CVSS
    import type { GraphNode } from "../api";

    // Recibir los datos y acciones del componente
    let {
        node,
        source = false,
        score = true
    }: { node: GraphNode; source?: boolean; score?: boolean } = $props();
</script>

<!-- Mostrar la puntuación cuando esté registrada -->
{#if score && node.cvssScore != null}
    <span class="cvss-score" title={node.cvssVector || undefined}>
        {node.cvssVector?.split("/")[0].replace(":", " ") || "CVSS"}
        <strong>{node.cvssScore.toLocaleString("es-MX", { minimumFractionDigits: 1 })}</strong>
    </span>
{/if}

<!-- Enlazar el aviso original del CVE -->
{#if source && node.sourceUrl}
    <a class="advisory-source" href={node.sourceUrl} target="_blank" rel="noreferrer">
        Consultar aviso original ↗
    </a>
{/if}
