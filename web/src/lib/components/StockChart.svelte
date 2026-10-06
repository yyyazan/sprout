<script>
  // Stock chart, Google-Finance style. Shares its shell, interactions and
  // markers with PortfolioChart (components/chart/* + lib/chartKit) — only the
  // data differs: real daily closes from `history`, intraday from /api/stock for
  // 1D/1W, else a deterministic mock hidden behind the loading skeleton.
  //
  // NOTE: per-bar volume isn't in the data feed yet, so the volume histogram is
  // a deterministic client-side mock (clearly a visual scaffold). Real volume is
  // a backend follow-up; the histogram swaps in transparently once it lands.
  import { onMount } from 'svelte';
  import { createChart, AreaSeries, CandlestickSeries, LineSeries, HistogramSeries, LineStyle, PriceScaleMode, createSeriesMarkers } from 'lightweight-charts';
  import { BRAND, chartPalette, baseChartOptions, themeOptions, areaStyle, hexA, bottomMargin, dataRange } from '$lib/chartTheme.js';
  import { ChartPointer, addBand, paintBand, tradeMarkers, tradeLines, indexOf, timeKey, fmtTime, fmtPct, fmtUsd, fmtUsdSigned, RANGE_LABELS } from '$lib/chartKit.svelte.js';
  import { priceSeries } from '$lib/mockStock.js';
  import { cachedStock, cachedIntraday } from '$lib/stockCache.js';
  import { theme } from '$lib/theme.js';
  import { trades as tradesStore, loadTrades } from '$lib/stores.js';
  import ChartFrame from './chart/ChartFrame.svelte';
  import ChartMenu from './chart/ChartMenu.svelte';
  import CompareMenu from './chart/CompareMenu.svelte';
  import ChartTip from './chart/ChartTip.svelte';

  let { ticker = '—', history = null, price = 100 } = $props();

  // days = lookback window for daily-history slicing; intraday = which
  // /api/stock intraday feed (else null → daily); mock = mockStock key.
  const RANGES = [
    { k: '1D',  days: 3,    intraday: '1d', mock: '1D' },
    { k: '1W',  days: 9,    intraday: '1w', mock: '1W' },
    { k: '1M',  days: 33,   intraday: null, mock: '1M' },
    { k: '3M',  days: 95,   intraday: null, mock: '3M' },
    { k: '6M',  days: 190,  intraday: null, mock: '3M' },
    { k: 'YTD', days: null, intraday: null, mock: '1Y' },
    { k: '1Y',  days: 370,  intraday: null, mock: '1Y' },
    { k: '2Y',  days: 740,  intraday: null, mock: '5Y' },
    { k: '5Y',  days: 1850, intraday: null, mock: '5Y' },
    { k: '10Y', days: 3700, intraday: null, mock: '5Y' },
    { k: 'ALL', days: Infinity, intraday: null, mock: '5Y' },
  ];

  let range = $state('1M');
  let panBars = $state(0);            // bars the fixed-width window is shifted back
  let chartType = $state('area');     // 'area' | 'candles' | 'line'
  let showVolume = $state(true);
  let sma50 = $state(false);
  let sma200 = $state(false);
  let showTrades = $state(true);      // buy/sell fills as markers
  const cfg = $derived(RANGES.find((r) => r.k === range) ?? RANGES[0]);

  const TYPE_LABEL = { area: 'Area', candles: 'Candlestick', line: 'Line' };
  // scale margins as a fraction of the plot; the bottom one is the volume band's room
  const MARGIN_TOP = 0.08, MARGIN_BOTTOM = 0.26;

  // ── compare: rebased-% overlays of any tickers ──
  let compares = $state([]);     // [{ sym, label, color }]
  let cmpData = $state({});      // sym → [{ time, value }] for the current range

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

  // Real intraday bars for 1D/1W (5m/30m). Daily ranges slice `history`.
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
  // so a horizontal scroll pans it back through history.
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
  // what the pointer and the band work over: the plotted closes, or nothing while loading
  const pts = $derived(data.real ? data.area : []);

  // deterministic mock volume per bar, coloured up/down by the bar's move
  const volumeData = $derived.by(() => {
    const c = data.candles;
    if (!c?.length) return [];
    let seed = 0; for (const ch of (ticker || 'x')) seed = (seed * 31 + ch.charCodeAt(0)) >>> 0;
    return c.map((bar, i) => {
      seed = (seed * 1664525 + 1013904297) >>> 0;
      const noise = 0.45 + (seed / 0xffffffff) * 0.9;
      const up = bar.close >= bar.open;
      return { time: bar.time, value: Math.round(bar.close * 1000 * noise), color: up ? hexA(PAL.GAIN, 0.42) : hexA(PAL.LOSS, 0.42) };
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

  // shared, theme-reactive palette (lib/chartTheme.js mirrors the app.css tokens)
  const PAL = $derived(chartPalette($theme));

  let host = $state();
  let chart = $state(null);
  let series = null;
  let volSeries = null;
  let sma50Series = null, sma200Series = null;
  let band = null;

  const ptr = new ChartPointer({
    points: () => pts,
    series: () => series,
    pan: (bars) => {
      const N = data.total ?? 0, W = data.area?.length ?? 0;
      if (!N || N <= W) return false; // whole history (or an intraday feed) already in view
      panBars = Math.max(0, Math.min(Math.round(panBars + bars), N - W));
      return true;
    },
  });

  const hoverPt = $derived.by(() => {
    const i = ptr.hover ? indexOf(pts, ptr.hover.time) : -1;
    return i < 0 ? null : pts[i];
  });

  // readout: the window's move (1D: vs prev close); while hovering, start → that bar
  const read = $derived.by(() => {
    if (!pts.length) return null;
    const base = data.prevClose ?? pts[0].value;
    const cur = (hoverPt ?? pts[pts.length - 1]).value;
    if (!base) return null;
    return {
      pct: (cur / base - 1) * 100,
      label: hoverPt ? fmtTime(hoverPt.time) : RANGE_LABELS[range] ?? '',
      extra: { text: fmtUsdSigned(cur - base), up: cur >= base },
    };
  });

  // drag-measure, oldest → newest whichever way the mouse went
  const measure = $derived.by(() => {
    const s = ptr.span(pts);
    if (!s) return null;
    const v0 = pts[s.i0].value, v1 = pts[s.i1].value;
    return { ...s, abs: v1 - v0, pct: v0 ? (v1 / v0 - 1) * 100 : null };
  });

  // ── my buy/sell fills for this ticker ──
  onMount(() => loadTrades());
  const myTrades = $derived(
    ($tradesStore ?? []).filter((t) => (t.ticker || '').toUpperCase() === (ticker || '').toUpperCase())
  );
  const marks = $derived(tradeMarkers(pts, myTrades, PAL));
  const hoverFills = $derived(
    hoverPt && !measure && showTrades ? (marks.byKey.get(timeKey(hoverPt.time)) ?? null) : null
  );

  onMount(() => {
    const base = baseChartOptions(PAL);
    chart = createChart(host, {
      ...base,
      rightPriceScale: { ...base.rightPriceScale, scaleMargins: { top: MARGIN_TOP, bottom: MARGIN_BOTTOM } },
      timeScale: { ...base.timeScale, timeVisible: true, secondsVisible: false },
    });
    band = addBand(chart);
    const detach = ptr.attach(chart, host);
    return () => { detach(); chart?.remove(); chart = null; series = null; band = null; };
  });

  // re-skin chrome (axes, grid, crosshair) when the theme flips
  $effect(() => {
    if (!chart) return;
    chart.applyOptions(themeOptions(PAL));
  });

  // (re)build the price series on data / type / theme / fills change
  $effect(() => {
    if (!chart) return;
    const d = data, type = chartType;
    // while data is still mock (loading), plot NOTHING — the skeleton covers the area
    // so no fake trajectory ever flashes
    const real = d.real;
    if (series) { chart.removeSeries(series); series = null; }
    if (type === 'candles') {
      series = chart.addSeries(CandlestickSeries, {
        upColor: PAL.GAIN, downColor: PAL.LOSS, borderUpColor: PAL.INK, borderDownColor: PAL.INK,
        wickUpColor: PAL.INK, wickDownColor: PAL.INK, priceLineVisible: false, lastValueVisible: false,
        autoscaleInfoProvider: dataRange,
      });
      series.setData(real ? d.candles : []);
    } else if (type === 'line') {
      series = chart.addSeries(LineSeries, { color: BRAND, lineWidth: 2, priceLineVisible: false, lastValueVisible: false, autoscaleInfoProvider: dataRange });
      series.setData(real ? d.area : []);
    } else {
      series = chart.addSeries(AreaSeries, { ...areaStyle(), autoscaleInfoProvider: dataRange });
      series.setData(real ? d.area : []);
    }
    // a raw-$ reference line is meaningless on the % compare scale
    if (real && d.prevClose != null && !compares.length) {
      series.createPriceLine({ price: d.prevClose, color: PAL.MUTED, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: 'Prev close' });
    }
    // the volume band sits under the price, but a price axis can't run under $0 — on a
    // ticker that swings hard the band narrows instead (the % compare scale can go below 0)
    const bars = real ? d.candles : [];
    chart.priceScale('right').applyOptions({
      scaleMargins: {
        top: MARGIN_TOP,
        bottom: compares.length || !bars.length ? MARGIN_BOTTOM
          : bottomMargin(MARGIN_BOTTOM, MARGIN_TOP, Math.min(...bars.map((b) => b.low)), Math.max(...bars.map((b) => b.high))),
      },
    });
    // fills ride the fresh series, so the old markers go with the removed one
    createSeriesMarkers(series, real && showTrades ? marks.markers : []);
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

  $effect(() => { paintBand(band, pts, measure, PAL); });
</script>

<ChartFrame ranges={RANGES.map((r) => r.k)} bind:range onrange={() => (panBars = 0)}
  bind:compares self={ticker} {read}>
  {#snippet tools()}
    <ChartMenu label={TYPE_LABEL[chartType]} icon="line">
      {#snippet children({ close })}
        {#each Object.entries(TYPE_LABEL) as [k, label]}
          <button class="cm-item" class:sel={chartType === k} onclick={() => { chartType = k; close(); }}>{label}</button>
        {/each}
      {/snippet}
    </ChartMenu>
    <CompareMenu bind:list={compares} exclude={ticker} />
    <ChartMenu label="Indicators" icon="indicators" width={185}>
      <button class="cm-item" class:sel={showTrades} onclick={() => (showTrades = !showTrades)}><span class="cm-check">{showTrades ? '✓' : ''}</span>My trades</button>
      <button class="cm-item" class:sel={showVolume} onclick={() => (showVolume = !showVolume)}><span class="cm-check">{showVolume ? '✓' : ''}</span>Volume</button>
      <button class="cm-item" class:sel={sma50} onclick={() => (sma50 = !sma50)}><span class="cm-check">{sma50 ? '✓' : ''}</span>SMA 50</button>
      <button class="cm-item" class:sel={sma200} onclick={() => (sma200 = !sma200)}><span class="cm-check">{sma200 ? '✓' : ''}</span>SMA 200</button>
    </ChartMenu>
  {/snippet}

  <div class="sc-canvas" bind:this={host}></div>
  {#if !data.real}
    <!-- loading: a calm breathing block — deliberately NO line/shape so it never
         reads as a price trajectory -->
    <div class="skel skel-fill sc-skel" role="img" aria-label="loading chart"></div>
  {/if}
  {#if data.real && data.prevClose != null && !compares.length}
    <div class="sc-prev">Prev close <b>{fmtUsd(data.prevClose)}</b></div>
  {/if}
  {#if measure}
    <div class="sc-anchor" style="left:{ptr.anchor.x}px"></div>
    <ChartTip x={ptr.hover.x} y={ptr.hover.y} tone={(measure.pct ?? 0) >= 0 ? 'pos' : 'neg'}
      value={fmtUsdSigned(measure.abs)} aside={fmtPct(measure.pct)}
      sub="{fmtTime(measure.t0)} → {fmtTime(measure.t1)}" />
  {:else if hoverPt}
    <ChartTip x={ptr.hover.x} y={ptr.hover.y} value={fmtUsd(hoverPt.value)} sub={fmtTime(hoverPt.time)}
      lines={tradeLines(hoverFills)} />
  {/if}
</ChartFrame>

<style>
  /* pan-y: vertical swipes keep scrolling the page/sheet; horizontal drags and
     the long-press scrub belong to the chart */
  .sc-canvas { position: absolute; inset: 0; overflow: hidden; touch-action: pan-y; user-select: none; }
  /* loading: the shared .skel block over the plot, above the empty canvas */
  .sc-skel { z-index: 4; pointer-events: none; }
  .sc-prev { position: absolute; top: 6px; right: 58px; z-index: 3; pointer-events: none;
    font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); font-variant-numeric: tabular-nums; }
  .sc-prev b { color: var(--ink); font-weight: 600; }
  .sc-anchor { position: absolute; top: 0; bottom: 0; width: 0; z-index: 4; pointer-events: none; border-left: 1px dashed var(--muted); }
</style>
