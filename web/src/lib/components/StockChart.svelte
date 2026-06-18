<script>
  // Google-Finance-style chart shell: a top toolbar (chart type · compare ·
  // indicators) → the price chart with a volume histogram + previous-close
  // reference line → GF range tabs (1D 5D 1M 6M YTD 1Y 5Y MAX). Real closes
  // when `history` is supplied, intraday from /api/stock for 1D/5D, else a
  // deterministic mock. Crosshair reads price+date; click-drag measures a span.
  //
  // NOTE: per-bar volume isn't in the data feed yet, so the volume histogram is
  // a deterministic client-side mock (clearly a visual scaffold). Real volume is
  // a backend follow-up; the histogram swaps in transparently once it lands.
  import { onMount } from 'svelte';
  import { createChart, AreaSeries, CandlestickSeries, LineSeries, HistogramSeries, ColorType, CrosshairMode, LineStyle, PriceScaleMode, createSeriesMarkers } from 'lightweight-charts';
  import { priceSeries } from '$lib/mockStock.js';
  import { api } from '$lib/api.js';
  import { cachedStock, cachedIntraday } from '$lib/stockCache.js';
  import { theme } from '$lib/theme.js';
  import { trades as tradesStore, loadTrades } from '$lib/stores.js';

  let { ticker = '—', history = null, price = 100 } = $props();

  // GF range set. days = lookback window for daily-history slicing; intraday =
  // which /api/stock intraday feed (else null → daily); mock = mockStock key.
  const RANGES = [
    { k: '1D',  days: 3,    intraday: '1d', mock: '1D' },
    { k: '5D',  days: 9,    intraday: '1w', mock: '1W' },
    { k: '1M',  days: 33,   intraday: null, mock: '1M' },
    { k: '6M',  days: 190,  intraday: null, mock: '3M' },
    { k: 'YTD', days: null, intraday: null, mock: '1Y' },
    { k: '1Y',  days: 370,  intraday: null, mock: '1Y' },
    { k: '2Y',  days: 740,  intraday: null, mock: '5Y' },
    { k: '3Y',  days: 1100, intraday: null, mock: '5Y' },
    { k: '5Y',  days: 1850, intraday: null, mock: '5Y' },
    { k: 'MAX', days: Infinity, intraday: null, mock: '5Y' },
  ];

  let range = $state('1D');
  let panBars = $state(0);            // bars the fixed-width window is shifted back
  let chartType = $state('area');     // 'area' | 'candles' | 'line'
  let showVolume = $state(true);
  let sma50 = $state(false);
  let sma200 = $state(false);
  let showTrades = $state(true);      // overlay my buy/sell fills as markers
  let openMenu = $state(null);        // 'type' | 'compare' | 'indicators' | null
  const cfg = $derived(RANGES.find((r) => r.k === range) ?? RANGES[0]);

  const TYPE_LABEL = { area: 'Area', candles: 'Candlestick', line: 'Line' };

  // ── compare: overlay any tickers on the chart ──
  // Quick picks + a search box (same /api/search the palette uses). While ≥1
  // compare is active the right price scale flips to Percentage mode, so every
  // series is rebased to the window start — the Google Finance read.
  const QUICK_COMPARES = [
    { sym: 'SPY', label: 'S&P 500' },
    { sym: 'QQQ', label: 'Nasdaq 100' },
    { sym: 'BTC-USD', label: 'Bitcoin' },
  ];
  const CMP_COLORS = ['#5b8def', '#ff90e8', '#ffc900', '#c994e8', '#ff6e5e'];
  const CMP_MAX = 4;

  let compares = $state([]);     // [{ sym, label, color }]
  let cmpData = $state({});      // sym → [{ time, value }] for the current range
  let cmpQ = $state('');
  let cmpResults = $state([]);
  let cmpLoading = $state(false);

  const compared = (sym) => compares.some((c) => c.sym === sym);
  function toggleCompare(sym, label) {
    const s = (sym || '').toUpperCase();
    if (s === (ticker || '').toUpperCase()) return;            // never compare with itself
    if (compared(s)) { compares = compares.filter((c) => c.sym !== s); return; }
    if (compares.length >= CMP_MAX) return;
    const used = new Set(compares.map((c) => c.color));
    compares = [...compares, { sym: s, label: label ?? s, color: CMP_COLORS.find((c) => !used.has(c)) ?? CMP_COLORS[0] }];
    cmpQ = '';
    cmpResults = [];
  }

  // debounced ticker search for the compare menu (180ms, stale-proof)
  let cmpSeq = 0, cmpTimer = null;
  $effect(() => {
    const q = cmpQ.trim();
    if (cmpTimer) clearTimeout(cmpTimer);
    if (!q) { cmpResults = []; cmpLoading = false; return; }
    cmpLoading = true;
    const mine = ++cmpSeq;
    cmpTimer = setTimeout(async () => {
      try {
        const r = await api.search(q);
        if (mine !== cmpSeq) return;
        cmpResults = (r.results ?? []).slice(0, 6);
      } catch {
        if (mine === cmpSeq) cmpResults = [];
      } finally {
        if (mine === cmpSeq) cmpLoading = false;
      }
    }, 180);
  });

  // fetch each compared ticker's points for the current range (shared module
  // cache: daily history once per symbol, intraday once per symbol+feed)
  $effect(() => {
    const list = compares, c = cfg;
    if (!list.length) { cmpData = {}; return; }
    let cancelled = false;
    (async () => {
      const out = {};
      await Promise.all(list.map(async ({ sym }) => {
        try {
          if (c.intraday) {
            const r = await cachedIntraday(sym, c.intraday);
            out[sym] = (r?.points ?? []).filter((p) => p.c != null).map((p) => ({ time: p.t, value: p.c }));
          } else {
            const r = await cachedStock(sym);
            out[sym] = realSeries(r?.history ?? null, c)?.area ?? [];
          }
        } catch { out[sym] = []; }
      }));
      if (!cancelled) cmpData = out;
    })();
    return () => { cancelled = true; };
  });

  // Real intraday bars for 1D/5D (5m/30m). Daily ranges slice `history`.
  let intra = $state(null);
  $effect(() => {
    const t = ticker, c = cfg;
    if (!t || t === '—' || !c.intraday) { intra = null; return; }
    let cancelled = false;
    cachedIntraday(t, c.intraday)
      .then((r) => { if (!cancelled && r?.points?.length > 1) intra = { ...r, forRange: c.k }; })
      .catch(() => {});
    return () => { cancelled = true; };
  });

  function isoMinusDays(iso, days) { const d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() - days); return d.toISOString().slice(0, 10); }
  function ytdCutoff(iso) { return iso.slice(0, 4) + '-01-01'; }

  // Daily series over the FULL history + `fromIdx` = where the selected range's
  // window starts. `data` slices this to a fixed-WIDTH window (shifted by panBars)
  // so a horizontal scroll pans it back through history (see onWheel).
  function realSeries(hist, c) {
    if (!hist || hist.length < 2) return null;
    const last = hist[hist.length - 1].t;
    const cutoff = c.k === 'YTD' ? ytdCutoff(last) : (c.days === Infinity ? '0000' : isoMinusDays(last, c.days));
    const area = hist.map((p) => ({ time: p.t, value: p.c }));
    const candles = hist.map((p, i) => { const o = i ? hist[i - 1].c : p.c; return { time: p.t, open: o, high: Math.max(o, p.c), low: Math.min(o, p.c), close: p.c }; });
    let fromIdx = hist.findIndex((p) => p.t >= cutoff);
    if (fromIdx < 0 || fromIdx > hist.length - 2) fromIdx = Math.max(0, hist.length - 2);
    return { area, candles, fromIdx };
  }

  const data = $derived.by(() => {
    if (cfg.intraday && intra?.forRange === cfg.k && intra.ticker === (ticker || '').toUpperCase()) {
      const pts = intra.points.filter((p) => p.c != null);
      const area = pts.map((p) => ({ time: p.t, value: p.c }));
      const candles = pts.map((p, i) => {
        const o = i ? pts[i - 1].c : (intra.prevClose ?? p.c);
        return { time: p.t, open: o, high: Math.max(o, p.c), low: Math.min(o, p.c), close: p.c };
      });
      return { area, candles, prevClose: cfg.k === '1D' ? intra.prevClose : null, real: true };
    }
    const full = history?.length ? realSeries(history, cfg) : null;
    // no real data yet → mock series (hidden behind the loading skeleton, never plotted)
    if (!full) return { ...priceSeries(ticker, cfg.mock, price ?? 100), prevClose: null, real: false };
    // slice the full history to a fixed-WIDTH window, shifted back by panBars
    const N = full.area.length;
    const W = Math.max(2, Math.min(N, N - full.fromIdx));
    const pan = Math.max(0, Math.min(panBars, N - W));
    const end = N - pan;
    const start = Math.max(0, end - W);
    return { area: full.area.slice(start, end), candles: full.candles.slice(start, end), prevClose: null, real: true, total: N };
  });

  // deterministic mock volume per bar, coloured up/down by the bar's move
  const volumeData = $derived.by(() => {
    const c = data.candles;
    if (!c?.length) return [];
    let seed = 0; for (const ch of (ticker || 'x')) seed = (seed * 31 + ch.charCodeAt(0)) >>> 0;
    return c.map((bar, i) => {
      seed = (seed * 1664525 + 1013904297) >>> 0;
      const noise = 0.45 + (seed / 0xffffffff) * 0.9;
      const up = bar.close >= bar.open;
      return { time: bar.time, value: Math.round(bar.close * 1000 * noise), color: up ? hexA(GAIN, 0.42) : hexA(LOSS, 0.42) };
    });
  });

  // simple moving average over the area values
  function smaSeries(area, period) {
    if (!area || area.length < period) return [];
    const out = [];
    let sum = 0;
    for (let i = 0; i < area.length; i++) {
      sum += area[i].value;
      if (i >= period) sum -= area[i - period].value;
      if (i >= period - 1) out.push({ time: area[i].time, value: sum / period });
    }
    return out;
  }

  const f = (n) => Number(n ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const pctS = (n) => (n == null ? '—' : (n > 0 ? '+' : '') + n.toFixed(1) + '%');
  const usdS = (n) => (n == null ? '—' : (n >= 0 ? '+$' : '−$') + f(Math.abs(n)));
  function fmtDate(t) {
    if (t == null) return '';
    let d;
    if (typeof t === 'number') {
      d = new Date(t * 1000);
      return isNaN(d) ? '' : d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    }
    if (typeof t === 'string') d = new Date(t + 'T00:00:00');
    else if (typeof t === 'object' && t.year) d = new Date(t.year, (t.month || 1) - 1, t.day || 1);
    else return '';
    return isNaN(d) ? '' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  const BRAND = '#0fb39a', GAIN = '#00c060', LOSS = '#ff4d4d';
  // theme-reactive chart palette (lightweight-charts can't read CSS vars)
  const PAL = $derived($theme === 'light'
    ? { INK: '#1a1a1a', GRID: '#e7e1d3', MUTED: '#8a8478' }
    : { INK: '#faf7f0', GRID: '#2a2722', MUTED: '#8f897c' });
  function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`; }

  let host = $state();
  let chart = $state(null);
  let series = null;
  let volSeries = null;
  let sma50Series = null, sma200Series = null;
  let highlight = null;
  let hover = $state(null);
  let drag = $state(null);

  // ── my buy/sell fills as chart markers ──────────────────────────────────
  // Trades live in the shared store (no per-ticker endpoint); filter client-side.
  onMount(() => loadTrades());
  const myTrades = $derived(
    ($tradesStore ?? []).filter((t) => (t.ticker || '').toUpperCase() === (ticker || '').toUpperCase())
  );
  // local YYYY-MM-DD for a bar time (intraday=unix seconds, daily=already a string)
  const barDay = (time) => (typeof time === 'number'
    ? (() => { const d = new Date(time * 1000); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; })()
    : time);
  // stable lookup key matching both bar times and crosshair times. lightweight-charts
  // hands back daily times as a {year,month,day} object (not the original string), so
  // both sides must normalize the same way or the hover lookup never matches.
  const timeKey = (t) => {
    if (t == null) return '';
    if (typeof t === 'number') return String(t);
    if (typeof t === 'string') return t;
    if (typeof t === 'object' && t.year) return `${t.year}-${String(t.month).padStart(2, '0')}-${String(t.day).padStart(2, '0')}`;
    return String(t);
  };
  // { markers: sorted lightweight-charts markers, byTime: Map(String(barTime) → trades) }
  const tradeMarkers = $derived.by(() => {
    const bars = data.area;
    if (!bars?.length || !myTrades.length) return { markers: [], byTime: new Map() };
    const days = bars.map((b) => ({ day: barDay(b.time), time: b.time }));
    const first = days[0].day, last = days[days.length - 1].day;
    // place each in-window trade on its day's bar, snapping to the nearest prior bar
    const agg = new Map();     // `${barTime}|${side}` → true (one marker per day+side)
    const byTime = new Map();  // String(barTime) → [trades]
    for (const t of myTrades) {
      const d = t.date;
      if (!d || d < first || d > last) continue;
      let barTime = null;
      for (const bd of days) { if (bd.day <= d) barTime = bd.time; else break; }
      if (barTime == null) continue;
      const side = (t.action || '').toLowerCase() === 'buy' ? 'buy' : 'sell';
      agg.set(`${barTime}|${side}`, true);
      const k = timeKey(barTime);
      (byTime.get(k) ?? byTime.set(k, []).get(k)).push(t);
    }
    // emit in bar order so the array is time-ascending (lightweight-charts requires it)
    const markers = [];
    for (const b of bars) {
      for (const side of ['buy', 'sell']) {
        if (!agg.has(`${b.time}|${side}`)) continue;
        markers.push({
          time: b.time,
          position: side === 'buy' ? 'belowBar' : 'aboveBar',
          color: side === 'buy' ? GAIN : LOSS,
          shape: side === 'buy' ? 'arrowUp' : 'arrowDown',
        });
      }
    }
    return { markers, byTime };
  });
  // fills under the crosshair (resting hover, not the drag-measure) → tooltip detail
  const hoverTrades = $derived(
    hover && !drag && showTrades ? (tradeMarkers.byTime.get(timeKey(hover.time)) ?? null) : null
  );
  // click-drag span measure is a mouse affordance; touch gets the hold-scrub below
  function startDrag(e) {
    if (e?.pointerType === 'touch') return;
    if (hover?.price != null) { drag = { x: hover.x, price: hover.price, time: hover.time }; updateHighlight(); }
  }

  // ── touch scrub: HOLD (220ms) then DRAG moves the crosshair ──
  // Deterministic pointer implementation: hold engages, drag scrubs via
  // setCrosshairPosition (hover/tooltip fed manually), lift clears. A quick
  // swipe cancels the hold so the page/sheet keeps scrolling naturally.
  const HOLD_MS = 220, HOLD_SLOP = 8;
  let wrapEl = $state();
  let holdTimer = null, scrubbing = false, downAt = null;

  function scrubAt(clientX, clientY) {
    const arr = data?.area;
    if (!chart || !series || !arr?.length) return;
    const r = wrapEl.getBoundingClientRect();
    const x = Math.min(Math.max(clientX - r.left, 0), r.width);
    const y = Math.min(Math.max(clientY - r.top, 0), r.height);
    const lg = chart.timeScale().coordinateToLogical(x);
    if (lg == null) return;
    const pt = arr[Math.min(arr.length - 1, Math.max(0, Math.round(lg)))];
    if (!pt) return;
    chart.setCrosshairPosition(pt.value, pt.time, series);
    const sx = chart.timeScale().timeToCoordinate(pt.time);
    hover = { x: sx ?? x, y, price: pt.value, time: pt.time };
    updateHighlight();
  }
  function endScrub() {
    if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
    downAt = null;
    if (scrubbing) {
      scrubbing = false;
      chart?.clearCrosshairPosition();
      hover = null;
      updateHighlight();
    }
  }
  function onTouchDown(e) {
    if (e.pointerType !== 'touch') return;
    downAt = { x: e.clientX, y: e.clientY };
    holdTimer = setTimeout(() => { holdTimer = null; scrubbing = true; scrubAt(downAt.x, downAt.y); }, HOLD_MS);
  }
  function onTouchMove(e) {
    if (e.pointerType !== 'touch') return;
    if (scrubbing) { scrubAt(e.clientX, e.clientY); return; }
    if (downAt && Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > HOLD_SLOP) endScrub();
  }
  function onTouchEnd(e) { if (e.pointerType === 'touch') endScrub(); }

  // Two-finger / horizontal-wheel pan: shift the fixed-width window back/forward
  // through history (no zoom). Vertical scroll is left to the page.
  function onWheel(e) {
    if (!chart || Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return; // vertical → page scroll
    const N = data.total ?? 0, W = data.area?.length ?? 0;
    if (!N || N <= W) return; // whole history (or intraday feed) already in view
    e.preventDefault();
    panBars = Math.max(0, Math.min(Math.round(panBars - e.deltaX / 8), N - W));
  }

  onMount(() => {
    chart = createChart(host, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: 'rgba(0,0,0,0)' }, textColor: PAL.MUTED, fontFamily: 'Space Mono, ui-monospace, monospace', fontSize: 10, attributionLogo: false },
      grid: { vertLines: { visible: false }, horzLines: { color: PAL.GRID } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.08, bottom: 0.26 } },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, fixLeftEdge: true, fixRightEdge: true },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: { color: PAL.INK, width: 1, style: LineStyle.Solid, labelVisible: false },
        horzLine: { color: PAL.GRID, width: 1, style: LineStyle.Dotted, labelVisible: false },
      },
      handleScroll: false, handleScale: false,
    });
    highlight = chart.addSeries(AreaSeries, {
      lineColor: 'rgba(0,0,0,0)', lineWidth: 1, topColor: hexA(PAL.INK, 0.08), bottomColor: hexA(PAL.INK, 0.08),
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      autoscaleInfoProvider: () => null,
    });
    highlight.setData([]);
    chart.subscribeCrosshairMove((param) => {
      if (!param.point || !param.time || param.point.x < 0) { hover = null; updateHighlight(); return; }
      const d = series ? param.seriesData.get(series) : null;
      const px = d ? (d.value ?? d.close) : null;
      hover = px == null ? null : { x: param.point.x, y: param.point.y, price: px, time: param.time };
      updateHighlight();
    });
    const endDrag = () => { drag = null; updateHighlight(); };
    window.addEventListener('pointerup', endDrag);
    host.addEventListener('wheel', onWheel, { passive: false });
    return () => {
      window.removeEventListener('pointerup', endDrag);
      host.removeEventListener('wheel', onWheel);
      chart?.remove(); chart = null;
    };
  });

  // re-skin chrome (axes, grid, crosshair) when the theme flips
  $effect(() => {
    if (!chart) return;
    const p = PAL;
    chart.applyOptions({
      layout: { textColor: p.MUTED },
      grid: { horzLines: { color: p.GRID } },
      crosshair: { vertLine: { color: p.INK }, horzLine: { color: p.GRID } },
    });
  });

  // (re)build the price series on data / type / theme change
  $effect(() => {
    if (!chart) return;
    const d = data, type = chartType;
    // while data is still mock (loading), plot NOTHING — the skeleton covers the area
    // so no fake trajectory ever flashes
    const real = d.real;
    if (series) { chart.removeSeries(series); series = null; }
    if (type === 'candles') {
      series = chart.addSeries(CandlestickSeries, {
        upColor: GAIN, downColor: LOSS, borderUpColor: PAL.INK, borderDownColor: PAL.INK,
        wickUpColor: PAL.INK, wickDownColor: PAL.INK, priceLineVisible: false, lastValueVisible: false,
      });
      series.setData(real ? d.candles : []);
    } else if (type === 'line') {
      series = chart.addSeries(LineSeries, { color: BRAND, lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
      series.setData(real ? d.area : []);
    } else {
      series = chart.addSeries(AreaSeries, {
        lineColor: BRAND, lineWidth: 2, topColor: hexA(BRAND, 0.16), bottomColor: hexA(BRAND, 0),
        priceLineVisible: false, lastValueVisible: false,
      });
      series.setData(real ? d.area : []);
    }
    // a raw-$ reference line is meaningless on the % compare scale
    if (real && d.prevClose != null && !compares.length) {
      series.createPriceLine({ price: d.prevClose, color: PAL.MUTED, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: 'prev close' });
    }
    // my buy/sell fills (reading these re-runs the effect when trades load / toggle flips;
    // markers attach to the fresh series, so the old ones go with the removed series)
    createSeriesMarkers(series, real && showTrades ? tradeMarkers.markers : []);
    // the series IS the window slice (shifted by panBars), so fit it edge-to-edge
    if (real) chart.timeScale().fitContent();
  });

  // volume histogram, pinned to the bottom on its own overlay scale
  $effect(() => {
    if (!chart) return;
    const vol = showVolume && data.real ? volumeData : [];
    if (!volSeries) {
      volSeries = chart.addSeries(HistogramSeries, { priceScaleId: 'vol', priceLineVisible: false, lastValueVisible: false });
      chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    }
    volSeries.setData(vol);
  });

  // SMA overlays
  $effect(() => {
    if (!chart) return;
    const want50 = sma50, want200 = sma200, area = data.real ? data.area : [];
    if (want50 && !sma50Series) sma50Series = chart.addSeries(LineSeries, { color: '#d8a23a', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    if (!want50 && sma50Series) { chart.removeSeries(sma50Series); sma50Series = null; }
    if (want200 && !sma200Series) sma200Series = chart.addSeries(LineSeries, { color: '#7f77dd', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    if (!want200 && sma200Series) { chart.removeSeries(sma200Series); sma200Series = null; }
    if (sma50Series) sma50Series.setData(smaSeries(area, 50));
    if (sma200Series) sma200Series.setData(smaSeries(area, 200));
  });

  // compare overlays — one line per compared ticker, % scale while any active
  let cmpSeriesMap = new Map();   // sym → ISeriesApi
  $effect(() => {
    if (!chart) return;
    const list = compares, dataMap = cmpData;
    for (const [sym, s] of [...cmpSeriesMap]) {
      if (!list.some((c) => c.sym === sym)) { chart.removeSeries(s); cmpSeriesMap.delete(sym); }
    }
    for (const c of list) {
      if (!cmpSeriesMap.has(c.sym)) {
        cmpSeriesMap.set(c.sym, chart.addSeries(LineSeries, {
          color: c.color, lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false,
          crosshairMarkerVisible: false,
        }));
      }
      cmpSeriesMap.get(c.sym).setData(dataMap[c.sym] ?? []);
    }
    // % mode rebases every series to the window start so overlays are comparable
    chart.priceScale('right').applyOptions({ mode: list.length ? PriceScaleMode.Percentage : PriceScaleMode.Normal });
    chart.timeScale().fitContent();
  });

  let updatingHl = false;
  function updateHighlight() {
    if (updatingHl || !chart || !highlight) return;
    updatingHl = true;
    try {
      const a = data?.area;
      if (!drag || !hover || !a || a.length < 2) { highlight.setData([]); return; }
      const ts = chart.timeScale();
      const c0 = ts.coordinateToLogical(Math.min(drag.x, hover.x));
      const c1 = ts.coordinateToLogical(Math.max(drag.x, hover.x));
      if (c0 == null || c1 == null) { highlight.setData([]); return; }
      const i0 = Math.max(0, Math.floor(Math.min(c0, c1)));
      const i1 = Math.min(a.length - 1, Math.ceil(Math.max(c0, c1)));
      const slice = i1 > i0 ? a.slice(i0, i1 + 1) : [];
      const moved = Math.abs(hover.x - drag.x);
      const col = moved <= 8 ? hexA(PAL.INK, 0.08) : (hover.price - drag.price >= 0 ? hexA(GAIN, 0.18) : hexA(LOSS, 0.18));
      highlight.applyOptions({ topColor: col, bottomColor: col });
      highlight.setData(slice);
    } catch (e) {
      try { highlight.setData([]); } catch (_) {}
    } finally {
      updatingHl = false;
    }
  }

  const toggleMenu = (m) => (openMenu = openMenu === m ? null : m);
  function onWindowClick(e) { if (!e.target.closest?.('.gf-tool')) openMenu = null; }
  onMount(() => { window.addEventListener('click', onWindowClick); return () => window.removeEventListener('click', onWindowClick); });
</script>

<div class="sc">
  <!-- GF toolbar: chart type · compare · indicators -->
  <div class="gf-bar">
    <div class="gf-tool">
      <button class="gf-btn" class:active={openMenu === 'type'} onclick={() => toggleMenu('type')}>
        <svg class="gf-ic" viewBox="0 0 24 24" aria-hidden="true"><polyline points="2,15 8,9 13,13 22,4" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" /></svg>{TYPE_LABEL[chartType]}<span class="gf-cv" aria-hidden="true">▾</span>
      </button>
      {#if openMenu === 'type'}
        <div class="gf-menu">
          {#each Object.entries(TYPE_LABEL) as [k, label]}
            <button class="gf-item" class:sel={chartType === k} onclick={() => { chartType = k; openMenu = null; }}>{label}</button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="gf-tool">
      <button class="gf-btn" class:active={openMenu === 'compare' || compares.length > 0} onclick={() => toggleMenu('compare')}>
        <span class="gf-ic" aria-hidden="true">⇄</span>Compare{#if compares.length}<span class="gf-count">{compares.length}</span>{/if}<span class="gf-cv" aria-hidden="true">▾</span>
      </button>
      {#if openMenu === 'compare'}
        <div class="gf-menu gf-menu-cmp">
          <input class="gf-cmp-input" type="text" placeholder="Search any stock or ETF…"
            bind:value={cmpQ}
            autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
          {#if cmpQ.trim()}
            {#if cmpLoading}
              <div class="gf-cmp-note">searching…</div>
            {:else if cmpResults.length === 0}
              <div class="gf-cmp-note">no matches</div>
            {:else}
              {#each cmpResults as r (r.symbol)}
                <button class="gf-item" class:sel={compared((r.symbol || '').toUpperCase())}
                  onclick={() => toggleCompare(r.symbol, r.name)}>
                  <span class="gf-check">{compared((r.symbol || '').toUpperCase()) ? '✓' : ''}</span>
                  <span class="gf-cmp-name">{r.name}</span><span class="gf-sym">{r.symbol}</span>
                </button>
              {/each}
            {/if}
          {:else}
            {#each QUICK_COMPARES as c (c.sym)}
              <button class="gf-item" class:sel={compared(c.sym)} onclick={() => toggleCompare(c.sym, c.label)}>
                <span class="gf-check">{compared(c.sym) ? '✓' : ''}</span>{c.label}<span class="gf-sym">{c.sym}</span>
              </button>
            {/each}
            {#each compares.filter((c) => !QUICK_COMPARES.some((q) => q.sym === c.sym)) as c (c.sym)}
              <button class="gf-item sel" onclick={() => toggleCompare(c.sym)}>
                <span class="gf-check">✓</span><span class="gf-cmp-name">{c.label}</span><span class="gf-sym">{c.sym}</span>
              </button>
            {/each}
          {/if}
        </div>
      {/if}
    </div>

    <div class="gf-tool">
      <button class="gf-btn" class:active={openMenu === 'indicators'} onclick={() => toggleMenu('indicators')}>
        <span class="gf-ic" aria-hidden="true">∿</span>Indicators<span class="gf-cv" aria-hidden="true">▾</span>
      </button>
      {#if openMenu === 'indicators'}
        <div class="gf-menu gf-menu-wide">
          <button class="gf-item" class:sel={showTrades} onclick={() => (showTrades = !showTrades)}><span class="gf-check">{showTrades ? '✓' : ''}</span>My trades</button>
          <button class="gf-item" class:sel={showVolume} onclick={() => (showVolume = !showVolume)}><span class="gf-check">{showVolume ? '✓' : ''}</span>Volume</button>
          <button class="gf-item" class:sel={sma50} onclick={() => (sma50 = !sma50)}><span class="gf-check">{sma50 ? '✓' : ''}</span>SMA 50</button>
          <button class="gf-item" class:sel={sma200} onclick={() => (sma200 = !sma200)}><span class="gf-check">{sma200 ? '✓' : ''}</span>SMA 200</button>
        </div>
      {/if}
    </div>
  </div>

  <!-- active compares — removable legend chips, dot = series colour -->
  {#if compares.length}
    <div class="gf-cmps">
      <span class="gf-chip gf-chip-self"><span class="gf-dot" style="background:{BRAND}"></span>{ticker}</span>
      {#each compares as c (c.sym)}
        <button class="gf-chip" onclick={() => toggleCompare(c.sym)} title="Remove {c.sym}">
          <span class="gf-dot" style="background:{c.color}"></span>{c.sym}<span class="gf-x" aria-hidden="true">✕</span>
        </button>
      {/each}
    </div>
  {/if}

  <!-- chart -->
  <div class="sc-chartwrap" bind:this={wrapEl}
    onpointerdown={(e) => { startDrag(e); onTouchDown(e); }}
    onpointermove={onTouchMove} onpointerup={onTouchEnd} onpointercancel={onTouchEnd}>
    <div class="sc-chart" bind:this={host}></div>
    {#if !data.real}
      <!-- loading: a calm breathing block — deliberately NO line/shape so it never
           reads as a price trajectory -->
      <div class="sc-skel" role="img" aria-label="loading chart"></div>
    {/if}
    {#if data.real && data.prevClose != null && !compares.length}
      <div class="sc-prev">prev close <b>${f(data.prevClose)}</b></div>
    {/if}
    {#if drag}<div class="sc-anchor" style="left:{drag.x}px"></div>{/if}
    {#if hover}
      {#if drag && drag.price != null}
        {@const d$ = hover.price - drag.price}
        {@const dp = (hover.price / drag.price - 1) * 100}
        {@const moved = Math.abs(hover.x - drag.x)}
        {@const fromT = drag.x <= hover.x ? drag.time : hover.time}
        {@const toT = drag.x <= hover.x ? hover.time : drag.time}
        <div class="sc-tip {moved > 8 ? (d$ >= 0 ? 'pos' : 'neg') : ''}" class:below={hover.y < 48} style="left:{hover.x}px; top:{hover.y}px">
          <span class="sc-tip-v">{usdS(d$)} · {pctS(dp)}</span>
          <span class="sc-tip-d">{fmtDate(fromT)} → {fmtDate(toT)}</span>
        </div>
      {:else}
        <div class="sc-tip" class:below={hover.y < 48} style="left:{hover.x}px; top:{hover.y}px">
          <span class="sc-tip-v">${f(hover.price)}</span>
          <span class="sc-tip-d">{fmtDate(hover.time)}</span>
          {#if hoverTrades}
            {#each hoverTrades as t (t.date + t.action + t.shares + (t.price ?? ''))}
              <span class="sc-tip-trade {(t.action || '').toLowerCase() === 'buy' ? 'up' : 'down'}">
                {(t.action || '').toLowerCase()} {Number(t.shares).toLocaleString('en-US', { maximumFractionDigits: 4 })} sh{#if t.price != null} @ ${f(t.price)}{/if}
              </span>
            {/each}
          {/if}
        </div>
      {/if}
    {/if}
  </div>

  <!-- GF range tabs -->
  <div class="gf-ranges" role="group" aria-label="range">
    {#each RANGES as rg}
      <button class="gf-range" class:on={range === rg.k} onclick={() => { range = rg.k; panBars = 0; }}>{rg.k}</button>
    {/each}
  </div>
</div>

<style>
  .sc { height: 100%; display: flex; flex-direction: column; gap: 10px; min-width: 0; }

  /* toolbar */
  .gf-bar { display: flex; align-items: center; gap: 8px; flex: 0 0 auto; }
  .gf-tool { position: relative; }
  .gf-btn { display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
    font-family: var(--sans); font-size: 12px; font-weight: 700; color: var(--ink);
    padding: 5px 12px; background: transparent; border: var(--bw) solid var(--hairline);
    border-radius: 999px; transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .gf-btn:hover { border-color: var(--ink); }
  .gf-btn.active { background: var(--ink); border-color: var(--ink); color: var(--paper); }
  .gf-ic { font-size: 13px; opacity: .7; }
  svg.gf-ic { width: 14px; height: 14px; }
  .gf-cv { font-size: 9px; opacity: .6; margin-left: 1px; }
  .gf-menu { position: absolute; top: calc(100% + 5px); left: 0; z-index: 20; min-width: 150px;
    display: flex; flex-direction: column; padding: 5px; gap: 1px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh); }
  .gf-menu-wide { min-width: 185px; }
  .gf-item { display: flex; align-items: center; gap: 8px; width: 100%; cursor: pointer; text-align: left;
    font-family: var(--sans); font-size: 12.5px; font-weight: 600; color: var(--ink);
    padding: 7px 9px; border: 0; background: transparent; border-radius: 6px; }
  .gf-item:hover:not(:disabled) { background: var(--hover); }
  .gf-item.sel { font-weight: 700; }
  .gf-check { flex: 0 0 14px; font-size: 12px; color: var(--brand); }
  .gf-sym { margin-left: auto; font-family: var(--mono); font-size: 10px; color: var(--muted); }
  /* compare menu: search box on top, results / quick picks under it */
  .gf-menu-cmp { min-width: 230px; }
  .gf-cmp-input { box-sizing: border-box; width: 100%; margin-bottom: 4px; padding: 7px 9px;
    border: var(--bw) solid var(--hairline); border-radius: 6px; outline: none; background: transparent;
    font-family: var(--sans); font-size: 12.5px; font-weight: 600; color: var(--ink); }
  .gf-cmp-input:focus { border-color: var(--ink); }
  .gf-cmp-input::placeholder { color: var(--muted); font-weight: 500; }
  .gf-cmp-name { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .gf-cmp-note { padding: 7px 9px; font-family: var(--mono); font-size: 11px; color: var(--muted); }
  .gf-count { font-family: var(--mono); font-size: 10px; font-weight: 700; line-height: 1;
    padding: 2px 6px; border-radius: 999px; background: var(--paper); color: var(--ink);
    border: 1px solid currentColor; }
  /* iOS focus-zoom guard for the in-menu search */
  @media (max-width: 700px) { .gf-cmp-input { font-size: 16px; } }

  /* active-compare chips under the toolbar */
  .gf-cmps { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; flex: 0 0 auto; }
  .gf-chip { display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
    font-family: var(--mono); font-size: 10.5px; font-weight: 700; color: var(--ink);
    padding: 3px 9px; background: transparent; border: var(--bw) solid var(--hairline); border-radius: 999px; }
  .gf-chip:hover { border-color: var(--ink); }
  .gf-chip-self { cursor: default; color: var(--muted); }
  .gf-dot { width: 8px; height: 8px; border-radius: 50%; border: 1px solid var(--ink); flex: 0 0 auto; }
  .gf-x { font-size: 9px; opacity: .6; }

  /* chart */
  .sc-chartwrap { flex: 1 1 auto; min-height: 200px; position: relative; user-select: none; touch-action: none; }
  /* phone: give vertical swipes back to the page/sheet scroll; horizontal drags
     and the long-press crosshair scrub stay with the chart */
  @media (max-width: 700px) {
    .sc-chartwrap { touch-action: pan-y; }
  }
  .sc-chart { position: absolute; inset: 0; overflow: hidden; }
  /* loading skeleton — a single breathing block (no line/shape = no trajectory) */
  .sc-skel { position: absolute; inset: 0; z-index: 4; pointer-events: none;
    border: var(--bw) solid color-mix(in srgb, var(--ink) 16%, transparent);
    border-radius: var(--r); background: color-mix(in srgb, var(--ink) 6%, transparent);
    animation: sc-skel 1.4s ease-in-out infinite; }
  @keyframes sc-skel { 0%, 100% { opacity: .35; } 50% { opacity: .85; } }
  @media (prefers-reduced-motion: reduce) { .sc-skel { animation: none; opacity: .5; } }
  .sc-prev { position: absolute; top: 6px; right: 8px; z-index: 3; pointer-events: none;
    font-family: var(--mono); font-size: 10px; color: var(--muted); }
  .sc-prev b { color: var(--ink); font-weight: 700; }
  .sc-anchor { position: absolute; top: 0; bottom: 0; width: 0; z-index: 4; pointer-events: none; border-left: 1px dashed var(--muted); }
  .sc-tip { position: absolute; z-index: 5; pointer-events: none; white-space: nowrap;
    transform: translate(-50%, calc(-100% - 12px));
    display: flex; flex-direction: column; align-items: center; line-height: 1.2;
    font-family: var(--mono); font-variant-numeric: tabular-nums;
    padding: 3px 7px; background: var(--ink); color: var(--paper) !important; border-radius: 4px; }
  .sc-tip-v { font-size: 11px; font-weight: 700; }
  .sc-tip-d { font-size: 9px; font-weight: 400; }
  .sc-tip-trade { margin-top: 3px; font-size: 10px; font-weight: 700; text-transform: capitalize; }
  .sc-tip-trade.up { color: var(--gain) !important; }
  .sc-tip-trade.down { color: var(--loss) !important; }
  .sc-tip.pos { background: var(--gain); color: #fff !important; }
  .sc-tip.neg { background: var(--loss); color: #fff !important; }
  .sc-tip.below { transform: translate(-50%, 12px); }

  /* GF range tabs */
  .gf-ranges { display: flex; align-items: center; gap: 2px; flex: 0 0 auto;
    border-top: 1.5px solid color-mix(in srgb, var(--ink) 11%, transparent); padding-top: 8px; }
  /* range pills — system states: text → outline on hover → solid ink when on */
  .gf-range { font-family: var(--mono); font-size: 11px; font-weight: 600; cursor: pointer; color: var(--muted);
    padding: 4px 11px; border: var(--bw) solid transparent; background: transparent; border-radius: 999px;
    letter-spacing: .02em; transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .gf-range:hover { color: var(--ink); border-color: var(--ink); }
  .gf-range.on { color: var(--paper); background: var(--ink); border-color: var(--ink); }
</style>
