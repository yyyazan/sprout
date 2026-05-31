// SPA mode: Lightweight Charts and Three.js are browser-only, and a personal dashboard
// doesn't need SSR. Disabling it keeps data-loading simple (fetch in onMount).
export const ssr = false;
export const prerender = false;
