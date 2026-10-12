<script>
  // Portfolio chart. Shares its shell, interactions and markers with
  // StockChart (components/chart/* + lib/chartKit) — only the data differs.
  // Plots $ value or time-weighted return over the selected window; the readout
  // is the window's TWR and its gap to SPY (or start → hovered day).
  //   Value  = dollars, with deposits and withdrawals as bars in a strip under the curve.
  //   Return = TWR %, with rebased-% comparison lines (S&P 500 on until switched off).
  import { onMount, untrack } from 'svelte';
  import { createChart, AreaSeries, LineSeries, HistogramSeries, LineStyle, PriceScaleMode, createSeriesMarkers } from 'lightweight-charts';
  import { theme } from '$lib/theme.js';
  import { chartPalette, baseChartOptions, themeOptions, areaStyle, bottomMargin, dataRange, hexA } from '$lib/chartTheme.js';
  import { ChartPointer, addBand, paintBand, tradeMarkers, tradeLines, flowBuckets, flowLines, flowBarsPrimitive, timeKey, fmtTime, fmtPct, fmtUsd, fmtUsdSigned, RANGE_LABELS } from '$lib/chartKit.svelte.js';
  import { cachedStock } from '$lib/stockCache.js';
  import { trades as tradesStore, loadTrades } from '$lib/stores.js';
  import ChartFrame from './chart/ChartFrame.svelte';
  import ChartMenu from './chart/ChartMenu.svelte';
  import CompareMenu, { SP500 } from './chart/CompareMenu.svelte';
  import ChartTip from './chart/ChartTip.svelte';

  // equity = {x:['YYYY-MM-DD'...], y:[$...]} portfolio value
  // spy    = {x,y} parallel SPY portfolio ($) — same cash flows invested in SPY
  // twr    = {portfolio:{x,y}, spy:{x,y}} decimals — for the apples-to-apples % view
  // netInvested = {x,y} cumulative net deposits ($) — strips deposits out of a
  //          span's $ change so a measure reads earnings, not balance growth
  // flows = [{ date, amount }] every deposit (+) and withdrawal (−) — the Value bars
  // onwindow({ from, to, range, custom }) = the window on screen, for the Drivers
  //          tile: the range's bars, or the drag-measure span while measuring.
  //          custom = panned or measured, so the label should be dates.
  let { equity = { x: [], y: [] }, spy = null, twr = null, netInvested = null, flows = [], onwindow = null } = $props();

  // scale margins as a fraction of the plot: air above the peak, and under the low just enough for a buy arrow
  const MARGIN_TOP = 0.12, MARGIN_BOTTOM = 0.07;
  // curve : cash-flow strip, as pane stretch factors (the strip is a quarter of the plot)
  const FLOW_SPLIT = [3, 1];
  const RANGES = [
    { k: '1D',  days: 1 },
    { k: '1W',  days: 7 },
    { k: '1M',  days: 31 },
    { k: '3M',  days: 92 },
    { k: '6M',  days: 183 },
    { k: 'YTD', days: null },
    { k: '1Y',  days: 366 },
    { k: '2Y',  days: 731 },
    { k: '5Y',  days: 1827 },
    { k: '10Y', days: 3653 },
    { k: 'ALL', days: Infinity },
  ];

  // shared, theme-reactive palette (lib/chartTheme.js mirrors the app.css tokens)
  const PAL = $derived(chartPalette($theme));

  let range = $state('ALL');
  let mode = $state('return');    // 'value' | 'return' — Return is the default metric
  let panBars = $state(0);        // how many bars the fixed-width window is shifted back
  let showTrades = $state(true);  // buy/sell fills as markers
  let showFlows = $state(true);   // deposits / withdrawals as bars (Value only)

  // ── benchmarks: rebased-% overlays, portfolio plotted as its TWR growth ──
  // A Return-view feature (Value is dollars, so it sets them aside, list intact).
  // The S&P 500 is on until the user switches it off.
  let benchmarks = $state([{ ...SP500 }]);   // [{ sym, label, color }]
  let bmHist = $state({});       // sym → [{ t, c }] raw daily closes
  const comparing = $derived(mode === 'return' && benchmarks.length > 0);

  // The S&P 500 rides the dashboard payload (twr.spy), the same series the "vs SPY"
  // gap is read from, so the default overlay needs no request. Anything else loads
  // its daily closes once, via the shared module cache.
  const spyLine = $derived(rows.filter((r) => r.sret != null).map((r) => ({ t: r.t, c: 1 + r.sret })));
  const inPayload = (sym) => sym === 'SPY' && spyLine.length > 1;

  $effect(() => {
    const list = benchmarks.filter((b) => !untrack(() => inPayload(b.sym)));
    if (!list.length) { bmHist = {}; return; }
    let cancelled = false;
    (async () => {
      const out = {};
      await Promise.all(list.map(async ({ sym }) => {
        try {
          const r = await cachedStock(sym);
          out[sym] = (r?.history ?? []).filter((p) => p.c != null);
        } catch { out[sym] = []; }
      }));
      if (!cancelled) bmHist = out;
    })();
    return () => { cancelled = true; };
  });

  const mapOf = (xy) => {
    const m = new Map();
    if (xy?.x) for (let i = 0; i < xy.x.length; i++) m.set(xy.x[i], xy.y[i]);
    return m;
  };

  // Aligned daily rows, dropping points with no portfolio value.
  //   pv = portfolio $ · sv = parallel-SPY $ · pret/sret = TWR decimals · ni = net invested
  const rows = $derived.by(() => {
    const x = equity?.x ?? [], y = equity?.y ?? [];
    const svmap = mapOf(spy), pmap = mapOf(twr?.portfolio), smap = mapOf(twr?.spy), nimap = mapOf(netInvested);
    const out = [];
    for (let i = 0; i < x.length; i++) {
      if (y[i] == null) continue;
      out.push({
        t: x[i], pv: y[i], sv: svmap.get(x[i]) ?? null,
        pret: pmap.get(x[i]) ?? null, sret: smap.get(x[i]) ?? null,
        ni: nimap.get(x[i]) ?? null,
      });
    }
    return out;
  });

  // A brand-new account still gets a full calendar of points, just all zeros —
  // so "nothing to show" is an all-zero curve, not an empty array. The canvas
  // stays mounted (the chart is created from it in onMount); the controls hide
  // and an overlay covers the flat axes.
  const empty = $derived(rows.length === 0 || rows.every((r) => !r.pv));

  function isoMinusDays(iso, days) {
    const d = new Date(iso + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() - days);
    return d.toISOString().slice(0, 10);
  }
  function ytdCutoff(iso) { return iso.slice(0, 4) + '-01-01'; }

  // The visible window for the chosen range — a fixed bar-WIDTH that can be
  // shifted back through history by `panBars`, so every downstream read
  // (series, readout, rebasing, compare) tracks the window.
  const view = $derived.by(() => {
    const all = rows;
    if (all.length < 2) return all;
    const cfg = RANGES.find((r) => r.k === range);
    let W;
    if (!cfg || cfg.days === Infinity) W = all.length;
    else {
      const cutoff = cfg.k === 'YTD' ? ytdCutoff(all[all.length - 1].t) : isoMinusDays(all[all.length - 1].t, cfg.days);
      W = all.filter((r) => r.t >= cutoff).length;
    }
    W = Math.max(2, Math.min(W, all.length));
    const pan = Math.max(0, Math.min(panBars, all.length - W));
    const end = all.length - pan;          // exclusive
    return all.slice(Math.max(0, end - W), end);
  });
  const byKey = $derived(new Map(view.map((r) => [r.t, r])));

  const baseRow = $derived(view[0] ?? null);
  const lastRow = $derived(view.length ? view[view.length - 1] : null);

  // time-weighted return of b vs a (decimals → percent)
  const twRet = (b, a, key) =>
    b?.[key] == null || a?.[key] == null ? null : ((1 + b[key]) / (1 + a[key]) - 1) * 100;

  // the primary series: $ value, TWR % vs the window start, or (comparing) the
  // TWR growth index the Percentage scale rebases — raw value if TWR is missing
  const mainPts = $derived.by(() => {
    const v = view;
    if (comparing) {
      const g = v.filter((r) => r.pret != null).map((r) => ({ time: r.t, value: 1 + r.pret }));
      return g.length >= 2 ? g : v.map((r) => ({ time: r.t, value: r.pv }));
    }
    if (mode === 'value') return v.map((r) => ({ time: r.t, value: r.pv }));
    return v.filter((r) => r.pret != null).map((r) => ({ time: r.t, value: twRet(r, baseRow, 'pret') }));
  });

  // ── Lightweight Charts wiring ──
  let host = $state();
  let chart = $state(null);
  let main = null;
  let band = null;
  let bmSeries = [];
  let flowSeries = [];
  let flowDays = [];   // bar times carrying a flow, for the hover snap

  const ptr = new ChartPointer({
    points: () => mainPts,
    series: () => main,
    holdMs: 1,
    // over the strip, snap to the nearest flow bar within 14px
    snap: (_pane, x) => {
      let best = null, d = 14;
      for (const t of flowDays) {
        const dx = Math.abs((chart?.timeScale().timeToCoordinate(t) ?? Infinity) - x);
        if (dx < d) { d = dx; best = t; }
      }
      return best;
    },
    pan: (bars) => {
      const max = rows.length - view.length;
      if (max <= 0) return false; // whole series in view (e.g. ALL)
      panBars = Math.max(0, Math.min(Math.round(panBars + bars), max));
      return true;
    },
  });

  const hoverRow = $derived(ptr.hover ? byKey.get(timeKey(ptr.hover.time)) ?? null : null);

  // readout: the window's TWR + gap to SPY; while hovering, window start → that day
  const read = $derived.by(() => {
    const r = hoverRow ?? lastRow;
    if (!baseRow || !r) return null;
    const you = twRet(r, baseRow, 'pret'), bench = twRet(r, baseRow, 'sret');
    const gap = you != null && bench != null ? you - bench : null;
    return {
      pct: you,
      label: hoverRow ? fmtTime(hoverRow.t) : RANGE_LABELS[range] ?? '',
      extra: gap == null ? null : { text: fmtPct(gap) + ' vs SPY', up: gap >= 0 },
    };
  });

  // drag-measure: TWR % between the two days, and the $ change net of deposits
  const measure = $derived.by(() => {
    const s = ptr.span(mainPts);
    if (!s) return null;
    const a = byKey.get(timeKey(s.t0)), b = byKey.get(timeKey(s.t1));
    if (!a || !b) return null;
    const pct = twRet(b, a, 'pret') ?? (a.pv ? (b.pv / a.pv - 1) * 100 : null);
    const abs = b.pv - a.pv - (a.ni != null && b.ni != null ? b.ni - a.ni : 0);
    return { ...s, pct, abs };
  });

  // the window the Drivers tile explains. Follows range, pan and drag-measure,
  // not hover: a deliberate gesture re-ranks the bars, passing the mouse doesn't.
  const win = $derived.by(() => {
    if (measure) {
      const a = timeKey(measure.t0), b = timeKey(measure.t1);
      return { from: a <= b ? a : b, to: a <= b ? b : a, range, custom: true };
    }
    if (!baseRow || !lastRow) return null;
    return { from: baseRow.t, to: lastRow.t, range, custom: panBars > 0 };
  });
  $effect(() => { onwindow?.(win); });

  // ── my buy/sell fills, every ticker ──
  onMount(() => loadTrades());
  const marks = $derived(tradeMarkers(mainPts, $tradesStore ?? [], PAL));
  const hoverFills = $derived(
    ptr.hover && !measure && showTrades ? (marks.byKey.get(timeKey(ptr.hover.time)) ?? null) : null
  );

  // ── deposits and withdrawals, bucketed onto the bars that carry them ──
  const flowBars = $derived(flowBuckets(rows.map((r) => r.t), flows));
  const flowOn = $derived(mode === 'value' && showFlows && (flows?.length ?? 0) > 0);
  const hoverFlow = $derived(flowOn && hoverRow && !measure ? flowBars.get(hoverRow.t) ?? null : null);
  const keys = $derived(flowOn ? [{ label: 'Deposit', color: 'var(--gain)' }, { label: 'Withdrawal', color: 'var(--loss)' }] : []);
  // the strip's axis: whole dollars, k from a thousand, a bare 0 on the baseline
  const flowTick = (x) => {
    const a = Math.abs(x);
    return a < 0.5 ? '0' : (x < 0 ? '−$' : '$') + (a >= 1000 ? +(a / 1000).toFixed(1) + 'k' : Math.round(a));
  };

  onMount(() => {
    const base = baseChartOptions(PAL);
    chart = createChart(host, {
      ...base,
      rightPriceScale: { ...base.rightPriceScale, scaleMargins: { top: MARGIN_TOP, bottom: MARGIN_BOTTOM } },
    });
    band = addBand(chart);
    const detach = ptr.attach(chart, host);
    return () => { detach(); chart.remove(); chart = null; main = null; band = null; };
  });

  // re-skin chrome (axes, grid, crosshair) when the theme flips
  $effect(() => {
    if (!chart) return;
    chart.applyOptions(themeOptions(PAL));
  });

  // Rebuild the series whenever the window, mode, benchmarks, flows, fills or theme change.
  $effect(() => {
    if (!chart) return;
    const pts = mainPts, m = mode, cmp = comparing ? benchmarks : [], bmData = bmHist, v = view, strip = flowOn;

    if (main) chart.removeSeries(main);
    for (const s of bmSeries) chart.removeSeries(s);
    for (const s of flowSeries) chart.removeSeries(s);   // the strip's pane goes with its last series
    bmSeries = [];
    flowSeries = [];
    flowDays = [];

    // compare: rebased % via the Percentage scale; alone: $ or TWR % as-is
    chart.priceScale('right').applyOptions({ mode: cmp.length ? PriceScaleMode.Percentage : PriceScaleMode.Normal });
    // the axis stops at the data: a thin margin under the lowest point, and Value
    // (dollars) never runs under $0. Return and compare are % and can really go below 0.
    const vals = pts.map((p) => p.value);
    chart.priceScale('right').applyOptions({
      scaleMargins: {
        top: MARGIN_TOP,
        bottom: m === 'value' && !cmp.length
          ? bottomMargin(MARGIN_BOTTOM, MARGIN_TOP, Math.min(...vals), Math.max(...vals))
          : MARGIN_BOTTOM,
      },
    });
    chart.applyOptions({
      localization: {
        priceFormatter: cmp.length ? undefined : m === 'value'
          ? (x) => '$' + x.toLocaleString('en-US', { maximumFractionDigits: 0 })
          : (x) => (x >= 0 ? '+' : '−') + Math.abs(x).toFixed(0) + '%',
      },
    });

    // one area style for Value, Return and compare (chartTheme.areaStyle)
    main = chart.addSeries(AreaSeries, { ...areaStyle(), autoscaleInfoProvider: dataRange });
    main.setData(pts);
    // fills ride the fresh series, so the old markers go with the removed one
    createSeriesMarkers(main, showTrades ? marks.markers : []);
    if (!cmp.length && m === 'return') {
      main.createPriceLine({ price: 0, color: PAL.GRID, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false });
    }

    const lo = v[0]?.t, hi = v[v.length - 1]?.t;
    for (const b of cmp) {
      const hist = (inPayload(b.sym) ? spyLine : bmData[b.sym] ?? []).filter((p) => (!lo || p.t >= lo) && (!hi || p.t <= hi));
      if (hist.length < 2) continue;
      const s = chart.addSeries(LineSeries, {
        color: b.color, lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      });
      s.setData(hist.map((p) => ({ time: p.t, value: p.c })));
      bmSeries.push(s);
    }

    // cash flow: its own strip under the curve (pane 1) so it never crowds the value axis.
    // Deposits rise from the baseline, withdrawals hang below it.
    if (strip) {
      const dep = [], wd = [];
      for (const r of v) {
        const b = flowBars.get(r.t);
        if (b?.dep) dep.push({ time: r.t, value: b.dep, color: hexA(PAL.GAIN, 0.85) });
        if (b?.wd) wd.push({ time: r.t, value: -b.wd, color: hexA(PAL.LOSS, 0.85) });
      }
      flowDays = [...dep, ...wd].map((p) => p.time);
      const bar = { priceLineVisible: false, lastValueVisible: false, priceFormat: { type: 'custom', minMove: 1, formatter: flowTick } };
      // the histograms only carry the data (and so the axis); the primitive draws the bars
      const up = chart.addSeries(HistogramSeries, { ...bar, color: 'rgba(0,0,0,0)' }, 1);
      const down = chart.addSeries(HistogramSeries, { ...bar, color: 'rgba(0,0,0,0)' }, 1);
      up.setData(dep);
      down.setData(wd);
      up.attachPrimitive(flowBarsPrimitive(chart, up, [...dep, ...wd]));
      flowSeries = [up, down];
      chart.priceScale('right', 1).applyOptions({ scaleMargins: { top: 0.14, bottom: 0.14 } });
      chart.panes().forEach((p, i) => p.setStretchFactor(FLOW_SPLIT[i] ?? 1));
    }

    chart.timeScale().fitContent();
  });

  $effect(() => { paintBand(band, mainPts, measure, PAL); });
</script>

<div class="pc">
  {#if empty}
    <div class="pc-empty">
      <div class="pc-empty-t">No activity yet</div>
      <div class="pc-empty-s">Log a deposit or your first trade to start the curve.</div>
    </div>
  {/if}
  <ChartFrame ranges={RANGES.map((r) => r.k)} bind:range onrange={() => (panBars = 0)}
    bind:compares={benchmarks} self="You" showCompares={mode === 'return'} {keys} {read} bare={empty}>
    {#snippet tools()}
      {#if mode === 'return'}<CompareMenu bind:list={benchmarks} />{/if}
      <ChartMenu label="Indicators" icon="indicators" width={185}>
        <button class="cm-item" class:sel={showTrades} onclick={() => (showTrades = !showTrades)}><span class="cm-check">{showTrades ? '✓' : ''}</span>My trades</button>
        {#if mode === 'value'}
          <button class="cm-item" class:sel={showFlows} onclick={() => (showFlows = !showFlows)}><span class="cm-check">{showFlows ? '✓' : ''}</span>Cash flow</button>
        {/if}
      </ChartMenu>
    {/snippet}
    {#snippet right()}
      <div class="pc-toggle" role="group" aria-label="metric">
        <button class:on={mode === 'value'} onclick={() => (mode = 'value')}>Value</button>
        <button class:on={mode === 'return'} onclick={() => (mode = 'return')}>Return</button>
      </div>
    {/snippet}

    <div class="pc-canvas" bind:this={host}></div>
    {#if measure}
      <div class="pc-anchor" style="left:{ptr.anchor.x}px"></div>
      <ChartTip x={ptr.hover.x} y={ptr.hover.y} tone={(measure.pct ?? measure.abs) >= 0 ? 'pos' : 'neg'}
        value={fmtUsdSigned(measure.abs)} aside={fmtPct(measure.pct)}
        sub="{fmtTime(measure.t0)} → {fmtTime(measure.t1)}" />
    {:else if hoverRow}
      <ChartTip x={ptr.hover.x} y={ptr.hover.y} value={fmtUsd(hoverRow.pv)}
        lines={[...flowLines(hoverFlow), ...tradeLines(hoverFills, (t) => (t.ticker || '').toUpperCase())]} />
    {/if}
  </ChartFrame>
</div>

<style>
  /* chrome-less: the host's .chart-widget is the widget */
  .pc { position: relative; height: 100%; min-width: 0; }

  /* empty account: cover the bare axes */
  .pc-empty { position: absolute; inset: 0; z-index: 6; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 4px; padding: 16px;
    background: var(--surface); text-align: center; }
  .pc-empty-t { font-family: var(--sans); font-size: var(--fs-title); font-weight: 600; color: var(--ink); }
  .pc-empty-s { font-family: var(--sans); font-size: var(--fs-body); font-weight: 500; color: var(--muted); }

  /* pan-y: vertical swipes keep scrolling the page; horizontal drags and the
     scrub belong to the chart */
  .pc-canvas { position: absolute; inset: 0; overflow: hidden; touch-action: pan-y; user-select: none; }
  .pc-anchor { position: absolute; top: 0; bottom: 0; width: 0; z-index: 4; pointer-events: none;
    border-left: 1px dashed var(--muted); }

  /* metric toggle — system pills (text → outline hover → solid ink when on) */
  .pc-toggle { display: inline-flex; gap: 2px; }
  .pc-toggle button { font-family: var(--sans); font-size: var(--fs-body); font-weight: 600; cursor: pointer;
    padding: 5px 12px; background: transparent; color: var(--muted);
    border: var(--bw) solid transparent; border-radius: 999px;
    transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .pc-toggle button:hover { color: var(--ink); border-color: var(--ink); }
  .pc-toggle button.on { background: var(--ink); color: var(--paper); border-color: var(--ink); }
</style>
