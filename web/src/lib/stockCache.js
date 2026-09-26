// Shared promise cache for per-symbol market payloads. The stock view, both
// charts' compare menus and the hover prefetch all read through here, so a
// ticker fetched once is instant everywhere for ~5 min (the backend's intraday
// TTL). Failed fetches are evicted so a retry can succeed.
import { api } from './api.js';

const TTL_MS = 5 * 60_000;

function makeCache(fetcher) {
  const map = new Map(); // key → { at, p, v } — v = the settled value once it lands

  function load(maxAge, args) {
    const key = args.join(':');
    const hit = map.get(key);
    if (hit && Date.now() - hit.at < maxAge) return hit.p;
    // a refetch keeps serving the previous value to peek() until the new one lands
    const entry = { at: Date.now(), p: fetcher(...args), v: hit?.v };
    entry.p.then((v) => { entry.v = v; }, () => { if (map.get(key) === entry) map.delete(key); });
    map.set(key, entry);
    return entry.p;
  }

  const get = (...args) => load(TTL_MS, args);
  // same, but refetch if the cached copy is older than maxAge ms
  get.within = (maxAge, ...args) => load(maxAge, args);
  // the value already in hand, synchronously — lets a view paint its first frame from cache
  get.peek = (...args) => {
    const hit = map.get(args.join(':'));
    return hit && Date.now() - hit.at < TTL_MS ? hit.v : undefined;
  };
  return get;
}

export const cachedStock = makeCache((sym) => api.stock(sym));
export const cachedIntraday = makeCache((sym, range) => api.intraday(sym, range));
export const cachedRelated = makeCache((sym) => api.related(sym));

// use:prefetch={ticker} — warm a stock's payloads when the pointer rests on
// something that opens it. 120ms dwell, so sweeping down a list doesn't fan
// out a request per row.
export function prefetch(node, sym) {
  let cur = sym, timer = null;
  const enter = () => {
    clearTimeout(timer);
    timer = setTimeout(() => { if (cur) { cachedStock(cur); cachedRelated(cur); } }, 120);
  };
  const leave = () => clearTimeout(timer);
  node.addEventListener('pointerenter', enter);
  node.addEventListener('pointerleave', leave);
  return {
    update(s) { cur = s; },
    destroy() {
      leave();
      node.removeEventListener('pointerenter', enter);
      node.removeEventListener('pointerleave', leave);
    },
  };
}
