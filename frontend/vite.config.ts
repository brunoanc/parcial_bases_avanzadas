import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
    plugins: [svelte()],
    envDir: "..",
    build: {
        rollupOptions: {
            output: {
                manualChunks: { graph: ["cytoscape"] }
            }
        }
    }
});
