// Thin typed-ish fetch wrappers around the FastAPI backend. During dev, Vite
// proxies /api → http://localhost:8000 (see vite.config.js), so relative paths
// work both in dev and in a same-origin production deploy.
import { writable } from 'svelte/store';

// Flips true when any data call returns 401 (the server-side password gate);
// the layout overlays the unlock screen. Login responses don't count — a wrong
// password is a failed unlock, not a new lock.
export const locked = writable(false);

function check401(r, path) {
  if (r.status === 401 && !path.startsWith('/auth/')) locked.set(true);
}

async function get(path) {
  const r = await fetch(`/api${path}`);
  check401(r, path);
  if (!r.ok) throw new Error(`GET ${path} → ${r.status}`);
  return r.json();
}

async function del(path) {
  const r = await fetch(`/api${path}`, { method: 'DELETE' });
  check401(r, path);
  if (!r.ok) throw new Error(`DELETE ${path} → ${r.status}`);
  return r.json();
}

async function post(path, body) {
  const r = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  check401(r, path);
  if (!r.ok && r.status >= 500) throw new Error(`POST ${path} → ${r.status}`);
  return r.json();
}

export const api = {
  dashboard: () => get('/dashboard'),
  momentum: () => get('/momentum'),
  stock: (t) => get('/stock/' + encodeURIComponent(t)),
  intraday: (t, range) => get('/stock/' + encodeURIComponent(t) + '/intraday?range=' + encodeURIComponent(range)),
  related: (t) => get('/stock/' + encodeURIComponent(t) + '/related'),
  market: () => get('/market'),
  earnings: () => get('/earnings'),
  watchlist: () => get('/watchlist'),
  watch: (t) => post('/watchlist', { ticker: t }),
  unwatch: (t) => del('/watchlist/' + encodeURIComponent(t)),
  search: (q) => get('/search?q=' + encodeURIComponent(q)),
  investments: () => get('/investments'),
  garden: () => get('/garden'),
  trades: () => get('/trades'),
  transactions: () => get('/transactions'),
  realized: () => get('/realized'),
  addTrade: (body) => post('/trades', body),
  addTransaction: (body) => post('/transactions', body),
  login: (password) => post('/auth/login', { password })
};
