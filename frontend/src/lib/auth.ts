import { initializeApp } from "firebase/app";
import {
    getAuth,
    GoogleAuthProvider,
    onAuthStateChanged,
    signInWithPopup,
    signOut,
    type User
} from "firebase/auth";
import { writable } from "svelte/store";
import { baseUrl } from "./config";

const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID;
const apiKey = import.meta.env.VITE_FIREBASE_API_KEY;

// Preparar Firebase con su configuración pública
const firebaseApp = projectId && apiKey ? initializeApp({
    apiKey,
    projectId,
    authDomain: `${projectId}.firebaseapp.com`
}) : null;
const auth = firebaseApp ? getAuth(firebaseApp) : null;

export const editor = writable<User | null>(null);

// Restaurar los permisos de la sesión guardada
if (auth) {
    onAuthStateChanged(auth, async (user) => {
        editor.set(null);

        if (!user) {
            return;
        }

        try {
            const allowed = await checkSession(user);

            if (allowed && auth.currentUser?.uid === user.uid) {
                editor.set(user);
            }
        }
        catch (reason) {
            console.warn((reason as Error).message);
        }
    });
}

// Consultar la autorización que decide el backend
async function checkSession(user: User): Promise<boolean> {
    let response: Response;

    try {
        response = await fetch(`${baseUrl}/auth/session`, {
            headers: { Authorization: `Bearer ${await user.getIdToken()}` },
            signal: AbortSignal.timeout(15000)
        });
    }
    catch {
        throw new Error("No se pudieron verificar tus permisos. Intenta de nuevo.");
    }

    if (!response.ok && ![401, 403].includes(response.status)) {
        throw new Error("No se pudieron verificar tus permisos. Intenta de nuevo.");
    }

    return response.ok;
}

// Abrir Google y comprobar el permiso de edición
export async function login() {
    if (!auth) {
        throw new Error("El inicio de sesión no está disponible.");
    }

    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: "select_account" });
    const { user } = await signInWithPopup(auth, provider);
    const allowed = await checkSession(user);

    if (!allowed) {
        await signOut(auth);
        throw new Error("Esta cuenta no tiene permiso para editar.");
    }
}

// Cerrar la sesión de Firebase
export async function logout() {
    if (auth) {
        await signOut(auth);
    }
}

// Adjuntar un token vigente a las operaciones de escritura
export async function authorization(): Promise<string> {
    await auth?.authStateReady();
    const user = auth?.currentUser;

    if (!user || !user.emailVerified) {
        throw new Error("Inicia sesión para modificar los datos.");
    }

    return `Bearer ${await user.getIdToken()}`;
}
