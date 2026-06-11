// Mobile detection for the dashboard's phone experience. A matchMedia-driven
// readable so the layout/page can mount EXACTLY ONE tree (desktop or mobile) —
// CSS-hiding both would double-mount the three.js garden (singleton #garden-root)
// and the charts. 700px matches the sidebar-collapse breakpoint in app.css so
// the CSS and JS worlds flip at the same width.
import { readable } from 'svelte/store';

const QUERY = '(max-width: 700px)';

export const isMobile = readable(false, (set) => {
  if (typeof window === 'undefined') return;
  const mq = window.matchMedia(QUERY);
  set(mq.matches);
  const on = (e) => set(e.matches);
  mq.addEventListener('change', on);
  return () => mq.removeEventListener('change', on);
});
