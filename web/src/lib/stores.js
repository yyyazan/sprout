// Shared cross-route state. The sidebar lives in the layout while holdings data
// and the stock-detail / search overlays used to live in the dashboard page;
// these stores let the global rail open the same overlays from any route.
import { writable, get } from 'svelte/store';
import { api } from './api.js';

// Non-joker holding cards powering the sidebar rail. null = not loaded yet.
export const holdings = writable(null);

// What each ticker is, where it isn't a plain stock: { VOO: 'index', MUU: 'fund' }.
// Fed by the holding cards, /api/kinds (everything traded or listed), the stock view
// and search results; TickerBadge reads it. Mirrored to localStorage so a reload
// doesn't flash fund badges solid while the first fetch lands.
const KINDS_KEY = 'sprout-kinds';
function seededKinds() {
  try { return JSON.parse(localStorage.getItem(KINDS_KEY)) ?? {}; } catch { return {}; }
}
export const kinds = writable(typeof localStorage === 'undefined' ? {} : seededKinds());
// map: { TICKER: 'stock' | 'index' | 'fund' }; 'stock' clears an entry. keepKnown = a hint
// (a search result's ETF flag) that must not overwrite a real classification.
export function noteKinds(map, keepKnown = false) {
  if (!map) return;
  kinds.update((cur) => {
    const next = { ...cur };
    for (const [t, k] of Object.entries(map)) {
      if (keepKnown && next[t]) continue;
      if (!k || k === 'stock') delete next[t]; else next[t] = k;
    }
    try { localStorage.setItem(KINDS_KEY, JSON.stringify(next)); } catch { /* private mode */ }
    return next;
  });
}
// search results flag ETFs/mutual funds; that's only a hint (index vs other fund needs the
// category), so it never overwrites what we already know
export function noteSearchKinds(results) {
  noteKinds(Object.fromEntries((results ?? []).map((r) => [r.symbol, r.kind])), true);
}
export function loadKinds() {
  return api.kinds().then(noteKinds).catch(() => {});
}

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

// All-time time-weighted return (%) and the gap to SPY (pp), from the dashboard
// payload's cumulative TWR series. Null when there's no data yet.
export function allTimeReturn(twr) {
  const last = (xy) => { const y = xy?.y ?? []; for (let i = y.length - 1; i >= 0; i--) if (y[i] != null) return y[i] * 100; return null; };
  const ret = last(twr?.portfolio), spy = last(twr?.spy);
  return { ret, vsSpy: ret != null && spy != null ? ret - spy : null };
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
  const held = (cards ?? []).filter((c) => !c.is_joker);
  holdings.set(held);
  noteKinds(Object.fromEntries(held.map((c) => [c.ticker, c.kind ?? 'stock'])));
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

// Sidebar lists: [{ id, name, items: [{ ticker, name, price, dayPct, weekPct,
// monthPct, spark }] }] | null = not loaded. Shared by the sidebar, the stock
// view's list picker and the phone Holdings pane.
export const lists = writable(null);
let lsInflight = null;
export function loadLists(force = false) {
  if (get(lists) && !force) return Promise.resolve();
  if (lsInflight) return lsInflight;
  lsInflight = api
    .lists()
    .then((l) => lists.set(l ?? []))
    .catch(() => {})
    .finally(() => { lsInflight = null; });
  return lsInflight;
}

// Every write shows the new state at once, then swaps in the server's
// hydrated copy. `seq` drops a slow response that a newer write superseded;
// a failed write reloads the truth.
let lsSeq = 0;
async function commitLists(next, request) {
  const mine = ++lsSeq;
  if (next) lists.set(next);
  try {
    const r = await request();
    if (mine === lsSeq && r?.lists) lists.set(r.lists);
    return r;
  } catch {
    if (mine === lsSeq) loadLists(true);
    return null;
  }
}

const layoutOf = (ls) => ls.map((L) => ({ id: L.id, tickers: L.items.map((i) => i.ticker) }));
export const saveLists = (next) => commitLists(next, () => api.setLayout(layoutOf(next)));

export async function createList(name, tickers = []) {
  const r = await commitLists(null, () => api.createList(name, tickers));
  return r?.id ?? null;
}
export function renameList(id, name) {
  const next = (get(lists) ?? []).map((L) => (L.id === id ? { ...L, name } : L));
  return commitLists(next, () => api.renameList(id, name));
}
export function deleteList(id) {
  return commitLists((get(lists) ?? []).filter((L) => L.id !== id), () => api.deleteList(id));
}

// A row for a ticker about to land in a list, before the server hydrates it:
// reuse one from another list, else build it from the holding + live move.
export function rowFor(ticker) {
  for (const L of get(lists) ?? []) {
    const hit = L.items.find((i) => i.ticker === ticker);
    if (hit) return hit;
  }
  const c = (get(holdings) ?? []).find((h) => h.ticker === ticker);
  const m = get(moves)[ticker];
  return {
    ticker, name: c?.company_name ?? ticker, price: m?.spot ?? c?.current_price ?? null,
    dayPct: m?.day_pct ?? c?.day_pct ?? null, weekPct: m?.week_pct ?? c?.week_pct ?? null,
    monthPct: m?.month_pct ?? null, spark: m?.spark ?? [],
  };
}

export function setMembership(ticker, listId, on) {
  const next = (get(lists) ?? []).map((L) => {
    if (L.id !== listId) return L;
    const items = L.items.filter((i) => i.ticker !== ticker);
    return { ...L, items: on ? [...items, rowFor(ticker)] : items };
  });
  return saveLists(next);
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
