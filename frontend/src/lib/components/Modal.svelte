<script lang="ts">
    // Cargar el montaje y el contenido del diálogo
    import { onMount, type Snippet } from "svelte";

    // Recibir los datos y acciones del componente
    let { label, onclose, children }: { label: string; onclose: () => void; children: Snippet } = $props();

    // Guardar los datos y el estado de esta vista
    let dialog: HTMLDialogElement;

    // Abrir el diálogo cuando se monta el componente
    onMount(() => dialog.showModal());
</script>

<!-- Mostrar el contenido dentro de un diálogo -->
<dialog
    class="modal"
    bind:this={dialog}
    aria-labelledby={label}
    oncancel={(event) => {
        // Aplicar las mismas reglas de cierre al presionar Escape
        event.preventDefault();
        onclose();
    }}
>
    {@render children()}
</dialog>
