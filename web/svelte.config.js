import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    // SPA mode: emit a static bundle with an index.html fallback so deep links
    // (e.g. /investments/AAPL) resolve client-side. FastAPI serves build/.
    adapter: adapter({ fallback: 'index.html' })
  }
};

export default config;
