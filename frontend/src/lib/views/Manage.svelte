<script lang="ts">
    // Importar las herramientas y los componentes necesarios
    import { onMount } from "svelte";
    import Cvss from "../components/Cvss.svelte";
    import Modal from "../components/Modal.svelte";
    import NodeForm from "../components/NodeForm.svelte";
    import Relations from "../components/Relations.svelte";
    import { request, nodeLabel, severityLabels, nodePath, type GraphNode, type Kind, type DependencyTarget } from "../api";

    // Recibir los datos y acciones del componente
    export let onchanged: () => Promise<void>;
    export let initialTarget: DependencyTarget | null = null;
    export let onreturn: (reanalyze?: boolean) => Promise<void>;

    // Nombrar los catálogos en la interfaz
    const catalogLabels: Record<Kind, string> = {
        projects: "Proyectos",
        packages: "Paquetes",
        vulnerabilities: "Vulnerabilidades"
    };

    // Guardar los datos y el estado de esta vista
    let kind: Kind = initialTarget?.kind || "projects";
    let records: GraphNode[] = [];
    let packages: GraphNode[] = [];
    let vulnerabilities: GraphNode[] = [];
    let loading = true;
    let busy = false;
    let error = "";
    let notice = "";
    let editing: GraphNode | null = null;
    let formOpen = false;
    let deleting: GraphNode | null = null;
    let relationNode: GraphNode | null = null;

    // Cargar los datos al abrir el componente
    onMount(initialize);

    // Cargar el catálogo y abrir el nodo solicitado
    async function initialize() {
        await load();

        // Buscar el nodo que se pidió editar
        if (initialTarget && !error) {
            relationNode = records.find((item) => item.id === initialTarget?.id) || null;

            // Avisar si el nodo dejó de estar disponible
            if (!relationNode) {
                error = "Esta dependencia ya no está disponible.";
            }
        }
    }

    // Cargar los registros y las opciones de relaciones
    async function load() {
        loading = true;
        error = "";

        // Consultar los datos que necesita esta vista
        try {
            const packageRequest = request<GraphNode[]>("/packages");
            const vulnerabilityRequest = request<GraphNode[]>("/vulnerabilities");
            const catalogRequest =
                kind === "packages"
                    ? packageRequest
                    : kind === "vulnerabilities"
                      ? vulnerabilityRequest
                      : request<GraphNode[]>("/projects");
            [records, packages, vulnerabilities] = await Promise.all([
                catalogRequest,
                packageRequest,
                vulnerabilityRequest
            ]);
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

    // Cambiar el tipo de catálogo y cerrar las relaciones
    async function switchKind(next: Kind) {
        kind = next;
        relationNode = null;
        notice = "";
        await load();
    }

    // Preparar el formulario para crear o editar
    function openForm(node: GraphNode | null = null) {
        editing = node;
        error = "";
        formOpen = true;
    }

    // Actualizar el catálogo y la lista de proyectos
    async function changed() {
        await load();
        await onchanged();
    }

    // Confirmar que se guardaron los datos
    async function saved() {
        await changed();
        notice = kind === "packages" && editing
            ? "Se guardó la versión. Cámbiala desde Dependencias para usarla en un proyecto."
            : "Se guardaron los cambios.";
    }

    // Eliminar el nodo seleccionado y actualizar las listas
    async function remove() {
        // Terminar si no hay un nodo elegido para eliminar
        if (!deleting) {
            return;
        }

        busy = true;
        error = "";
        notice = "";
        const id = deleting.id;

        // Pedir la eliminación del nodo
        try {
            await request(nodePath(kind, id), "DELETE");
            await changed();
            deleting = null;
            notice = "Se eliminó el registro. Las dependencias compartidas se conservaron.";

            // Cerrar las relaciones del nodo eliminado
            if (relationNode?.id === id) {
                relationNode = null;
            }
        }
        catch (reason) {
            // Mostrar el motivo por el que no se completó la operación
            error = (reason as Error).message;
        }
        finally {
            // Terminar el estado de carga aunque ocurra un error
            busy = false;
        }
    }
</script>

<!-- Mostrar el catálogo o el editor solicitado -->
<section class="manage-view" class:focused-editor={initialTarget}>
    <header class="page-heading">
        <h1>{initialTarget ? "Editar dependencia" : "Administrar"}</h1>
        <!-- Mostrar las herramientas del catálogo completo -->
        {#if !initialTarget}
            <button class="primary" disabled={busy || loading} onclick={() => openForm()}>
                Crear {kind === "projects" ? "proyecto" : kind === "packages" ? "paquete" : "vulnerabilidad"}
            </button>
        {/if}
    </header>

    <!-- Mostrar las herramientas del catálogo completo -->
    {#if !initialTarget}
        <!-- Elegir el tipo de nodo que se administra -->
        <nav class="tabs" aria-label="Catálogo">
            <!-- Permitir cambiar entre los tres catálogos -->
            {#each ["projects", "packages", "vulnerabilities"] as tab}
                <button
                    class:active={kind === tab}
                    disabled={busy || loading}
                    onclick={() => switchKind(tab as Kind)}
                >
                    {catalogLabels[tab as Kind]}
                </button>
            {/each}
        </nav>
    {/if}

    <!-- Mostrar el error de la operación -->
    {#if error}
        <div class="error-banner" role="alert">{error}</div>
    {/if}
    <!-- Confirmar que se guardaron los cambios -->
    {#if notice}
        <div class="notice" role="status">{notice}</div>
    {/if}

    <div class="catalog-layout" class:with-relations={relationNode && !initialTarget}>
        <!-- Mostrar las herramientas del catálogo completo -->
        {#if !initialTarget}
            <!-- Mostrar los registros del catálogo seleccionado -->
            <div class="catalog">
                <div class="table-caption">
                    <span>Total: {records.length}</span>
                    <button class="text-button" onclick={load} disabled={loading || busy}>Actualizar</button>
                </div>
                <!-- Mostrar el estado de carga antes del contenido -->
                {#if loading}
                    <p class="empty">Cargando...</p>
                {:else if !records.length}
                    <!-- Avisar que el catálogo está vacío -->
                    <p class="empty">
                        Todavía no hay {catalogLabels[kind].toLocaleLowerCase("es-MX")}.
                    </p>
                {:else}
                    <!-- Mostrar los registros y sus acciones -->
                    {#each records as node (node.id)}
                        <article class="record" class:chosen={relationNode?.id === node.id}>
                            <div class="record-info">
                                <strong>{nodeLabel(node)}</strong>
                                <Cvss {node}></Cvss>
                                <!-- Mostrar el ecosistema del paquete -->
                                {#if node.ecosystem}
                                    <span class="record-meta">{node.ecosystem}</span>
                                {/if}
                                <!-- Mostrar la descripción del registro -->
                                {#if node.description}
                                    <p>{node.description}</p>
                                {/if}
                                <!-- Mostrar la severidad del CVE -->
                                {#if node.severity}
                                    <span class="severity {node.severity}">
                                        {severityLabels[node.severity]}
                                    </span>
                                {/if}
                            </div>
                            <div class="row-actions">
                                <!-- Mostrar los campos o acciones propios de proyectos y paquetes -->
                                {#if kind !== "vulnerabilities"}
                                    <button
                                        onclick={() => relationNode = node}
                                        disabled={busy}
                                    >
                                        Dependencias
                                    </button>
                                {/if}

                                <button onclick={() => openForm(node)} disabled={busy}>Editar</button>
                                <button class="danger-text" onclick={() => (deleting = node)} disabled={busy}>
                                    Eliminar
                                </button>
                            </div>
                        </article>
                    {/each}
                {/if}
            </div>
        {:else if loading}
            <!-- Mostrar el estado de carga antes del contenido -->
            <p class="empty">Cargando dependencia...</p>
        {/if}

        <!-- Abrir las conexiones del nodo elegido -->
        {#if relationNode}
            <!-- Recrear el editor cuando cambia el nodo seleccionado -->
            {#key relationNode.id}
                <Relations
                    {kind}
                    {relationNode}
                    {packages}
                    {vulnerabilities}
                    {initialTarget}
                    bind:busy
                    onchanged={changed}
                    {onreturn}
                    onclose={() => relationNode = null}
                ></Relations>
            {/key}
        {:else if initialTarget && !loading && error}
            <!-- Permitir volver a cargar el nodo solicitado -->
            <button onclick={initialize}>Intentar de nuevo</button>
        {/if}
    </div>
</section>

<!-- Abrir el formulario de creación o edición -->
{#if formOpen}
    <NodeForm {kind} node={editing} onsaved={saved} onclose={() => formOpen = false}></NodeForm>
{/if}

<!-- Pedir confirmación antes de eliminar el nodo -->
{#if deleting}
    <Modal
        label="delete-title"
        onclose={() => {
            if (!busy) deleting = null;
        }}
    >
        <h2 id="delete-title">¿Eliminar {nodeLabel(deleting)}?</h2>
        <p>Se eliminarán este registro y sus conexiones. Las dependencias compartidas se conservarán.</p>
        <!-- Mostrar el error de la operación -->
        {#if error}
            <p class="inline-error" role="alert">{error}</p>
        {/if}

        <footer>
            <button onclick={() => (deleting = null)} disabled={busy}>Cancelar</button>
            <button class="danger" onclick={remove} disabled={busy}>
                {busy ? "Eliminando..." : "Eliminar registro"}
            </button>
        </footer>
    </Modal>
{/if}
