<script lang="ts">
    // Importar las herramientas y los componentes necesarios
    import { onMount } from "svelte";
    import Graph from "./lib/components/Graph.svelte";
    import Manage from "./lib/views/Manage.svelte";
    import Sidebar from "./lib/components/Sidebar.svelte";
    import ProjectInspector from "./lib/components/ProjectInspector.svelte";
    import {
        request,
        nodePath,
        type Analysis,
        type DependencyTarget,
        type Finding,
        type GraphData,
        type GraphNode
    } from "./lib/api";

    // Guardar los datos y el estado de esta vista
    let view = "explorer";
    let projects: GraphNode[] = [];
    let projectId = "";
    let graph: GraphData = { nodes: [], edges: [] };
    let analysis: Analysis | null = null;
    let highlighted: Finding | null = null;
    let selected: GraphNode | null = null;
    let error = "";
    let loading = true;
    let analyzing = false;
    let manageTarget: DependencyTarget | null = null;
    let loadSequence = 0;

    // Actualizar los valores que dependen de la selección
    $: project = projects.find((item) => item.id === projectId);
    $: dependencyCount = graph.edges.filter((edge) => edge.type === "DEPENDS_ON").length;

    onMount(() => {
        // Cargar los datos al abrir el componente
        void refresh();
    });

    // Actualizar los proyectos y el mapa seleccionado
    async function refresh() {
        error = "";
        loading = true;

        // Pedir la lista de proyectos a la API
        try {
            projects = await request<GraphNode[]>("/projects");

            // Limpiar la selección si el proyecto ya no existe
            if (!projects.some((item) => item.id === projectId)) {
                projectId = "";
            }

            await loadGraph(projectId);
        }
        catch (reason) {
            // Mostrar el motivo por el que no se completó la operación
            error = (reason as Error).message;
        }
        finally {
            // Terminar el estado de carga aunque ocurra un error
            loading = false;
        }
    }

    // Cargar el mapa y descartar resultados anteriores
    async function loadGraph(id: string) {
        const sequence = ++loadSequence;
        projectId = id;
        analysis = null;
        highlighted = null;
        selected = null;
        error = "";
        graph = { nodes: [], edges: [] };

        // Terminar cuando no hay un proyecto seleccionado
        if (!id) {
            loading = false;
            return;
        }

        loading = true;

        // Consultar el mapa del proyecto
        try {
            const result = await request<GraphData>(`${nodePath("projects", id)}/graph`);

            // Aplicar solo el resultado de la selección más reciente
            if (sequence === loadSequence) {
                graph = result;
            }
        }
        catch (reason) {
            // Mostrar el motivo por el que no se completó la operación
            if (sequence === loadSequence) {
                error = (reason as Error).message;
            }
        }
        finally {
            // Terminar el estado de carga aunque ocurra un error
            if (sequence === loadSequence) {
                loading = false;
            }
        }
    }

    // Consultar el mapa y sus rutas vulnerables juntos
    async function analyze() {
        const id = projectId;
        const sequence = loadSequence;
        analyzing = true;
        error = "";
        highlighted = null;
        selected = null;

        // Consultar los datos actuales del análisis
        try {
            // Cargar juntos grafo y análisis para descartar resultados anteriores
            const [newGraph, result] = await Promise.all([
                request<GraphData>(`${nodePath("projects", id)}/graph`),
                request<Analysis>(`${nodePath("projects", id)}/analysis`)
            ]);

            // Aplicar solo el resultado de la selección más reciente
            if (sequence === loadSequence) {
                graph = newGraph;
                analysis = result;
            }
        }
        catch (reason) {
            // Mostrar el motivo por el que no se completó la operación
            if (sequence === loadSequence) {
                analysis = null;
                error = (reason as Error).message;
            }
        }
        finally {
            // Terminar el estado de carga aunque ocurra un error
            analyzing = false;
        }
    }

    // Seleccionar la ruta que se mostrará en el mapa
    function highlight(finding: Finding) {
        highlighted = finding;
        selected = null;
    }

    // Abrir el editor del proyecto o paquete elegido
    function editDependencies(node: GraphNode, dependencyId?: string) {
        manageTarget = { kind: node.type === "Project" ? "projects" : "packages", id: node.id, dependencyId };
        view = "manage";
    }

    // Buscar quién usa la versión vulnerable
    function editFinding(finding: Finding) {
        const edge = finding.pathEdges[finding.pathEdges.length - 2];
        const source = graph.nodes.find((node) => node.id === edge.source);

        // Abrir la dependencia desde el nodo que la utiliza
        if (source) {
            editDependencies(source, finding.package.id);
        }
    }

    // Volver al proyecto y actualizar el análisis si hubo cambios
    async function returnToExplorer(reanalyze = false) {
        view = "explorer";
        manageTarget = null;

        // Repetir el análisis después de una corrección
        if (reanalyze && projectId) {
            await analyze();
        }
    }
</script>

<!-- Organizar la navegación y el área de trabajo -->
<div class="app-shell">
    <Sidebar
        {projects}
        {projectId}
        {view}
        {loading}
        onhome={() => returnToExplorer()}
        onmanage={() => {
            manageTarget = null;
            view = "manage";
        }}
        onproject={(id) => {
            view = "explorer";
            manageTarget = null;
            void loadGraph(id);
        }}
    ></Sidebar>

    <!-- Mostrar la vista activa del proyecto -->
    <main>
        <!-- Mostrar el catálogo o el editor de dependencias -->
        {#if view === "manage"}
            <div class="topbar">
                <button class="text-button back-link" onclick={() => returnToExplorer()}>
                    ← Volver a {project?.name || "proyectos"}
                </button>
            </div>
        {/if}

        <!-- Mostrar el catálogo o el editor de dependencias -->
        {#if view === "manage"}
            <!-- Recrear el editor cuando cambia el nodo seleccionado -->
            {#key manageTarget}
                <Manage onchanged={refresh} initialTarget={manageTarget} onreturn={returnToExplorer}></Manage>
            {/key}
        {:else}
            <!-- Mostrar el proyecto y la acción de análisis -->
            <header class="explorer-heading">
                <h1>{project?.name || "Proyectos"}</h1>
                <!-- Mostrar las herramientas del proyecto seleccionado -->
                {#if projectId}
                    <button
                        class="analyze"
                        class:primary={!analysis}
                        onclick={analyze}
                        disabled={loading || analyzing}
                    >
                        {analyzing ? "Analizando..." : analysis ? "Volver a analizar" : "Analizar proyecto"}
                    </button>
                {/if}
            </header>

            <!-- Mostrar el error de la operación -->
            {#if error}
                <div class="error-banner explorer-error" role="alert">
                    <p>{error}</p>
                    <button onclick={refresh} disabled={loading}>Intentar de nuevo</button>
                </div>
            {/if}

            <div class="explorer-layout" class:awaiting-project={!projectId}>
                <!-- Mostrar el mapa y sus herramientas -->
                <section class="graph-panel" aria-label="Grafo del proyecto">
                    <!-- Mostrar las herramientas del proyecto seleccionado -->
                    {#if projectId}
                        <!-- Mostrar el tamaño del grafo y el control de rutas -->
                        <header class="graph-toolbar">
                            <div class="metrics">
                                <span>
                                    <b>
                                        {graph.nodes.filter((node) => node.type === "PackageVersion").length}
                                    </b>
                                    Paquetes
                                </span>
                                <span>
                                    <b>{dependencyCount}</b>
                                    Dependencias
                                </span>
                            </div>
                            <!-- Permitir volver al mapa completo -->
                            {#if highlighted}
                                <button class="text-button" onclick={() => (highlighted = null)}>
                                    Mostrar todas las rutas
                                </button>
                            {/if}
                        </header>
                    {/if}

                    <div class="graph-stage">
                        <!-- Mostrar el estado de carga antes del contenido -->
                        {#if loading}
                            <div class="graph-empty">
                                <div class="loading-mark"></div>
                                <h2>Cargando...</h2>
                            </div>
                        {:else if !projectId}
                            <!-- Pedir un proyecto antes de mostrar el mapa -->
                            <div class="graph-empty"><h2>Elige un proyecto de la barra lateral</h2></div>
                        {:else if !graph.nodes.length}
                            <!-- Permitir intentar otra vez si no se cargó el mapa -->
                            <div class="graph-empty">
                                <h2>No se pudo cargar este proyecto</h2>
                                <button onclick={() => loadGraph(projectId)}>Intentar de nuevo</button>
                            </div>
                        {:else}
                            <Graph data={graph} {highlighted} onselect={(node) => (selected = node)}></Graph>
                        {/if}
                    </div>
                    <!-- Mostrar las herramientas del proyecto seleccionado -->
                    {#if projectId}
                        <!-- Explicar los colores y gestos del mapa -->
                        <footer class="graph-footer">
                            <div class="legend">
                                <span>
                                    <i class="project-dot"></i>
                                    Proyecto
                                </span>
                                <span>
                                    <i class="package-dot"></i>
                                    Paquete
                                </span>
                                <span>
                                    <i class="vulnerability-dot"></i>
                                    Vulnerabilidad
                                </span>
                            </div>
                        </footer>
                    {/if}
                </section>

                <!-- Mostrar las herramientas del proyecto seleccionado -->
                {#if projectId}
                    <ProjectInspector
                        {selected}
                        {analysis}
                        {highlighted}
                        {graph}
                        {analyzing}
                        {projectId}
                        onselect={(node) => selected = node}
                        onhighlight={highlight}
                        onedit={editDependencies}
                        oneditfinding={editFinding}
                    ></ProjectInspector>
                {/if}
            </div>
        {/if}
    </main>
</div>
