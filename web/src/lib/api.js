// Thin typed-ish fetch wrappers around the FastAPI backend. During dev, Vite
// proxies /api → http://localhost:8000 (see vite.config.js), so relative paths
// work both in dev and in a same-origin production deploy.

async function get(path) {
  const r = await fetch(`/api${path}`);
  if (!r.ok) throw new Error(`GET ${path} → ${r.status}`);
  return r.json();
}

async function del(path) {
  const r = await fetch(`/api${path}`, { method: 'DELETE' });
  if (!r.ok) throw new Error(`DELETE ${path} → ${r.status}`);
  return r.json();
}

async function post(path, body) {
  const r = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
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
  addTransaction: (body) => post('/transactions', body)
};
