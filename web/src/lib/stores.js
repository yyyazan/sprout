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
// The sidebar rail's mover strips read this so they stay live. Polling pauses
// while the tab is hidden (no point quoting a backgrounded glance app) and
// resumes with an immediate tick on refocus if the data has gone stale.
const MOMENTUM_MS = 60_000;
export const moves = writable({});

// Aggregate intraday day-change ($ and %) across the non-joker holdings, using
// the live momentum move when present and the frozen card day_pct as fallback.
// Each holding's prior value is backed out from its current market value and
// day %, so the totals stay correct across mixed up/down moves.
export function portfolioDayMove(cards, liveMoves = {}) {
  let curr = 0, prev = 0;
  for (const c of cards ?? []) {
    if (c.is_joker) continue;
    const mv = c.market_value ?? 0;
    const live = liveMoves[c.ticker];
    const r = ((live ? live.day_pct : c.day_pct) ?? 0) / 100;
    curr += mv;
    prev += r > -1 ? mv / (1 + r) : mv;
  }
  const gain = curr - prev;
  return { gain, pct: prev > 0 ? (gain / prev) * 100 : 0 };
}
let momentumStarted = false;
export function startMomentum() {
  if (momentumStarted) return;
  momentumStarted = true;
  let lastTick = 0;
  const tick = () => {
    lastTick = Date.now();
    return api.momentum().then((m) => moves.set(m.moves ?? {})).catch(() => {});
  };
  const loop = () => {
    if (!document.hidden) tick();
    setTimeout(loop, MOMENTUM_MS);
  };
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && Date.now() - lastTick > MOMENTUM_MS) tick();
  });
  loop();
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

// Trade history (newest first) — shared by the trade ticket tile and the mobile
// log pane so the same page doesn't fetch /api/trades twice. null = not loaded.
export const trades = writable(null);
let trInflight = null;
export function loadTrades(force = false) {
  if (get(trades) && !force) return Promise.resolve();
  if (trInflight) return trInflight;
  trInflight = api
    .trades()
    .then((t) => trades.set(t ?? []))
    .catch(() => {})
    .finally(() => { trInflight = null; });
  return trInflight;
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
