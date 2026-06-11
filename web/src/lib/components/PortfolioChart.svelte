<script>
  // First-class interactive portfolio chart — fills cols 4–6 beside the peek.
  // Hero = portfolio value ($) as an area, with SPY overlaid as "the same starting
  // money grown at SPY's return" (rebased to the visible window's start, so the gap
  // between the lines reads as out/under-performance). A Value|Return toggle flips
  // both to time-weighted % from the window start. Range buttons zoom the window;
  // the crosshair re-reads the big header number + delta to the hovered point.
  import { onMount } from 'svelte';
  import { createChart, AreaSeries, LineSeries, ColorType, CrosshairMode, LineStyle, TrackingModeExitMode } from 'lightweight-charts';
  import { theme } from '$lib/theme.js';

  // equity = {x:['YYYY-MM-DD'...], y:[$...]} portfolio value
  // spy    = {x,y} parallel SPY portfolio ($) — same cash flows invested in SPY
  //          (the honest $ benchmark; the gap is real performance, not deposits)
  // twr    = {portfolio:{x,y}, spy:{x,y}} decimals — for the apples-to-apples % view
  let { equity = { x: [], y: [] }, spy = null, twr = null } = $props();

  const RANGES = [
    { k: '1W', days: 7 },
    { k: '1M', days: 31 },
    { k: '3M', days: 92 },
    { k: '1Y', days: 366 },
    { k: 'ALL', days: Infinity },
  ];

  const BRAND = '#0fb39a';
  // theme-reactive chart palette (lightweight-charts can't read CSS vars)
  const PAL = $derived($theme === 'light'
    ? { INK: '#1a1a1a', GRID: '#e7e1d3', MUTED: '#8a8478', SPY: '#b3ab9c' }
    : { INK: '#faf7f0', GRID: '#2a2722', MUTED: '#8f897c', SPY: '#7d776b' });

  let range = $state('ALL');
  let mode = $state('value');     // 'value' | 'return'
  let chartType = $state('area'); // 'area' | 'line' — render of the value series
  let benchmark = $state(true);   // show the SPY overlay line
  let openMenu = $state(null);    // 'type' | 'compare' | null — toolbar dropdowns
  let hoverRow = $state(null);    // aligned row under the crosshair, or null at rest
  const toggleMenu = (m) => (openMenu = openMenu === m ? null : m);

  const mapOf = (xy) => {
    const m = new Map();
    if (xy?.x) for (let i = 0; i < xy.x.length; i++) m.set(xy.x[i], xy.y[i]);
    return m;
  };

  // Aligned daily rows, dropping points with no portfolio value.
  //   pv = portfolio $ · sv = parallel-SPY $ · pret/sret = TWR decimals
  const rows = $derived.by(() => {
    const x = equity?.x ?? [], y = equity?.y ?? [];
    const svmap = mapOf(spy), pmap = mapOf(twr?.portfolio), smap = mapOf(twr?.spy);
    const out = [];
    for (let i = 0; i < x.length; i++) {
      if (y[i] == null) continue;
      out.push({
        t: x[i], pv: y[i], sv: svmap.get(x[i]) ?? null,
        pret: pmap.get(x[i]) ?? null, sret: smap.get(x[i]) ?? null,
      });
    }
    return out;
  });

  function isoMinusDays(iso, days) {
    const d = new Date(iso + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() - days);
    return d.toISOString().slice(0, 10);
  }

  // The visible window for the chosen range (always ≥2 points if data allows).
  const view = $derived.by(() => {
    const all = rows;
    if (all.length < 2) return all;
    const cfg = RANGES.find((r) => r.k === range);
    if (!cfg || cfg.days === Infinity) return all;
    const cutoff = isoMinusDays(all[all.length - 1].t, cfg.days);
    const sliced = all.filter((r) => r.t >= cutoff);
    return sliced.length >= 2 ? sliced : all.slice(-2);
  });

  const baseRow = $derived(view[0] ?? null);
  // Dollar overlay (Value mode) needs the parallel-SPY $ series; the % overlay
  // (Return mode) needs a TWR anchor at the window start.
  const hasSpyUsd = $derived(view.some((r) => r.sv != null));
  const hasSpyRet = $derived(!!(baseRow && baseRow.sret != null && view.some((r) => r.sret != null)));

  // time-weighted return of a row vs the window start (decimals → percent)
  const twRet = (r, base, key) =>
    r?.[key] == null || base?.[key] == null ? null : ((1 + r[key]) / (1 + base[key]) - 1) * 100;

  // The number block reads the hovered row, or the latest point at rest.
  const read = $derived.by(() => {
    if (!view.length) return null;
    const r = hoverRow ?? view[view.length - 1];
    return {
      t: r.t,
      pv: r.pv,
      youPct: twRet(r, baseRow, 'pret'),
      spyPct: twRet(r, baseRow, 'sret'),
      gap: hasSpyUsd && r.sv != null ? r.pv - r.sv : null,   // real $ ahead of / behind SPY
    };
  });

  const fmtUsd = (n) => '$' + Math.round(n).toLocaleString('en-US');
  const fmtUsdSigned = (n) => (n >= 0 ? '+$' : '−$') + Math.round(Math.abs(n)).toLocaleString('en-US');
  const fmtPct = (n) => (n == null ? '—' : (n >= 0 ? '+' : '') + n.toFixed(1) + '%');
  const fmtDate = (iso) =>
    new Date(iso + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  // ── Lightweight Charts wiring ──
  let host = $state();
  let chart = null;
  let byTime = new Map();   // window time → row, for the crosshair read
  let handles = [];

  function hexA(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
  }

  onMount(() => {
    chart = createChart(host, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'rgba(0,0,0,0)' },
        textColor: PAL.MUTED, fontFamily: 'Space Mono, ui-monospace, monospace',
        fontSize: 11, attributionLogo: false,
      },
      grid: { vertLines: { visible: false }, horzLines: { color: PAL.GRID } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.08 } },
      timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: { color: PAL.INK, width: 1, style: LineStyle.Solid, labelVisible: false },
        horzLine: { color: PAL.GRID, width: 1, style: LineStyle.Dotted, labelVisible: false },
      },
      handleScroll: false, handleScale: false,
      // touch: press-drag scrubs the crosshair (Apple-Stocks style), stays until
      // the next tap. Range stays fixed — the range pills own the window.
      trackingMode: { exitMode: TrackingModeExitMode.OnNextTap },
    });

    chart.subscribeCrosshairMove((p) => {
      if (!p.time || !p.point || p.point.x < 0) { hoverRow = null; return; }
      hoverRow = byTime.get(p.time) ?? null;
    });

    return () => { chart.remove(); chart = null; };
  });

  // close the toolbar dropdowns on any outside click
  function onWindowClick(e) { if (!e.target.closest?.('.pc-tool')) openMenu = null; }
  onMount(() => { window.addEventListener('click', onWindowClick); return () => window.removeEventListener('click', onWindowClick); });

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

  // Rebuild series whenever the window, mode, or theme changes.
  $effect(() => {
    if (!chart) return;
    const v = view, m = mode, base = baseRow, t = chartType;
    const showSpy = benchmark && (m === 'value' ? hasSpyUsd : hasSpyRet);

    for (const h of handles) chart.removeSeries(h);
    handles = [];
    byTime = new Map(v.map((r) => [r.t, r]));

    chart.applyOptions({
      localization: {
        priceFormatter: m === 'value'
          ? (x) => '$' + x.toLocaleString('en-US', { maximumFractionDigits: 0 })
          : (x) => (x >= 0 ? '+' : '') + x.toFixed(0) + '%',
      },
    });

    if (m === 'value') {
      const main = t === 'line'
        ? chart.addSeries(LineSeries, { color: BRAND, lineWidth: 2, priceLineVisible: false, lastValueVisible: false })
        : chart.addSeries(AreaSeries, {
            lineColor: BRAND, lineWidth: 2,
            topColor: hexA(BRAND, 0.26), bottomColor: hexA(BRAND, 0),
            priceLineVisible: false, lastValueVisible: false,
          });
      main.setData(v.map((r) => ({ time: r.t, value: r.pv })));
      handles.push(main);
      if (showSpy) {
        const sp = chart.addSeries(LineSeries, {
          color: PAL.SPY, lineWidth: 1.5, lineStyle: LineStyle.Dotted,
          priceLineVisible: false, lastValueVisible: false,
        });
        sp.setData(v.filter((r) => r.sv != null).map((r) => ({ time: r.t, value: r.sv })));
        handles.push(sp);
      }
    } else {
      const you = chart.addSeries(LineSeries, {
        color: BRAND, lineWidth: 2, priceLineVisible: false, lastValueVisible: false,
      });
      you.setData(v.filter((r) => r.pret != null).map((r) => ({ time: r.t, value: twRet(r, base, 'pret') })));
      handles.push(you);
      if (showSpy) {
        const sp = chart.addSeries(LineSeries, {
          color: PAL.SPY, lineWidth: 1.5, lineStyle: LineStyle.Dotted,
          priceLineVisible: false, lastValueVisible: false,
        });
        sp.setData(v.filter((r) => r.sret != null).map((r) => ({ time: r.t, value: twRet(r, base, 'sret') })));
        handles.push(sp);
      }
      handles[0].createPriceLine({
        price: 0, color: PAL.GRID, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false,
      });
    }

    chart.timeScale().fitContent();
  });
</script>

<!-- two widgets matching the stock view's grid language: header (split 2-up) + chart -->
<div class="pcg">
  <div class="pc-head-row">
  <section class="pc-w pc-head-w">
  <div class="pc-eyebrow"><span class="pc-dot" aria-hidden="true"></span>Your portfolio</div>
  <div class="pc-head">
    <div class="pc-read">
      <div class="pc-label">
        {hoverRow ? fmtDate(read?.t) : (mode === 'value' ? 'Portfolio value' : 'Time-weighted return')}
      </div>
      {#if read}
        {#if mode === 'value'}
          <div class="pc-value">{fmtUsd(read.pv)}</div>
          <div class="pc-delta">
            {#if read.gap != null}
              <span class={read.gap >= 0 ? 'up' : 'down'}>{fmtUsdSigned(read.gap)} vs SPY</span>
            {/if}
            <span class="pc-muted">you {fmtPct(read.youPct)}{#if read.spyPct != null} · SPY {fmtPct(read.spyPct)}{/if}</span>
          </div>
        {:else}
          <div class="pc-value {(read.youPct ?? 0) >= 0 ? 'up' : 'down'}">{fmtPct(read.youPct)}</div>
          <div class="pc-delta">
            {#if read.spyPct != null}
              <span class="pc-muted">SPY {fmtPct(read.spyPct)}</span>
              {#if read.youPct != null}
                {@const diff = read.youPct - read.spyPct}
                <span class={diff >= 0 ? 'up' : 'down'}>{(diff >= 0 ? '+' : '') + diff.toFixed(1)}pp {diff >= 0 ? 'ahead' : 'behind'}</span>
              {/if}
            {/if}
          </div>
        {/if}
      {/if}
    </div>
  </div>
  </section>
  <!-- right half intentionally blank — placeholder for a future widget -->
  <section class="pc-w pc-head-empty" aria-hidden="true"></section>
  </div>

  <section class="pc-w pc-chart-w">
    <!-- toolbar mirrors the stock chart's gf-bar so both views line up -->
    <div class="pc-bar">
      <div class="pc-tool">
        <button class="pc-btn" class:active={openMenu === 'type'} onclick={() => toggleMenu('type')}>
          <svg class="pc-ic" viewBox="0 0 24 24" aria-hidden="true"><polyline points="2,15 8,9 13,13 22,4" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" /></svg>{chartType === 'line' ? 'Line' : 'Area'}<span class="pc-cv" aria-hidden="true">▾</span>
        </button>
        {#if openMenu === 'type'}
          <div class="pc-menu">
            <button class="pc-item" class:sel={chartType === 'area'} onclick={() => { chartType = 'area'; openMenu = null; }}>Area</button>
            <button class="pc-item" class:sel={chartType === 'line'} onclick={() => { chartType = 'line'; openMenu = null; }}>Line</button>
          </div>
        {/if}
      </div>

      <div class="pc-tool">
        <button class="pc-btn" class:active={openMenu === 'compare'} onclick={() => toggleMenu('compare')}>
          <span class="pc-ic" aria-hidden="true">⇄</span>Benchmark<span class="pc-cv" aria-hidden="true">▾</span>
        </button>
        {#if openMenu === 'compare'}
          <div class="pc-menu pc-menu-wide">
            <button class="pc-item" class:sel={benchmark} onclick={() => (benchmark = !benchmark)}>
              <span class="pc-check">{benchmark ? '✓' : ''}</span>S&amp;P 500<span class="pc-sym">SPY</span>
            </button>
          </div>
        {/if}
      </div>

      <div class="pc-toggle" role="group" aria-label="metric">
        <button class:on={mode === 'value'} onclick={() => (mode = 'value')}>Value</button>
        <button class:on={mode === 'return'} onclick={() => (mode = 'return')}>Return</button>
      </div>
    </div>

    <div class="pc-canvas" bind:this={host}></div>
    <div class="pc-ranges" role="group" aria-label="range">
      {#each RANGES as r}
        <button class:on={range === r.k} onclick={() => (range = r.k)}>{r.k}</button>
      {/each}
    </div>
  </section>
</div>

<style>
  /* two stacked widgets, same grid language as the stock view */
  .pcg { display: flex; flex-direction: column; gap: 16px; height: 100%; min-height: 0; }
  .pc-w { background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-sizing: border-box; }
  /* header row is split 2-up (right half blank for now); both halves + the chart
     box are pinned to the stock view's dimensions (--title-h header · 440 chart)
     so the graph sits in the same place when you toggle modes */
  .pc-head-row { flex: 0 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .pc-head-w { height: var(--title-h, 152px); display: flex; flex-direction: column;
    gap: 10px; padding: 12px 16px 14px; box-sizing: border-box; }
  .pc-head-empty { height: var(--title-h, 152px); }
  .pc-chart-w { flex: 0 0 440px; min-height: 0; display: flex; flex-direction: column; gap: 10px;
    padding: 14px 16px; }
  .pc-eyebrow { display: flex; align-items: center; gap: 7px; font-family: var(--sans); font-size: 10px;
    font-weight: 700; text-transform: uppercase; letter-spacing: .14em; color: var(--brand); }
  .pc-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--brand); border: 1.5px solid var(--ink); }

  .pc-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .pc-read { min-width: 0; }
  .pc-label { font-size: 10px; text-transform: uppercase; letter-spacing: .1em; font-weight: 700;
    color: var(--ink); opacity: .55; margin-bottom: 4px; white-space: nowrap; }
  .pc-value { font-family: var(--mono); font-size: 30px; font-weight: 700; line-height: 1;
    font-variant-numeric: tabular-nums; }
  .pc-delta { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; margin-top: 6px;
    font-family: var(--mono); font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .pc-muted { color: var(--muted); font-weight: 400; }

  /* toolbar — mirrors StockChart's .gf-bar so the two charts align pixel-for-pixel */
  .pc-bar { display: flex; align-items: center; gap: 8px; flex: 0 0 auto; }
  .pc-tool { position: relative; }
  .pc-btn { display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
    font-family: var(--sans); font-size: 12px; font-weight: 700; color: var(--ink);
    padding: 5px 12px; background: transparent; border: var(--bw) solid var(--hairline);
    border-radius: 999px; transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .pc-btn:hover { border-color: var(--ink); }
  .pc-btn.active { background: var(--ink); border-color: var(--ink); color: var(--paper); }
  .pc-ic { font-size: 13px; opacity: .7; }
  svg.pc-ic { width: 14px; height: 14px; }
  .pc-cv { font-size: 9px; opacity: .6; margin-left: 1px; }
  .pc-menu { position: absolute; top: calc(100% + 5px); left: 0; z-index: 20; min-width: 150px;
    display: flex; flex-direction: column; padding: 5px; gap: 1px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh); }
  .pc-menu-wide { min-width: 185px; }
  .pc-item { display: flex; align-items: center; gap: 8px; width: 100%; cursor: pointer; text-align: left;
    font-family: var(--sans); font-size: 12.5px; font-weight: 600; color: var(--ink);
    padding: 7px 9px; border: 0; background: transparent; border-radius: 6px; }
  .pc-item:hover { background: var(--hover); }
  .pc-item.sel { font-weight: 700; }
  .pc-check { flex: 0 0 14px; font-size: 12px; color: var(--brand); }
  .pc-sym { margin-left: auto; font-family: var(--mono); font-size: 10px; color: var(--muted); }

  /* metric toggle — system pills (text → outline hover → solid ink when on) */
  .pc-toggle { display: inline-flex; flex: 0 0 auto; gap: 2px; margin-left: auto; }
  .pc-toggle button { font-family: var(--mono); font-size: 11px; font-weight: 600; cursor: pointer;
    padding: 5px 12px; background: transparent; color: var(--muted);
    border: var(--bw) solid transparent; border-radius: 999px;
    transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .pc-toggle button:hover { color: var(--ink); border-color: var(--ink); }
  .pc-toggle button.on { background: var(--ink); color: var(--paper); border-color: var(--ink); }

  /* pan-y: vertical swipes keep scrolling the page; horizontal drags and the
     long-press scrub belong to the chart */
  .pc-canvas { flex: 1; min-height: 0; touch-action: pan-y; }

  /* GF-style range tabs — identical states to StockChart's .gf-range */
  .pc-ranges { display: flex; align-items: center; gap: 2px;
    border-top: var(--bw) solid var(--hairline); padding-top: 8px; }
  .pc-ranges button { font-family: var(--mono); font-size: 11px; font-weight: 600; cursor: pointer; color: var(--muted);
    padding: 4px 11px; background: transparent; border: var(--bw) solid transparent; border-radius: 999px;
    letter-spacing: .02em; transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .pc-ranges button:hover { color: var(--ink); border-color: var(--ink); }
  .pc-ranges button.on { color: var(--paper); background: var(--ink); border-color: var(--ink); }

  .up { color: var(--gain); }
  .down { color: var(--loss); }

  /* mirror StockPanel's <900 shrink so the two charts stay matched on small screens */
  @media (max-width: 900px) {
    .pc-chart-w { flex-basis: 340px; }
  }
</style>
