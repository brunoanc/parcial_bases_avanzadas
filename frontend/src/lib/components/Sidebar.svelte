<script lang="ts">
    // Cargar los proyectos y el control de sesión
    import type { GraphNode } from "../api";
    import { editor } from "../auth";
    import Account from "./Account.svelte";

    // Recibir los datos y acciones del componente
    export let projects: GraphNode[];
    export let projectId: string;
    export let view: string;
    export let loading: boolean;
    export let onhome: () => void;
    export let onmanage: () => void;
    export let onproject: (id: string) => void;
</script>

<!-- Mostrar la navegación y los proyectos -->
<aside class="sidebar">
    <a
        class="brand"
        href="/"
        onclick={(event) => {
            // Volver al explorador sin recargar la aplicación
            event.preventDefault();
            onhome();
        }}
        aria-label="Inicio de DependencyGuard"
    >
        <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <rect x="2" y="3" width="10" height="10" rx="2" stroke="currentColor" stroke-width="1.5"></rect>
            <rect x="20" y="19" width="10" height="10" rx="2" stroke="currentColor" stroke-width="1.5"></rect>
            <path d="M12 8h5v16h3" stroke="currentColor" stroke-width="1.5"></path>
        </svg>
        <span>
            Dependency
            <span class="brand-light">Guard</span>
        </span>
    </a>

    <!-- Abrir la administración cuando la sesión permite editar -->
    {#if $editor}
        <nav class="main-nav" aria-label="Navegación principal">
            <button
                class:active={view === "manage"}
                onclick={onmanage}
            >
                Administrar
            </button>
        </nav>
    {/if}

    <div class="projects-heading">
        <span>Proyectos</span>
        <span>{projects.length}</span>
    </div>
    <!-- Elegir el proyecto que se quiere analizar -->
    <div class="project-list" aria-label="Proyectos">
        <!-- Listar los proyectos de la barra lateral -->
        {#each projects as item}
            <button
                class:active={view === "explorer" && projectId === item.id}
                aria-current={view === "explorer" && projectId === item.id ? "true" : undefined}
                onclick={() => onproject(item.id)}
            >
                <span class="project-mark" aria-hidden="true"></span>
                <span>{item.name}</span>
            </button>
        {:else}
            <p class="sidebar-empty">{loading ? "Cargando..." : "Todavía no hay proyectos"}</p>
        {/each}
    </div>

    <Account></Account>
</aside>
