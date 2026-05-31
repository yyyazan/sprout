import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    // During the parallel build, proxy API calls to the FastAPI dev server so
    // the frontend can use relative /api paths (no CORS needed).
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
});
