import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Relative base so the build works at https://<user>.github.io/<repo>/ without knowing the repo name
export default defineConfig({ base: './', plugins: [svelte()] });
