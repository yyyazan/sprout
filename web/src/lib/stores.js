// Shared cross-route state. The sidebar lives in the layout while holdings data
// and the stock-detail / search overlays used to live in the dashboard page;
// these stores let the global rail open the same overlays from any route.
import { writable, get } from 'svelte/store';
import { api } from './api.js';

// Non-joker holding cards powering the sidebar rail. null = not loaded yet.
export const holdings = writable(null);

// Global stock-detail overlay: { ticker, name, holding } | null.
export const detail = writable(null);
// Global ⌘K search palette.
export const searchOpen = writable(false);

// Live intraday moves polled from /api/momentum: { TICKER: { day_pct, week_pct } }.
// The sidebar rail's mover strips read this so they stay live like the old deck.
export const moves = writable({});
let momentumStarted = false;
export function startMomentum() {
  if (momentumStarted) return;
  momentumStarted = true;
  const tick = () => api.momentum().then((m) => moves.set(m.moves ?? {})).catch(() => {});
  tick();
  setInterval(tick, 60_000);
}

let inflight = null;
// Fetch holdings once for the rail. The dashboard page also primes this store
// from its own /dashboard payload (see primeHoldings), so on `/` this usually
// no-ops; on other routes it does the fetch.
export async function loadHoldings(force = false) {
  if (get(holdings) && !force) return;
  if (inflight) return inflight;
  inflight = api
    .dashboard()
    .then((d) => primeHoldings(d.cards))
    .catch(() => {})
    .finally(() => { inflight = null; });
  return inflight;
}

export function primeHoldings(cards) {
  holdings.set((cards ?? []).filter((c) => !c.is_joker));
}

// Watched (non-held) tickers: [{ ticker, name, price, dayPct }] | null = not loaded.
// Shared so the sidebar rail and the stock view's watch toggle stay in sync.
export const watchlist = writable(null);
let wlInflight = null;
export function loadWatchlist(force = false) {
  if (get(watchlist) && !force) return Promise.resolve();
  if (wlInflight) return wlInflight;
  wlInflight = api
    .watchlist()
    .then((w) => watchlist.set(w ?? []))
    .catch(() => {})
    .finally(() => { wlInflight = null; });
  return wlInflight;
}

export async function toggleWatch(ticker, on) {
  const r = await (on ? api.watch(ticker) : api.unwatch(ticker));
  if (r?.watchlist) watchlist.set(r.watchlist);
  return r?.ok ?? false;
}

export function openStock(payload) { detail.set(payload); }
export function closeStock() { detail.set(null); }
export function openSearch() { searchOpen.set(true); }
export function closeSearch() { searchOpen.set(false); }

// Search result → held card when we own it, else a market-only view.
export function openSearchResult(r) {
  searchOpen.set(false);
  const sym = (r.symbol || '').toUpperCase();
  const card = (get(holdings) ?? []).find((c) => c.ticker === sym);
  detail.set({ ticker: r.symbol, name: r.name, holding: card ? cardToHolding(card) : null });
}

// Map a dashboard card → the holding shape StockPanel/StockDetail expect.
export function cardToHolding(c) {
  const invested = c.cost_basis != null && c.shares ? c.cost_basis * c.shares : null;
  return {
    t: c.ticker, name: c.company_name, last: c.current_price, shares: c.shares,
    value: c.market_value, avg: c.cost_basis, pct: c.position_pct,
    gain: invested != null ? c.market_value - invested : null,
    retPct: invested ? (c.market_value / invested - 1) * 100 : null,
    dayMove: c.day_pct ?? 0,
  };
}
