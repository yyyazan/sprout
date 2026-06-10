// ⚠️ PLACEHOLDER DATA — front-end only, so we can judge the deep-view layout before
// wiring real data. Everything here is DETERMINISTIC per ticker (seeded PRNG) so it
// never flickers between renders, and every market field is anchored to the real
// current price we already have. SWAP POINT: replace mockStock()/priceSeries() with a
// real `/api/stock/{ticker}` (FastAPI + yfinance: Ticker.info + Ticker.history). The
// returned shapes below are the contract — keep them and only the source changes.

// Sectors for the portfolio's known tickers (yfinance `info.sector` later).
const SECTORS = {
  AAPL: 'Technology', NVDA: 'Technology', GOOG: 'Communication', GOOGL: 'Communication',
  SNOW: 'Technology', RDDT: 'Communication', IONQ: 'Technology', RGTI: 'Technology',
  RKLB: 'Industrials', UNH: 'Healthcare', IBIT: 'Crypto · ETF', VSCO: 'Consumer Disc.',
  AMZN: 'Consumer Disc.', MSFT: 'Technology', TSLA: 'Consumer Disc.', META: 'Communication',
};

function seedOf(s) { let h = 2166136261; for (let i = 0; i < (s || '').length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const lerp = (a, b, t) => a + (b - a) * t;

// Deterministic mock dividend yield (%) per ticker — its OWN seed (salt '|div')
// so it's independent of the price-series PRNG. ~55% of names pay; payers yield
// 0.4%-4.2%. Shared by the deep view's "div yld" stat AND the dividend wraith, so
// the two always agree for a given ticker. SWAP POINT: replace with the real
// yfinance yield (info.dividendYield) alongside the rest of /api/stock.
export function divYieldOf(ticker) {
  const r = mulberry32(seedOf((ticker || '') + '|div'));
  return r() < 0.45 ? 0 : +lerp(0.4, 4.2, r()).toFixed(2);
}

// holding = a card mapped to the holding shape (cardToHolding in stores.js),
// carrying real position fields; mockStock fills any market gaps.
export function mockStock(h) {
  const t = h?.t || '—';
  const price = h?.last ?? 100;
  const r = mulberry32(seedOf(t));
  const dayPct = h?.dayMove ?? 0;
  const prevClose = +(price / (1 + dayPct / 100)).toFixed(2);
  const open = +lerp(prevClose, price, 0.3 + r() * 0.5).toFixed(2);
  const iv = price * (0.005 + r() * 0.02);
  const dayLow = +Math.min(price, open, prevClose, price - iv * r()).toFixed(2);
  const dayHigh = +Math.max(price, open, prevClose, price + iv * r()).toFixed(2);
  const lo52 = +(price * lerp(0.55, 0.9, r())).toFixed(2);
  const hi52 = +(price * lerp(1.05, 1.6, r())).toFixed(2);
  const pe = +lerp(11, 48, r()).toFixed(1);
  const eps = +(price / pe).toFixed(2);
  const shares = h?.shares ?? 0;
  const avgCost = h?.avg ?? null;
  const totalCost = avgCost != null ? +(avgCost * shares).toFixed(2) : null;
  const mktValue = h?.value ?? +(price * shares).toFixed(2);
  const sharesOut = lerp(0.3e9, 6e9, r());
  const marketCap = price * sharesOut;
  const divYield = divYieldOf(t);   // shared with the dividend wraith (see divYieldOf)
  const beta = +lerp(0.7, 2.1, r()).toFixed(2);
  const avgVolume = Math.round(lerp(1.5e6, 45e6, r()));
  const volume = Math.round(avgVolume * lerp(0.5, 1.8, r()));
  const RATINGS = ['Strong Buy', 'Buy', 'Hold', 'Underperform'];
  const rating = RATINGS[Math.floor(r() * RATINGS.length)];
  const target = +(price * lerp(0.85, 1.45, r())).toFixed(2);
  return {
    t, name: h?.name ?? t, sector: SECTORS[t] ?? '—',
    price, dayPct, dayAbs: +(price - prevClose).toFixed(2), prevClose, open,
    dayLow, dayHigh, lo52, hi52,
    shares, avgCost, totalCost, mktValue,
    plAbs: h?.gain ?? null, plPct: h?.retPct ?? null, weight: h?.pct ?? null,
    pe, eps, marketCap, divYield, beta, volume, avgVolume,
    rating, target, upside: +((target / price - 1) * 100).toFixed(1),
    _mock: true,
  };
}

export const fmtCap = (n) => { const a = Math.abs(n); if (a >= 1e12) return (n / 1e12).toFixed(2) + 'T'; if (a >= 1e9) return (n / 1e9).toFixed(2) + 'B'; if (a >= 1e6) return (n / 1e6).toFixed(1) + 'M'; return Math.round(n).toLocaleString(); };
export const fmtVol = (n) => { const a = Math.abs(n); if (a >= 1e9) return (n / 1e9).toFixed(2) + 'B'; if (a >= 1e6) return (n / 1e6).toFixed(2) + 'M'; if (a >= 1e3) return (n / 1e3).toFixed(1) + 'K'; return '' + n; };

// ── price series per range ────────────────────────────────────────────────
// daily ranges use 'YYYY-MM-DD' (business-day) time; intraday ranges use UTC
// timestamps (seconds). Each returns {candles:[{time,open,high,low,close}], area:[{time,value}]}.
const RANGE_CFG = {
  '1D': { bars: 78, stepSec: 300, intraday: true, vol: 0.0016, span: 0.02 },
  '1W': { bars: 40, stepSec: 3600, intraday: true, vol: 0.004, span: 0.06 },
  '1M': { bars: 22, stepDays: 1, intraday: false, vol: 0.012, span: 0.16 },
  '3M': { bars: 64, stepDays: 1, intraday: false, vol: 0.013, span: 0.30 },
  '1Y': { bars: 52, stepDays: 7, intraday: false, vol: 0.020, span: 0.55 },
  '5Y': { bars: 60, stepDays: 30, intraday: false, vol: 0.035, span: 1.20 },
};
export const RANGES = Object.keys(RANGE_CFG);

const ymd = (d) => d.toISOString().slice(0, 10);

export function priceSeries(ticker, range, anchor) {
  const cfg = RANGE_CFG[range] ?? RANGE_CFG['3M'];
  const r = mulberry32(seedOf(ticker + '|' + range));
  const n = cfg.bars;
  const end = anchor ?? 100;
  const start = end * (1 + (r() * 2 - 1) * Math.min(0.9, cfg.span));
  const closes = new Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const drift = lerp(start, end, t);
    const noise = (r() * 2 - 1) * end * cfg.vol * Math.sqrt(n) * (1 - t * 0.4);
    closes[i] = Math.max(0.01, drift + noise);
  }
  closes[n - 1] = end;
  const times = new Array(n);
  if (cfg.intraday) {
    const now = Math.floor(Date.now() / 1000);
    for (let i = 0; i < n; i++) times[i] = now - (n - 1 - i) * cfg.stepSec;
  } else {
    const base = new Date(); base.setUTCHours(0, 0, 0, 0);
    for (let i = 0; i < n; i++) { const d = new Date(base); d.setUTCDate(d.getUTCDate() - (n - 1 - i) * cfg.stepDays); times[i] = ymd(d); }
  }
  const candles = new Array(n), area = new Array(n);
  let prev = closes[0];
  for (let i = 0; i < n; i++) {
    const c = closes[i];
    const o = i === 0 ? c * (1 + (r() * 2 - 1) * cfg.vol) : prev;
    const hi = Math.max(o, c) * (1 + r() * cfg.vol * 1.2);
    const lo = Math.min(o, c) * (1 - r() * cfg.vol * 1.2);
    candles[i] = { time: times[i], open: +o.toFixed(2), high: +hi.toFixed(2), low: +lo.toFixed(2), close: +c.toFixed(2) };
    area[i] = { time: times[i], value: +c.toFixed(2) };
    prev = c;
  }
  return { candles, area, up: end >= start };
}

// Per-holding monthly dividends from real positions x the mock yield above.
// Accepts the dashboard `cards` payload (or any [{ticker|t, company_name|name,
// market_value|value}]). Returns payers only, biggest first, plus the totals the
// wraith's hero shows. SWAP POINT: a real /api/dividends returns this same shape.
export function mockDividends(holdings) {
  const items = (holdings ?? [])
    .filter((h) => h && !h.is_joker)
    .map((h) => {
      const t = h.ticker ?? h.t ?? '-';
      const value = h.market_value ?? h.value ?? 0;
      const yieldPct = divYieldOf(t);
      return { t, name: h.company_name ?? h.name ?? t, value, yieldPct, annual: value * yieldPct / 100, monthly: value * yieldPct / 1200 };
    })
    .filter((d) => d.monthly > 0)
    .sort((a, b) => b.monthly - a.monthly);
  const monthlyTotal = items.reduce((s, d) => s + d.monthly, 0);
  const annualTotal = monthlyTotal * 12;
  const investedValue = items.reduce((s, d) => s + d.value, 0);
  const yieldOnValue = investedValue ? (annualTotal / investedValue) * 100 : 0;
  return { items, monthlyTotal, annualTotal, yieldOnValue };
}
