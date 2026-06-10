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
  import { createChart, AreaSeries, CandlestickSeries, LineSeries, HistogramSeries, ColorType, CrosshairMode, LineStyle } from 'lightweight-charts';
  import { priceSeries } from '$lib/mockStock.js';
  import { api } from '$lib/api.js';
  import { theme } from '$lib/theme.js';

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
    { k: '5Y',  days: 1850, intraday: null, mock: '5Y' },
    { k: 'MAX', days: Infinity, intraday: null, mock: '5Y' },
  ];

  let range = $state('1D');
  let chartType = $state('area');     // 'area' | 'candles' | 'line'
  let showVolume = $state(true);
  let sma50 = $state(false);
  let sma200 = $state(false);
  let openMenu = $state(null);        // 'type' | 'compare' | 'indicators' | null
  const cfg = $derived(RANGES.find((r) => r.k === range) ?? RANGES[0]);

  const TYPE_LABEL = { area: 'Area', candles: 'Candlestick', line: 'Line' };
  const COMPARES = [
    { sym: 'SPY', label: 'S&P 500' },
    { sym: 'QQQ', label: 'Nasdaq 100' },
    { sym: 'BTC-USD', label: 'Bitcoin' },
  ];

  // Real intraday bars for 1D/5D (5m/30m). Daily ranges slice `history`.
  let intra = $state(null);
  $effect(() => {
    const t = ticker, c = cfg;
    if (!t || t === '—' || !c.intraday) { intra = null; return; }
    let cancelled = false;
    api.intraday(t, c.intraday)
      .then((r) => { if (!cancelled && r?.points?.length > 1) intra = { ...r, forRange: c.k }; })
      .catch(() => {});
    return () => { cancelled = true; };
  });

  function isoMinusDays(iso, days) { const d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() - days); return d.toISOString().slice(0, 10); }
  function ytdCutoff(iso) { return iso.slice(0, 4) + '-01-01'; }

  function realSeries(hist, c) {
    if (!hist || hist.length < 2) return null;
    const last = hist[hist.length - 1].t;
    const cutoff = c.k === 'YTD' ? ytdCutoff(last) : (c.days === Infinity ? '0000' : isoMinusDays(last, c.days));
    let win = hist.filter((p) => p.t >= cutoff);
    if (win.length < 2) win = hist.slice(-2);
    const area = win.map((p) => ({ time: p.t, value: p.c }));
    const candles = win.map((p, i) => { const o = i ? win[i - 1].c : p.c; return { time: p.t, open: o, high: Math.max(o, p.c), low: Math.min(o, p.c), close: p.c }; });
    return { area, candles, prevClose: null };
  }

  const data = $derived.by(() => {
    if (cfg.intraday && intra?.forRange === cfg.k && intra.ticker === (ticker || '').toUpperCase()) {
      const pts = intra.points.filter((p) => p.c != null);
      const area = pts.map((p) => ({ time: p.t, value: p.c }));
      const candles = pts.map((p, i) => {
        const o = i ? pts[i - 1].c : (intra.prevClose ?? p.c);
        return { time: p.t, open: o, high: Math.max(o, p.c), low: Math.min(o, p.c), close: p.c };
      });
      return { area, candles, prevClose: cfg.k === '1D' ? intra.prevClose : null };
    }
    const real = history?.length ? realSeries(history, cfg) : null;
    return real ?? { ...priceSeries(ticker, cfg.mock, price ?? 100), prevClose: null };
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
  function startDrag() { if (hover?.price != null) { drag = { x: hover.x, price: hover.price, time: hover.time }; updateHighlight(); } }

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
    return () => { window.removeEventListener('pointerup', endDrag); chart?.remove(); chart = null; };
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
    if (series) { chart.removeSeries(series); series = null; }
    if (type === 'candles') {
      series = chart.addSeries(CandlestickSeries, {
        upColor: GAIN, downColor: LOSS, borderUpColor: PAL.INK, borderDownColor: PAL.INK,
        wickUpColor: PAL.INK, wickDownColor: PAL.INK, priceLineVisible: false, lastValueVisible: false,
      });
      series.setData(d.candles);
    } else if (type === 'line') {
      series = chart.addSeries(LineSeries, { color: BRAND, lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
      series.setData(d.area);
    } else {
      series = chart.addSeries(AreaSeries, {
        lineColor: BRAND, lineWidth: 2, topColor: hexA(BRAND, 0.16), bottomColor: hexA(BRAND, 0),
        priceLineVisible: false, lastValueVisible: false,
      });
      series.setData(d.area);
    }
    if (d.prevClose != null) {
      series.createPriceLine({ price: d.prevClose, color: PAL.MUTED, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: 'prev close' });
    }
    chart.timeScale().fitContent();
  });

  // volume histogram, pinned to the bottom on its own overlay scale
  $effect(() => {
    if (!chart) return;
    const vol = showVolume ? volumeData : [];
    if (!volSeries) {
      volSeries = chart.addSeries(HistogramSeries, { priceScaleId: 'vol', priceLineVisible: false, lastValueVisible: false });
      chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    }
    volSeries.setData(vol);
  });

  // SMA overlays
  $effect(() => {
    if (!chart) return;
    const want50 = sma50, want200 = sma200, area = data.area;
    if (want50 && !sma50Series) sma50Series = chart.addSeries(LineSeries, { color: '#d8a23a', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    if (!want50 && sma50Series) { chart.removeSeries(sma50Series); sma50Series = null; }
    if (want200 && !sma200Series) sma200Series = chart.addSeries(LineSeries, { color: '#7f77dd', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    if (!want200 && sma200Series) { chart.removeSeries(sma200Series); sma200Series = null; }
    if (sma50Series) sma50Series.setData(smaSeries(area, 50));
    if (sma200Series) sma200Series.setData(smaSeries(area, 200));
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
        <span class="gf-ic" aria-hidden="true">◔</span>{TYPE_LABEL[chartType]}<span class="gf-cv" aria-hidden="true">▾</span>
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
      <button class="gf-btn" class:active={openMenu === 'compare'} onclick={() => toggleMenu('compare')}>
        <span class="gf-ic" aria-hidden="true">⇄</span>Compare<span class="gf-cv" aria-hidden="true">▾</span>
      </button>
      {#if openMenu === 'compare'}
        <div class="gf-menu gf-menu-wide">
          {#each COMPARES as c}
            <button class="gf-item gf-item-soon" disabled>{c.label} <span class="gf-sym">{c.sym}</span><span class="gf-soon">soon</span></button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="gf-tool">
      <button class="gf-btn" class:active={openMenu === 'indicators'} onclick={() => toggleMenu('indicators')}>
        <span class="gf-ic" aria-hidden="true">∿</span>Indicators<span class="gf-cv" aria-hidden="true">▾</span>
      </button>
      {#if openMenu === 'indicators'}
        <div class="gf-menu gf-menu-wide">
          <button class="gf-item" class:sel={showVolume} onclick={() => (showVolume = !showVolume)}><span class="gf-check">{showVolume ? '✓' : ''}</span>Volume</button>
          <button class="gf-item" class:sel={sma50} onclick={() => (sma50 = !sma50)}><span class="gf-check">{sma50 ? '✓' : ''}</span>SMA 50</button>
          <button class="gf-item" class:sel={sma200} onclick={() => (sma200 = !sma200)}><span class="gf-check">{sma200 ? '✓' : ''}</span>SMA 200</button>
        </div>
      {/if}
    </div>
  </div>

  <!-- chart -->
  <div class="sc-chartwrap" onpointerdown={startDrag}>
    <div class="sc-chart" bind:this={host}></div>
    {#if data.prevClose != null}
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
        </div>
      {/if}
    {/if}
  </div>

  <!-- GF range tabs -->
  <div class="gf-ranges" role="group" aria-label="range">
    {#each RANGES as rg}
      <button class="gf-range" class:on={range === rg.k} onclick={() => (range = rg.k)}>{rg.k}</button>
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
  .gf-item-soon { cursor: default; color: var(--muted); }
  .gf-soon { margin-left: 8px; font-family: var(--mono); font-size: 8px; text-transform: uppercase; letter-spacing: .1em;
    padding: 1px 5px; border: 1px solid color-mix(in srgb, var(--ink) 22%, transparent); border-radius: 999px; }

  /* chart */
  .sc-chartwrap { flex: 1 1 auto; min-height: 200px; position: relative; user-select: none; touch-action: none; }
  .sc-chart { position: absolute; inset: 0; overflow: hidden; }
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
