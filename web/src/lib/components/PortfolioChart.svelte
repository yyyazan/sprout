<script>
  // First-class interactive portfolio chart — fills cols 4–6 beside the peek.
  // Hero = portfolio value ($) as an area, with SPY overlaid as "the same starting
  // money grown at SPY's return" (rebased to the visible window's start, so the gap
  // between the lines reads as out/under-performance). A Value|Return toggle flips
  // both to time-weighted % from the window start. Range buttons zoom the window;
  // the crosshair re-reads the big header number + delta to the hovered point.
  import { onMount } from 'svelte';
  import { createChart, AreaSeries, LineSeries, ColorType, CrosshairMode, LineStyle } from 'lightweight-charts';

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

  const BRAND = '#0fb39a', SPY_C = '#b3ab9c', GRID = '#ececea', MUTED = '#8a8478';

  let range = $state('ALL');
  let mode = $state('value');     // 'value' | 'return'
  let hoverRow = $state(null);    // aligned row under the crosshair, or null at rest

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
        textColor: MUTED, fontFamily: 'Space Mono, ui-monospace, monospace',
        fontSize: 11, attributionLogo: false,
      },
      grid: { vertLines: { visible: false }, horzLines: { color: GRID } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.08 } },
      timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: { color: '#1a1a1a', width: 1, style: LineStyle.Solid, labelVisible: false },
        horzLine: { color: GRID, width: 1, style: LineStyle.Dotted, labelVisible: false },
      },
      handleScroll: false, handleScale: false,
    });

    chart.subscribeCrosshairMove((p) => {
      if (!p.time || !p.point || p.point.x < 0) { hoverRow = null; return; }
      hoverRow = byTime.get(p.time) ?? null;
    });

    return () => { chart.remove(); chart = null; };
  });

  // Rebuild series whenever the window or mode changes.
  $effect(() => {
    if (!chart) return;
    const v = view, m = mode, base = baseRow;
    const showSpy = m === 'value' ? hasSpyUsd : hasSpyRet;

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
      const area = chart.addSeries(AreaSeries, {
        lineColor: BRAND, lineWidth: 2,
        topColor: hexA(BRAND, 0.26), bottomColor: hexA(BRAND, 0),
        priceLineVisible: false, lastValueVisible: false,
      });
      area.setData(v.map((r) => ({ time: r.t, value: r.pv })));
      handles.push(area);
      if (showSpy) {
        const sp = chart.addSeries(LineSeries, {
          color: SPY_C, lineWidth: 1.5, lineStyle: LineStyle.Dotted,
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
          color: SPY_C, lineWidth: 1.5, lineStyle: LineStyle.Dotted,
          priceLineVisible: false, lastValueVisible: false,
        });
        sp.setData(v.filter((r) => r.sret != null).map((r) => ({ time: r.t, value: twRet(r, base, 'sret') })));
        handles.push(sp);
      }
      handles[0].createPriceLine({
        price: 0, color: GRID, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false,
      });
    }

    chart.timeScale().fitContent();
  });
</script>

<div class="glass-card pc-card">
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
</div>

<style>
  .pc-card { display: flex; flex-direction: column; padding: 16px 18px; gap: 10px; height: 100%; }

  .pc-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .pc-read { min-width: 0; }
  .pc-label { font-size: 10px; text-transform: uppercase; letter-spacing: .1em; font-weight: 700;
    color: var(--ink); opacity: .55; margin-bottom: 4px; white-space: nowrap; }
  .pc-value { font-family: var(--mono); font-size: 30px; font-weight: 700; line-height: 1;
    font-variant-numeric: tabular-nums; }
  .pc-delta { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; margin-top: 6px;
    font-family: var(--mono); font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .pc-muted { color: var(--muted); font-weight: 400; }

  /* metric toggle — segmented ink radio, matching the deck's winbar */
  .pc-toggle { display: inline-flex; flex: 0 0 auto; border: var(--bw) solid var(--ink);
    border-radius: var(--r); overflow: hidden; box-shadow: var(--sh); }
  .pc-toggle button { font-family: var(--mono); font-size: 11px; font-weight: 700; cursor: pointer;
    padding: 6px 11px; background: var(--surface); color: var(--ink); border: 0;
    border-right: var(--bw) solid var(--ink); }
  .pc-toggle button:last-child { border-right: 0; }
  .pc-toggle button.on { background: var(--ink); color: var(--surface); }

  .pc-canvas { flex: 1; min-height: 180px; }

  /* range pills — lighter weight than the toggle, selected = ink underline chip */
  .pc-ranges { display: flex; gap: 6px; }
  .pc-ranges button { font-family: var(--mono); font-size: 12px; font-weight: 700; cursor: pointer;
    padding: 4px 12px; background: var(--surface); color: var(--muted);
    border: var(--bw) solid var(--ink); border-radius: var(--r); transition: transform .1s, box-shadow .1s; }
  .pc-ranges button:hover { color: var(--ink); transform: translate(-1px, -1px); box-shadow: 3px 3px 0 var(--ink); }
  .pc-ranges button.on { background: var(--ink); color: var(--surface); }

  .up { color: var(--gain); }
  .down { color: var(--loss); }

  @media (max-width: 1100px) {
    .pc-canvas { min-height: 220px; }
  }
</style>
