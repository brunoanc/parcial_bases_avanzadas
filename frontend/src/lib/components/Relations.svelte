<script lang="ts">
    // Cargar las consultas y la validación de relaciones
    import { onMount } from "svelte";
    import { request, nodeLabel, nodePath, type GraphNode, type Kind, type Neighbors, type DependencyTarget } from "../api";
    import { validateField, clearValidation } from "../forms";

    // Recibir los datos y acciones del componente
    export let kind: Kind;
    export let relationNode: GraphNode;
    export let packages: GraphNode[];
    export let vulnerabilities: GraphNode[];
    export let initialTarget: DependencyTarget | null;
    export let busy = false;
    export let onchanged: () => Promise<void>;
    export let onreturn: (reanalyze?: boolean) => Promise<void>;
    export let onclose: () => void;

    // Guardar los datos y el estado de esta vista
    let relations: Neighbors = { packages: [], vulnerabilities: [] };
    let targetPackage = "";
    let targetVulnerability = "";
    let replacement = "";
    let replacementSource = initialTarget?.dependencyId || "";
    let error = "";
    let notice = "";

    // Cargar los datos al abrir el componente
    onMount(load);

    // Actualizar los valores que dependen de la selección
    $: currentDependency = relations.packages.find((pkg) => pkg.id === replacementSource);
    $: availableReplacements = packages.filter(
        (pkg) => pkg.id !== relationNode?.id && pkg.id !== replacementSource
    );
    $: otherVersions = availableReplacements.filter(
        (pkg) => pkg.name === currentDependency?.name && pkg.ecosystem === currentDependency?.ecosystem
    );
    $: otherPackages = availableReplacements.filter(
        (pkg) => !otherVersions.some((version) => version.id === pkg.id)
    );

    // Cargar las dependencias y los CVEs del nodo
    async function load() {
        busy = true;
        error = "";

        // Consultar los datos que necesita esta vista
        try {
            relations = await request<Neighbors>(`${nodePath(kind, relationNode.id)}/neighbors`);
        }
        catch (reason) {
            // Mostrar el error de las conexiones
            error = (reason as Error).message;
        }
        finally {
            // Habilitar los controles de relaciones
            busy = false;
        }
    }

    // Agregar, quitar o reemplazar una conexión
    async function changeRelation(
        type: "dependencies" | "affected-by",
        target: string,
        remove = false,
        replacePackageId?: string
    ) {
        // Esperar a que se elija un destino
        if (!target) {
            return;
        }

        const body =
            type === "dependencies"
                ? {
                      sourceType: kind === "projects" ? "project" : "package",
                      sourceId: relationNode.id,
                      targetPackageId: target,
                      ...(replacePackageId ? { replacePackageId } : {})
                  }
                : { packageId: relationNode.id, vulnerabilityId: target };
        busy = true;
        error = "";
        notice = "";

        // Guardar la conexión y actualizar su vista
        try {
            await request(`/${type}`, remove ? "DELETE" : "POST", body);
            await onchanged();
            notice = "Se actualizaron las dependencias.";

            // Volver al análisis al terminar un reemplazo guiado
            if (initialTarget && replacePackageId) {
                await onreturn(true);
            }
            else {
                targetPackage = "";
                targetVulnerability = "";
                replacement = "";
                replacementSource = "";
                await load();
            }
        }
        catch (reason) {
            // Mostrar el error al cambiar la relación
            error = (reason as Error).message;
        }
        finally {
            // Habilitar los controles al terminar el cambio
            busy = false;
        }
    }
</script>

<!-- Editar las conexiones del nodo seleccionado -->
<aside class="relations-panel">
    <!-- Mostrar el error de la operación -->
    {#if error}
        <div class="inline-error" role="alert">
            <p>{error}</p>
            <button onclick={load} disabled={busy}>Intentar de nuevo</button>
        </div>
    {/if}

    <!-- Confirmar que se guardaron los cambios -->
    {#if notice}
        <p class="notice" role="status">{notice}</p>
    {/if}
    <header>
        <div>
            <p class="field-caption">Se usa en</p>
            <h2>{nodeLabel(relationNode)}</h2>
        </div>
        <!-- Cerrar las conexiones abiertas desde el catálogo -->
        {#if !initialTarget}
            <button
                class="text-button"
                onclick={onclose}
                disabled={busy}
            >
                Cerrar
            </button>
        {/if}
    </header>

    <!-- Avisar mientras se cargan las dependencias -->
    {#if busy && !relations.packages.length}
        <p class="empty">Cargando dependencias...</p>
    {/if}

    <!-- Permitir reemplazar una dependencia existente -->
    {#if relations.packages.length}
        <!-- Elegir qué dependencia se reemplaza y por cuál -->
        <form
            class="replacement-form"
            oninvalidcapture={validateField}
            oninputcapture={clearValidation}
            onsubmit={(event) => {
                // Guardar el reemplazo sin recargar la página
                event.preventDefault();
                void changeRelation("dependencies", replacement, false, replacementSource);
            }}
        >
            <label for="replace-source">Dependencia actual</label>
            <select
                id="replace-source"
                bind:value={replacementSource}
                onchange={() => (replacement = "")}
                required
                disabled={busy}
            >
                <option value="">Elige una dependencia</option>
                <!-- Mostrar las dependencias actuales del nodo -->
                {#each relations.packages as pkg}
                    <option value={pkg.id}>
                        {nodeLabel(pkg)}
                    </option>
                {/each}
            </select>
            <label for="replace-target">Reemplazar por</label>
            <select
                id="replace-target"
                bind:value={replacement}
                required
                disabled={busy || !replacementSource}
            >
                <option value="">Elige un reemplazo</option>
                <!-- Dar prioridad a otras versiones del mismo paquete -->
                {#if otherVersions.length}
                    <optgroup label="Otras versiones">
                        <!-- Mostrar las versiones alternativas del mismo paquete -->
                        {#each otherVersions as pkg}
                            <option value={pkg.id}>
                                {nodeLabel(pkg)}
                            </option>
                        {/each}
                    </optgroup>
                {/if}

                <!-- Ofrecer otros paquetes como reemplazo -->
                {#if otherPackages.length}
                    <optgroup label="Otros paquetes">
                        <!-- Mostrar los demás paquetes disponibles -->
                        {#each otherPackages as pkg}
                            <option value={pkg.id}>
                                {nodeLabel(pkg)}
                            </option>
                        {/each}
                    </optgroup>
                {/if}
            </select>
            <footer>
                <!-- Permitir regresar al proyecto sin guardar cambios -->
                {#if initialTarget}
                    <button
                        type="button"
                        onclick={() => onreturn()}
                        disabled={busy}
                    >
                        Cancelar
                    </button>
                {/if}

                <button
                    class="primary"
                    type="submit"
                    disabled={busy || !replacement || !replacementSource}
                >
                    {busy
                        ? "Guardando..."
                        : initialTarget
                          ? "Reemplazar y volver a analizar"
                          : "Reemplazar dependencia"}
                </button>
            </footer>
        </form>
    {/if}

    <!-- Consultar y modificar las conexiones directas -->
    <details class="dependency-tools" open={!initialTarget?.dependencyId}>
        <summary>
            Dependencias <span>{relations.packages.length}</span>
        </summary>
        <!-- Mostrar las dependencias actuales del nodo -->
        {#each relations.packages as pkg}
            <div class="relation-row">
                <code>{nodeLabel(pkg)}</code>
                <button
                    class="text-button danger-text"
                    onclick={() => changeRelation("dependencies", pkg.id, true)}
                    disabled={busy}
                >
                    Quitar
                </button>
            </div>
        {:else}
            <p class="muted">{busy ? "Cargando..." : "Sin dependencias"}</p>
        {/each}

        <label for="dependency">Agregar dependencia</label>
        <select id="dependency" bind:value={targetPackage} disabled={busy}>
            <option value="">Elige un paquete</option>
            <!-- Ofrecer paquetes que todavía no estén conectados -->
            {#each packages.filter((pkg) => pkg.id !== relationNode?.id && !relations.packages.some((item) => item.id === pkg.id)) as pkg}
                <option
                    value={pkg.id}
                >
                    {nodeLabel(pkg)}
                </option>
            {/each}
        </select>
        <button
            onclick={() => changeRelation("dependencies", targetPackage)}
            disabled={busy || !targetPackage}
        >
            Agregar dependencia
        </button>
    </details>

    <!-- Administrar los CVEs asociados a esta versión -->
    {#if kind === "packages"}
        <!-- Consultar y modificar las conexiones directas -->
        <details class="dependency-tools" open={!initialTarget?.dependencyId}>
            <summary>
                Vulnerabilidades <span>{relations.vulnerabilities.length}</span>
            </summary>
            <!-- Mostrar los CVEs asociados al paquete -->
            {#each relations.vulnerabilities as vulnerability}
                <div class="relation-row">
                    <code>{nodeLabel(vulnerability)}</code>
                    <button
                        class="text-button danger-text"
                        onclick={() => changeRelation("affected-by", vulnerability.id, true)}
                        disabled={busy}
                    >
                        Quitar
                    </button>
                </div>
            {:else}
                <p class="muted">
                    {busy ? "Cargando..." : "Sin vulnerabilidades registradas"}
                </p>
            {/each}

            <label for="vulnerability">Agregar vulnerabilidad</label>
            <select id="vulnerability" bind:value={targetVulnerability} disabled={busy}>
                <option value="">Elige una vulnerabilidad</option>
                <!-- Ofrecer CVEs que todavía no estén asociados -->
                {#each vulnerabilities.filter((v) => !relations.vulnerabilities.some((item) => item.id === v.id)) as v}
                    <option
                        value={v.id}
                    >
                        {nodeLabel(v)}
                    </option>
                {/each}
            </select>
            <button
                onclick={() => changeRelation("affected-by", targetVulnerability)}
                disabled={busy || !targetVulnerability}
            >
                Agregar vulnerabilidad
            </button>
        </details>
    {/if}
</aside>
