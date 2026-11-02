<script lang="ts">
    // Importar las herramientas y los componentes necesarios
    import Modal from "./Modal.svelte";
    import { request, nodePath, severityLabels, type GraphNode, type Kind } from "../api";
    import { validateField, clearValidation } from "../forms";

    // Recibir los datos y acciones del componente
    export let kind: Kind;
    export let node: GraphNode | null;
    export let onsaved: () => Promise<void>;
    export let onclose: () => void;

    // Guardar los datos y el estado de esta vista
    let busy = false;
    let error = "";
    let form = {
        name: node?.name || "",
        description: node?.description || "",
        version: node?.version || "",
        ecosystem: node?.ecosystem || "npm",
        id: node?.id || "",
        severity: node?.severity || "medium",
        cvssScore: node?.cvssScore ?? undefined,
        cvssVector: node?.cvssVector || "",
        sourceUrl: node?.sourceUrl || ""
    };

    // Guardar los datos del formulario y actualizar el catálogo
    async function save(event: SubmitEvent) {
        event.preventDefault();
        let body: Record<string, string | number | null>;

        // Preparar los datos del proyecto
        if (kind === "projects") {
            body = { name: form.name, description: form.description };
        }
        else if (kind === "packages") {
            // Preparar los datos de la versión del paquete
            body = { name: form.name, version: form.version, ecosystem: form.ecosystem };
        }
        else {
            // Preparar los datos del CVE
            body = {
                severity: form.severity,
                description: form.description,
                cvssScore: form.cvssScore ?? null,
                cvssVector: form.cvssVector || null,
                sourceUrl: form.sourceUrl || null
            };

            // Incluir el identificador solo al crear un CVE
            if (!node) {
                body.id = form.id;
            }
        }

        busy = true;
        error = "";

        // Enviar el formulario y refrescar los datos
        try {
            await request(node ? nodePath(kind, node.id) : `/${kind}`, node ? "PATCH" : "POST", body);
            await onsaved();
            onclose();
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

<Modal
    label="form-title"
    onclose={() => {
        if (!busy) onclose();
    }}
>
    <header>
        <h2 id="form-title">
            {node ? "Editar" : "Crear"}
            {kind === "projects"
                ? "proyecto"
                : kind === "packages"
                  ? "versión de paquete"
                  : "vulnerabilidad"}
        </h2>
        <button type="button" class="text-button" onclick={onclose} disabled={busy}>
            Cerrar
        </button>
    </header>
    <!-- Capturar y validar los datos antes de guardarlos -->
    <form onsubmit={save} oninvalidcapture={validateField} oninputcapture={clearValidation}>
        <!-- Mostrar los campos o acciones propios de proyectos y paquetes -->
        {#if kind !== "vulnerabilities"}
            <label for="node-name">Nombre</label>
            <input id="node-name" bind:value={form.name} required maxlength="100">
        {/if}
        <!-- Mostrar los datos y conexiones de la versión -->
        {#if kind === "packages"}
            <!-- Explicar cómo se guarda una versión distinta -->
            {#if node}
                <p class="form-note">
                    Al guardar una versión distinta se conserva la original. Cámbiala desde Dependencias
                    para usar la nueva versión.
                </p>
            {/if}

            <label for="version">Versión</label>
            <input id="version" bind:value={form.version} required maxlength="60">
            <label for="ecosystem">Ecosistema</label>
            <input
                id="ecosystem"
                bind:value={form.ecosystem}
                required
                maxlength="30"
                pattern="[a-z0-9\-]+">
        {:else}
            <!-- Mostrar el identificador y la puntuación del CVE -->
            {#if kind === "vulnerabilities"}
                <label for="demo-id">Identificador</label>
                <input
                    id="demo-id"
                    bind:value={form.id}
                    disabled={!!node}
                    required
                    pattern={"(CVE-[0-9]{4}-[0-9]{4,}|DEMO-[A-Z0-9\\-]+)"}
                    placeholder="CVE-2021-44906"
                    maxlength="60">
                <label for="severity">Severidad</label>
                <select id="severity" bind:value={form.severity}>
                    <!-- Ofrecer los niveles de severidad disponibles -->
                    {#each ["low", "medium", "high", "critical"] as severity}
                        <option value={severity}>
                            {severityLabels[severity]}
                        </option>
                    {/each}
                </select>
                <label for="cvss-score">Puntuación CVSS</label>
                <input
                    id="cvss-score"
                    type="number"
                    min="0"
                    max="10"
                    step="0.1"
                    bind:value={form.cvssScore}>
                <label for="cvss-vector">Vector CVSS</label>
                <input
                    id="cvss-vector"
                    bind:value={form.cvssVector}
                    maxlength="200"
                    placeholder="CVSS:3.1/AV:N/AC:L/…">
                <label for="source-url">Fuente</label>
                <input
                    id="source-url"
                    type="url"
                    pattern="https://.*"
                    bind:value={form.sourceUrl}
                    maxlength="500">
            {/if}

            <label for="description">Descripción</label>
            <textarea
                id="description"
                bind:value={form.description}
                required={kind === "vulnerabilities"}
                maxlength="2000"
                rows="4"></textarea>
        {/if}
        <!-- Mostrar el error de la operación -->
        {#if error}
            <p class="inline-error" role="alert">{error}</p>
        {/if}

        <footer>
            <button type="button" onclick={onclose} disabled={busy}>Cancelar</button>
            <button class="primary" type="submit" disabled={busy}>
                {busy ? "Guardando..." : "Guardar"}
            </button>
        </footer>
    </form>
</Modal>
