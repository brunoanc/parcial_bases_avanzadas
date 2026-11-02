<script lang="ts">
    // Cargar las rutas, los detalles y los permisos
    import Cvss from "./Cvss.svelte";
    import { editor } from "../auth";
    import { nodeLabel, severityLabels, type Analysis, type Finding, type GraphData, type GraphNode } from "../api";

    // Recibir los datos y acciones del componente
    export let selected: GraphNode | null;
    export let analysis: Analysis | null;
    export let highlighted: Finding | null;
    export let graph: GraphData;
    export let analyzing: boolean;
    export let projectId: string;
    export let onselect: (node: GraphNode | null) => void;
    export let onhighlight: (finding: Finding) => void;
    export let onedit: (node: GraphNode) => void;
    export let oneditfinding: (finding: Finding) => void;

    // Mostrar las rutas por grupos sin limitar lo que analiza el backend
    const PAGE_SIZE = 20;
    let visibleCount = PAGE_SIZE;
    let previousAnalysis: Analysis | null = null;

    // Empezar desde el primer grupo cuando llega un análisis nuevo
    $: if (analysis !== previousAnalysis) {
        visibleCount = PAGE_SIZE;
        previousAnalysis = analysis;
    }
</script>

<!-- Mostrar detalles y rutas de exposición -->
<aside class="inspector" aria-busy={analyzing}>
    <header class="inspector-heading">
        <h2>{selected ? "Detalles" : "Rutas de exposición"}</h2>
        <!-- Mostrar los detalles del nodo seleccionado -->
        {#if selected}
            <button class="text-button" onclick={() => onselect(null)}>
                Volver a las rutas
            </button>
        {:else if analysis}
            <!-- Mostrar cuántas rutas se encontraron -->
            <span class="count">
                {analysis.findings.length}
            </span>
        {/if}
    </header>
    <!-- Mostrar los detalles del nodo seleccionado -->
    {#if selected}
        <!-- Describir el nodo seleccionado -->
        <div class="node-details">
            <p class="entity-type">
                {selected.type === "PackageVersion"
                    ? "Paquete"
                    : selected.type === "Project"
                      ? "Proyecto"
                      : "Vulnerabilidad"}
            </p>
            <h3>{nodeLabel(selected)}</h3>
            <!-- Mostrar la versión y su ecosistema -->
            {#if selected.version}
                <dl>
                    <dt>Versión</dt>
                    <dd>{selected.version}</dd>
                    <dt>Ecosistema</dt>
                    <dd>{selected.ecosystem}</dd>
                </dl>
            {/if}

            <!-- Mostrar la severidad registrada -->
            {#if selected.severity}
                <span class="severity {selected.severity}">
                    {severityLabels[selected.severity]}
                </span>
            {/if}

            <Cvss node={selected} source></Cvss>
            <!-- Mostrar la descripción del nodo -->
            {#if selected.description}
                <p>{selected.description}</p>
            {/if}

            <!-- Permitir editar las dependencias del nodo -->
            {#if $editor && selected.type !== "Vulnerability"}
                <button
                    onclick={() => selected && onedit(selected)}
                >
                    Editar dependencias
                </button>
            {/if}
        </div>
    {:else if analyzing}
        <!-- Avisar mientras se consultan las rutas -->
        <div class="findings-empty" role="status"><h3>Analizando...</h3></div>
    {:else if !analysis}
        <!-- Indicar que el proyecto está listo para analizar -->
        <div class="findings-empty">
            <h3>{projectId ? "Listo para analizar" : "No has elegido un proyecto"}</h3>
        </div>
    {:else if !analysis.findings.length}
        <!-- Informar cuando el análisis no encuentra rutas registradas -->
        <div class="findings-empty" role="status">
            <h3>Sin vulnerabilidades registradas</h3>
            <p>
                Se revisaron las dependencias alcanzables y los CVEs registrados. Este resultado
                no garantiza que el proyecto sea seguro.
            </p>
        </div>
    {:else}
        <!-- Listar las rutas encontradas por el análisis -->
        <div class="findings-list">
            <!-- Mostrar cada camino hacia una versión vulnerable -->
            {#each analysis.findings.slice(0, visibleCount) as finding}
                <article class="finding" class:selected-finding={highlighted === finding}>
                    <header>
                        <span class="severity {finding.vulnerability.severity}">
                            {severityLabels[finding.vulnerability.severity || ""]}
                        </span>
                        <Cvss node={finding.vulnerability}></Cvss>
                    </header>
                    <h3>{nodeLabel(finding.vulnerability)}</h3>
                    <code>{nodeLabel(finding.package)}</code>
                    <div class="depth">
                        {finding.dependencyDepth === 1
                            ? "Dependencia directa"
                            : `${finding.dependencyDepth} niveles de dependencias`}
                    </div>
                    <!-- Desplegar el recorrido y la acción para corregirlo -->
                    {#if highlighted === finding}
                        <p>{finding.vulnerability.description}</p>
                        <Cvss node={finding.vulnerability} source score={false}></Cvss>
                        <ol class="finding-path">
                            <!-- Mostrar los nodos en el orden del recorrido -->
                            {#each finding.pathNodeIds as id}
                                <li>
                                    {nodeLabel(
                                        graph.nodes.find((node) => node.id === id) || {
                                            id
                                        }
                                    )}
                                </li>
                            {/each}
                        </ol>
                        <!-- Permitir cambios únicamente con la sesión autorizada -->
                        {#if $editor}
                            <button class="primary" onclick={() => oneditfinding(finding)}>
                                Editar dependencia <span aria-hidden="true">→</span>
                            </button>
                        {/if}
                    {:else}
                        <button class="path-action" onclick={() => onhighlight(finding)}>
                            Ver ruta <span aria-hidden="true">→</span>
                        </button>
                    {/if}
                </article>
            {/each}

            <!-- Permitir leer el resto de las rutas ya analizadas -->
            {#if visibleCount < analysis.findings.length}
                <p class="scope-note">
                    Mostrando {visibleCount} de {analysis.findings.length} rutas.
                </p>
                <button onclick={() => visibleCount += PAGE_SIZE}>Mostrar más rutas</button>
            {/if}
        </div>
    {/if}
</aside>
