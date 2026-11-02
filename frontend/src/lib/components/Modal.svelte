<script lang="ts">
    // Importar las herramientas y los componentes necesarios
    import { onMount, type Snippet } from "svelte";

    // Recibir los datos y acciones del componente
    let { label, onclose, children }: { label: string; onclose: () => void; children: Snippet } = $props();

    // Guardar los datos y el estado de esta vista
    let dialog: HTMLDialogElement;

    onMount(() => dialog.showModal());
</script>

<!-- Mostrar el contenido dentro de un diálogo -->
<dialog
    class="modal"
    bind:this={dialog}
    aria-labelledby={label}
    oncancel={(event) => {
        event.preventDefault();
        onclose();
    }}
>
    {@render children()}
</dialog>
