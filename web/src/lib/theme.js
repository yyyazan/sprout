// Light/dark theme — dark is the default (the neo-brutalist dark system); light is
// the original paper palette. Persisted to localStorage, applied as
// html[data-theme] so app.css variable overrides take effect.
import { writable } from 'svelte/store';

const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('sprout-theme') : null;
export const theme = writable(stored === 'light' ? 'light' : 'dark');

theme.subscribe((t) => {
  if (typeof document !== 'undefined') document.documentElement.dataset.theme = t;
  if (typeof localStorage !== 'undefined') localStorage.setItem('sprout-theme', t);
});

export const toggleTheme = () => theme.update((t) => (t === 'dark' ? 'light' : 'dark'));
