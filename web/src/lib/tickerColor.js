// Per-ticker label colors, Google-Finance style: a solid colored chip with the
// symbol in it. Recognizable names get their real brand color from a curated
// map; everything else gets a stable color hashed from the symbol so the same
// ticker is always the same color. `textOn` picks black/white for legibility.
//
// NOTE: this is the one sanctioned exception to the "color is data only, chrome
// is never colored" rule (see /design) — ticker badges are brand identifiers.

// Curated brand colors for the names people recognize on sight. Extend freely.
export const TICKER_COLORS = {
  AAPL: '#555555',   // graphite
  TSLA: '#E31937',   // red
  IBM:  '#1F70C1',   // blue
  AMZN: '#E47911',   // amazon orange
  BABA: '#FF6A00',   // alibaba orange
  GOOG: '#4285F4',   // google blue
  GOOGL:'#4285F4',
  MSFT: '#0067B8',   // microsoft blue
  META: '#0866FF',   // meta blue
  NVDA: '#5B8C00',   // nvidia green
  NFLX: '#E50914',   // netflix red
  AMD:  '#ED1C24',
  INTC: '#0071C5',
  DIS:  '#113CCF',
  KO:   '#F40009',
  PEP:  '#004B93',
  NKE:  '#111111',
  SBUX: '#00704A',
  JPM:  '#5C2D91',
  V:    '#1A1F71',
  MA:   '#EB001B',
  PYPL: '#003087',
  UBER: '#000000',
  ABNB: '#FF5A5F',
  SHOP: '#7AB55C',
  CRM:  '#00A1E0',
  ORCL: '#C74634',
  ADBE: '#FA0F00',
  SPOT: '#1DB954',
  COIN: '#0052FF',
  PLTR: '#101113',
  SPY:  '#1F70C1',
  QQQ:  '#5B8def',
  'BTC-USD': '#F7931A',
};

// Design accent deck (app.css) — the fallback palette for unknown tickers.
const ACCENT_DECK = ['#ff90e8', '#ffc900', '#23a094', '#5b8def', '#c994e8', '#ff6e5e'];

// Deterministic string hash (djb2-ish) → stable index into the accent deck.
function hashIndex(str, mod) {
  let h = 5381;
  for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0;
  return Math.abs(h) % mod;
}

export function tickerColor(sym) {
  const s = (sym || '').toUpperCase();
  return TICKER_COLORS[s] ?? ACCENT_DECK[hashIndex(s, ACCENT_DECK.length)];
}

// WCAG relative luminance → white text on dark chips, near-black on light ones.
export function textOn(bg) {
  const hex = (bg || '#000').replace('#', '');
  const n = hex.length === 3 ? hex.split('').map((c) => c + c).join('') : hex;
  const r = parseInt(n.slice(0, 2), 16) / 255;
  const g = parseInt(n.slice(2, 4), 16) / 255;
  const b = parseInt(n.slice(4, 6), 16) / 255;
  const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  return L > 0.5 ? '#1a1a1a' : '#ffffff';
}
