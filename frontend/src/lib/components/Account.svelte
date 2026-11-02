<script lang="ts">
    // Consultar la sesión y las acciones de acceso
    import { editor, login, logout } from "../auth";

    // Guardar el estado del inicio de sesión
    let busy = false;
    let error = "";

    // Abrir Google o cerrar la sesión actual
    async function toggleSession() {
        busy = true;
        error = "";

        // Completar la acción elegida con el proveedor de acceso
        try {
            // Elegir entre salir y abrir el acceso de Google
            if ($editor) {
                await logout();
            }
            else {
                await login();
            }
        }
        catch (reason) {
            // Explicar los errores conocidos sin mostrar códigos internos
            const code = (reason as { code?: string }).code;

            // Dejar que el usuario cancele sin mostrar un error
            if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") {
                return;
            }

            error = code === "auth/popup-blocked"
                ? "Permite las ventanas emergentes para iniciar sesión."
                : code ? "No se pudo iniciar sesión. Intenta de nuevo." : (reason as Error).message;
        }
        finally {
            // Volver a habilitar el botón
            busy = false;
        }
    }
</script>

<!-- Mostrar el acceso al final de la navegación -->
<div class="account">
    <!-- Identificar la sesión que tiene permiso de edición -->
    {#if $editor}
        <span class="account-email">{$editor.email}</span>
    {/if}
    <button onclick={toggleSession} disabled={busy}>
        {busy ? "Espera..." : $editor ? "Cerrar sesión" : "Iniciar sesión con Google"}
    </button>
    <!-- Avisar cuando no se pudo completar el acceso -->
    {#if error}
        <p class="inline-error" role="alert">{error}</p>
    {/if}
</div>
