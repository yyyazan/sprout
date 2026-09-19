<script>
  // First-class interactive portfolio chart. The header reads PERFORMANCE over the
  // selected range — a deposit-stripped $ gain + the window's time-weighted return,
  // and the gap to SPY — so the range buttons (1W…ALL) drive the headline, not just
  // the zoom. Scrubbing the crosshair swaps it for the hovered day's value and its
  // return-to-date. A Value|Return toggle flips the plotted line between $ and
  // time-weighted %; adding benchmarks rebases everything to the window start.
  import { onMount } from 'svelte';
  import { createChart, AreaSeries, LineSeries, LineStyle, PriceScaleMode } from 'lightweight-charts';
  import { theme } from '$lib/theme.js';
  import { BRAND, chartPalette, baseChartOptions, themeOptions } from '$lib/chartTheme.js';
  import { api } from '$lib/api.js';
  import { cachedStock } from '$lib/stockCache.js';

  // equity = {x:['YYYY-MM-DD'...], y:[$...]} portfolio value
  // spy    = {x,y} parallel SPY portfolio ($) — same cash flows invested in SPY
  //          (the honest $ benchmark; the gap is real performance, not deposits)
  // twr    = {portfolio:{x,y}, spy:{x,y}} decimals — for the apples-to-apples % view
  // netInvested = {x,y} cumulative net deposits ($) — lets a window's $ gain strip
  //          out deposits, so the headline reads earnings rather than balance growth
  let { equity = { x: [], y: [] }, spy = null, twr = null, netInvested = null } = $props();

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
  let openMenu = $state(null);    // 'compare' | null — toolbar dropdowns
  let hoverRow = $state(null);    // aligned row under the crosshair, or null at rest
  const toggleMenu = (m) => (openMenu = openMenu === m ? null : m);

  // ── benchmark compare — same framework as the stock view's compare ──
  // Add any number of tickers as benchmarks. When ≥1 is active the chart flips
  // to a rebased-% comparison: portfolio shows its time-weighted return, each
  // benchmark shows its price % — all rebased to the window start (the honest
  // apples-to-apples read), so Value/Return is set aside while comparing.
  const QUICK_BMS = [
    { sym: 'SPY', label: 'S&P 500' },
    { sym: 'QQQ', label: 'Nasdaq 100' },
    { sym: 'BTC-USD', label: 'Bitcoin' },
  ];
  const BM_COLORS = ['#5b8def', '#ff90e8', '#ffc900', '#c994e8', '#ff6e5e'];
  const BM_MAX = 4;

  let benchmarks = $state([]);   // [{ sym, label, color }]
  let bmHist = $state({});       // sym → [{ t, c }] raw daily closes
  let bmQ = $state('');
  let bmResults = $state([]);
  let bmLoading = $state(false);
  const comparing = $derived(benchmarks.length > 0);

  const benched = (sym) => benchmarks.some((b) => b.sym === sym);
  function toggleBenchmark(sym, label) {
    const s = (sym || '').toUpperCase();
    if (benched(s)) { benchmarks = benchmarks.filter((b) => b.sym !== s); return; }
    if (benchmarks.length >= BM_MAX) return;
    const used = new Set(benchmarks.map((b) => b.color));
    benchmarks = [...benchmarks, { sym: s, label: label ?? s, color: BM_COLORS.find((c) => !used.has(c)) ?? BM_COLORS[0] }];
    bmQ = '';
    bmResults = [];
  }

  // debounced ticker search for the benchmark menu (180ms, stale-proof)
  let bmSeq = 0, bmTimer = null;
  $effect(() => {
    const q = bmQ.trim();
    if (bmTimer) clearTimeout(bmTimer);
    if (!q) { bmResults = []; bmLoading = false; return; }
    bmLoading = true;
    const mine = ++bmSeq;
    bmTimer = setTimeout(async () => {
      try {
        const r = await api.search(q);
        if (mine !== bmSeq) return;
        bmResults = (r.results ?? []).slice(0, 6);
      } catch {
        if (mine === bmSeq) bmResults = [];
      } finally {
        if (mine === bmSeq) bmLoading = false;
      }
    }, 180);
  });

  // fetch each benchmark's daily history once, via the shared module cache
  $effect(() => {
    const list = benchmarks;
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
  //   pv = portfolio $ · sv = parallel-SPY $ · pret/sret = TWR decimals
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
  // stays mounted (the chart is created from it in onMount, so unmounting would
  // leave it uncreated once the first trade lands); the toolbar and ranges hide
  // and an overlay covers the flat axes.
  const empty = $derived(rows.length === 0 || rows.every((r) => !r.pv));

  function isoMinusDays(iso, days) {
    const d = new Date(iso + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() - days);
    return d.toISOString().slice(0, 10);
  }
  function ytdCutoff(iso) { return iso.slice(0, 4) + '-01-01'; }

  // The visible window for the chosen range — a fixed bar-WIDTH (W) that can be
  // shifted back through history by `panBars` (two-finger horizontal scroll), so
  // every downstream read (series, stats, rebasing, compare) tracks the window.
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

  const baseRow = $derived(view[0] ?? null);

  // time-weighted return of a row vs the window start (decimals → percent)
  const twRet = (r, base, key) =>
    r?.[key] == null || base?.[key] == null ? null : ((1 + r[key]) / (1 + base[key]) - 1) * 100;

  // SCRUBBING readout: the hovered day's value + its return-to-date (vs the window
  // start). Null at rest — the rest-state headline is `period` below.
  const read = $derived.by(() => {
    if (!hoverRow) return null;
    return {
      t: hoverRow.t,
      pv: hoverRow.pv,
      youPct: twRet(hoverRow, baseRow, 'pret'),
      spyPct: twRet(hoverRow, baseRow, 'sret'),
    };
  });

  const RANGE_LABELS = {
    '1D': 'today', '1W': 'past week', '1M': 'past month', '3M': 'past 3 months', '6M': 'past 6 months',
    'YTD': 'year to date', '1Y': 'past year', '2Y': 'past 2 years', '5Y': 'past 5 years', '10Y': 'past 10 years',
    'ALL': 'all-time',
  };

  // REST-state readout = the visible window's time-weighted return and the gap
  // to SPY in percentage points.
  const lastRow = $derived(view.length ? view[view.length - 1] : null);
  const period = $derived.by(() => {
    if (!baseRow || !lastRow) return null;
    const youPct = twRet(lastRow, baseRow, 'pret');
    const spyPct = twRet(lastRow, baseRow, 'sret');
    return { youPct, vs: youPct != null && spyPct != null ? youPct - spyPct : null };
  });

  const fmtUsd = (n) => '$' + Math.round(n).toLocaleString('en-US');
  const fmtPct = (n) => (n == null ? '—' : (n >= 0 ? '+' : '') + n.toFixed(1) + '%');
  const fmtDate = (iso) =>
    new Date(iso + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  // ── Lightweight Charts wiring ──
  let host = $state();
  let chart = null;
  let byTime = new Map();   // window time → row, for the crosshair read
  let handles = [];
  let mainData = [];        // the primary series' points — drives the touch scrub

  function hexA(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
  }

  // Two-finger / horizontal-wheel pan: shift the fixed-width window back/forward
  // through history (no zoom). Vertical scroll stays with the page.
  function onWheel(e) {
    if (!chart || Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
    const N = rows.length, W = view.length;
    if (N <= W) return; // whole series in view (e.g. ALL) — nothing to pan
    e.preventDefault();
    panBars = Math.max(0, Math.min(Math.round(panBars - e.deltaX / 8), N - W));
  }

  onMount(() => {
    const base = baseChartOptions(PAL);
    chart = createChart(host, {
      ...base,
      rightPriceScale: { ...base.rightPriceScale, scaleMargins: { top: 0.12, bottom: 0.08 } },
    });

    chart.subscribeCrosshairMove((p) => {
      if (!p.time || !p.point || p.point.x < 0) { hoverRow = null; return; }
      hoverRow = byTime.get(p.time) ?? null;
    });

    host.addEventListener('wheel', onWheel, { passive: false });
    return () => { host.removeEventListener('wheel', onWheel); chart.remove(); chart = null; };
  });

  // close the toolbar dropdowns on any outside click
  function onWindowClick(e) { if (!e.target.closest?.('.pc-tool')) openMenu = null; }
  onMount(() => { window.addEventListener('click', onWindowClick); return () => window.removeEventListener('click', onWindowClick); });

  // re-skin chrome (axes, grid, crosshair) when the theme flips
  $effect(() => {
    if (!chart) return;
    chart.applyOptions(themeOptions(PAL));
  });

  // Rebuild series whenever the window, mode, benchmarks, or theme changes.
  $effect(() => {
    if (!chart) return;
    const v = view, m = mode, base = baseRow;
    const cmp = benchmarks, bmData = bmHist;

    for (const h of handles) chart.removeSeries(h);
    handles = [];
    byTime = new Map(v.map((r) => [r.t, r]));

    if (cmp.length) {
      // ── COMPARE: rebased % via the library's Percentage scale (same as the
      // stock view's compare). Portfolio is fed its growth index (1+TWR) so the
      // scale rebases it to honest window TWR%; benchmarks fed raw closes →
      // price %. Everything rebases to the window start. ──
      chart.priceScale('right').applyOptions({ mode: PriceScaleMode.Percentage });
      chart.applyOptions({ localization: { priceFormatter: undefined } });

      const lo = v[0]?.t, hi = v[v.length - 1]?.t;
      const you = chart.addSeries(AreaSeries, { lineColor: BRAND, lineWidth: 2,
        topColor: hexA(BRAND, 0.22), bottomColor: hexA(BRAND, 0),
        priceLineVisible: false, lastValueVisible: false });
      mainData = v.filter((r) => r.pret != null).map((r) => ({ time: r.t, value: 1 + r.pret }));
      // fall back to raw value if TWR isn't available, so the line never vanishes
      you.setData(mainData.length >= 2 ? mainData : (mainData = v.map((r) => ({ time: r.t, value: r.pv }))));
      handles.push(you);

      for (const b of cmp) {
        const hist = (bmData[b.sym] ?? []).filter((p) => (!lo || p.t >= lo) && (!hi || p.t <= hi));
        if (hist.length < 2) continue;
        const s = chart.addSeries(LineSeries, {
          color: b.color, lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
        });
        s.setData(hist.map((p) => ({ time: p.t, value: p.c })));
        handles.push(s);
      }
    } else {
      // ── PORTFOLIO ONLY: $ value or TWR %, normal scale ──
      chart.priceScale('right').applyOptions({ mode: PriceScaleMode.Normal });
      chart.applyOptions({
        localization: {
          priceFormatter: m === 'value'
            ? (x) => '$' + x.toLocaleString('en-US', { maximumFractionDigits: 0 })
            : (x) => (x >= 0 ? '+' : '') + x.toFixed(0) + '%',
        },
      });

      if (m === 'value') {
        const main = chart.addSeries(AreaSeries, {
          lineColor: BRAND, lineWidth: 2,
          topColor: hexA(BRAND, 0.26), bottomColor: hexA(BRAND, 0),
          priceLineVisible: false, lastValueVisible: false,
        });
        mainData = v.map((r) => ({ time: r.t, value: r.pv }));
        main.setData(mainData);
        handles.push(main);
      } else {
        const you = chart.addSeries(LineSeries, {
          color: BRAND, lineWidth: 2, priceLineVisible: false, lastValueVisible: false,
        });
        mainData = v.filter((r) => r.pret != null).map((r) => ({ time: r.t, value: twRet(r, base, 'pret') }));
        you.setData(mainData);
        handles.push(you);
        handles[0].createPriceLine({
          price: 0, color: PAL.GRID, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false,
        });
      }
    }

    chart.timeScale().fitContent();
  });

  // ── touch scrub: HOLD (220ms) then DRAG moves the crosshair ──
  // Manual pointer implementation (deterministic, unlike the library's
  // tracking mode): hold engages, drag scrubs via setCrosshairPosition, lift
  // clears. Quick swipes cancel the hold so page scrolling stays natural.
  // Desktop mouse hover is untouched — the library handles it natively.
  const HOLD_MS = 1, HOLD_SLOP = 8;
  let holdTimer = null, scrubbing = false, downAt = null;

  function scrubAt(clientX) {
    if (!chart || !handles[0] || !mainData.length) return;
    const r = host.getBoundingClientRect();
    const x = Math.min(Math.max(clientX - r.left, 0), r.width);
    const lg = chart.timeScale().coordinateToLogical(x);
    if (lg == null) return;
    const pt = mainData[Math.min(mainData.length - 1, Math.max(0, Math.round(lg)))];
    if (!pt) return;
    chart.setCrosshairPosition(pt.value, pt.time, handles[0]);
    hoverRow = byTime.get(pt.time) ?? null;
  }
  function endScrub() {
    if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
    downAt = null;
    if (scrubbing) {
      scrubbing = false;
      chart?.clearCrosshairPosition();
      hoverRow = null;
    }
  }
  function onPtrDown(e) {
    if (e.pointerType !== 'touch') return;
    downAt = { x: e.clientX, y: e.clientY };
    holdTimer = setTimeout(() => { holdTimer = null; scrubbing = true; scrubAt(downAt.x); }, HOLD_MS);
  }
  function onPtrMove(e) {
    if (e.pointerType !== 'touch') return;
    if (scrubbing) { scrubAt(e.clientX); return; }
    // moved before the hold landed → it's a scroll, not a scrub
    if (downAt && Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > HOLD_SLOP) endScrub();
  }
  function onPtrEnd(e) { if (e.pointerType === 'touch') endScrub(); }
</script>

<!-- one chart widget; the window readout rides the toolbar (the persistent
     portfolio strip above the stage carries value + today's move) -->
<div class="pcg">
  <section class="pc-w pc-chart-w">
    {#if empty}
      <div class="pc-empty">
        <div class="pc-empty-t">No activity yet</div>
        <div class="pc-empty-s">Log a deposit or your first trade to start the curve.</div>
      </div>
    {/if}
    <!-- toolbar mirrors the stock chart's gf-bar so both views line up -->
    <div class="pc-bar" class:pc-hide={empty}>
      <div class="pc-tool">
        <button class="pc-btn" class:active={openMenu === 'compare' || comparing} onclick={() => toggleMenu('compare')}>
          <span class="pc-ic" aria-hidden="true">⇄</span>Compare{#if comparing}<span class="pc-count">{benchmarks.length}</span>{/if}<span class="pc-cv" aria-hidden="true">▾</span>
        </button>
        {#if openMenu === 'compare'}
          <div class="pc-menu pc-menu-cmp">
            <input class="pc-cmp-input" type="text" placeholder="Search any stock or ETF…"
              bind:value={bmQ}
              autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
            {#if bmQ.trim()}
              {#if bmLoading}
                <div class="pc-cmp-note">searching…</div>
              {:else if bmResults.length === 0}
                <div class="pc-cmp-note">no matches</div>
              {:else}
                {#each bmResults as r (r.symbol)}
                  <button class="pc-item" class:sel={benched((r.symbol || '').toUpperCase())}
                    onclick={() => toggleBenchmark(r.symbol, r.name)}>
                    <span class="pc-check">{benched((r.symbol || '').toUpperCase()) ? '✓' : ''}</span>
                    <span class="pc-cmp-name">{r.name}</span><span class="pc-sym">{r.symbol}</span>
                  </button>
                {/each}
              {/if}
            {:else}
              {#each QUICK_BMS as b (b.sym)}
                <button class="pc-item" class:sel={benched(b.sym)} onclick={() => toggleBenchmark(b.sym, b.label)}>
                  <span class="pc-check">{benched(b.sym) ? '✓' : ''}</span>{b.label}<span class="pc-sym">{b.sym}</span>
                </button>
              {/each}
              {#each benchmarks.filter((b) => !QUICK_BMS.some((q) => q.sym === b.sym)) as b (b.sym)}
                <button class="pc-item sel" onclick={() => toggleBenchmark(b.sym)}>
                  <span class="pc-check">✓</span><span class="pc-cmp-name">{b.label}</span><span class="pc-sym">{b.sym}</span>
                </button>
              {/each}
            {/if}
          </div>
        {/if}
      </div>

      <!-- readout: at rest the window's TWR + gap to SPY; scrubbing swaps in the hovered day -->
      <div class="pc-read">
        {#if hoverRow && read}
          <span class="pc-read-k">{fmtDate(read.t)}</span>
          <span class="pc-read-v {(read.youPct ?? 0) >= 0 ? 'up' : 'down'}">{fmtPct(read.youPct)}</span>
          {#if !comparing && read.spyPct != null}
            {@const gap = read.youPct - read.spyPct}
            <span class="pc-read-s {gap >= 0 ? 'up' : 'down'}">{(gap >= 0 ? '+' : '') + gap.toFixed(1)}% SPY</span>
          {/if}
          <span class="pc-read-s pc-muted">{fmtUsd(read.pv)}</span>
        {:else if period}
          <span class="pc-read-v {(period.youPct ?? 0) >= 0 ? 'up' : 'down'}">{fmtPct(period.youPct)}</span>
          <span class="pc-read-k">{RANGE_LABELS[range] ?? ''}</span>
          {#if !comparing && period.vs != null}
            <span class="pc-read-s {period.vs >= 0 ? 'up' : 'down'}">{(period.vs >= 0 ? '+' : '') + period.vs.toFixed(1)}% SPY</span>
          {/if}
        {/if}
      </div>

      {#if !comparing}
        <div class="pc-toggle" role="group" aria-label="metric">
          <button class:on={mode === 'value'} onclick={() => (mode = 'value')}>Value</button>
          <button class:on={mode === 'return'} onclick={() => (mode = 'return')}>Return</button>
        </div>
      {/if}
    </div>

    <!-- active benchmarks — removable legend chips, dot = series colour -->
    {#if comparing}
      <div class="pc-cmps">
        <span class="pc-chip pc-chip-self"><span class="pc-dot" style="background:{BRAND}"></span>You</span>
        {#each benchmarks as b (b.sym)}
          <button class="pc-chip" onclick={() => toggleBenchmark(b.sym)} title="Remove {b.sym}">
            <span class="pc-dot" style="background:{b.color}"></span>{b.sym}<span class="pc-chip-x" aria-hidden="true">✕</span>
          </button>
        {/each}
      </div>
    {/if}

    <!-- svelte-ignore a11y_no_static_element_interactions -- touch-scrub surface;
         the readout it drives is mirrored in the header text -->
    <div class="pc-canvas" bind:this={host}
      onpointerdown={onPtrDown} onpointermove={onPtrMove}
      onpointerup={onPtrEnd} onpointercancel={onPtrEnd}></div>
    <div class="pc-ranges" class:pc-hide={empty} role="group" aria-label="range">
      {#each RANGES as r}
        <button class:on={range === r.k} onclick={() => { range = r.k; panBars = 0; }}>{r.k}</button>
      {/each}
    </div>
  </section>
</div>

<style>
  /* one chart widget that fills whatever height its host gives it (the desktop
     stage's --stage-h; the phone pins .pc-chart-w to a fixed box) */
  .pcg { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .pc-w { background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    box-sizing: border-box; }

  /* empty account: cover the bare axes, hide controls that have nothing to act on */
  .pc-hide { visibility: hidden; }
  .pc-empty { position: absolute; inset: 0; z-index: 5; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 4px; padding: 16px;
    background: var(--surface); border-radius: var(--r); text-align: center; }
  .pc-empty-t { font-family: var(--sans); font-size: var(--fs-title); font-weight: 600; color: var(--ink); }
  .pc-empty-s { font-family: var(--sans); font-size: var(--fs-body); font-weight: 500; color: var(--muted); }
  .pc-chart-w { position: relative; flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; gap: 10px;
    padding: 14px 16px; }
  .pc-muted { color: var(--muted); font-weight: 400; }

  /* toolbar — mirrors StockChart's .gf-bar so the two charts align pixel-for-pixel */
  .pc-bar { display: flex; align-items: center; gap: 8px; flex: 0 0 auto; }
  /* window readout — TWR % leads, range label + gap-to-SPY trail; swaps to the
     hovered day while scrubbing. Takes the toolbar's middle so nothing jumps. */
  .pc-read { flex: 1 1 auto; min-width: 0; display: flex; align-items: baseline; gap: 8px;
    padding-left: 6px; font-family: var(--num); font-variant-numeric: tabular-nums;
    white-space: nowrap; overflow: hidden; }
  .pc-read-v { font-size: 18px; font-weight: 600; line-height: 1; letter-spacing: -.01em; }
  .pc-read-k { font-family: var(--sans); font-size: var(--fs-body); font-weight: 500; color: var(--muted); }
  .pc-read-s { font-size: var(--fs-body); font-weight: 500; }
  .pc-tool { position: relative; }
  /* toolbar button = the system pill: text → outline on hover → ink while its menu is open */
  .pc-btn { display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
    font-family: var(--sans); font-size: var(--fs-body); font-weight: 600; color: var(--ink);
    padding: 5px 12px; background: transparent; border: var(--bw) solid transparent;
    border-radius: 999px; transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .pc-btn:hover { border-color: var(--ink); }
  .pc-btn.active { background: var(--ink); border-color: var(--ink); color: var(--paper); }
  .pc-ic { font-size: 13px; opacity: .7; }
  svg.pc-ic { width: 14px; height: 14px; }
  .pc-cv { font-size: 9px; opacity: .6; margin-left: 1px; }
  .pc-menu { position: absolute; top: calc(100% + 5px); left: 0; z-index: 20; min-width: 150px;
    display: flex; flex-direction: column; padding: 5px; gap: 1px;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r); box-shadow: var(--sh); }
  .pc-item { display: flex; align-items: center; gap: 8px; width: 100%; cursor: pointer; text-align: left;
    font-family: var(--sans); font-size: 13px; font-weight: 500; color: var(--ink);
    padding: 7px 9px; border: 0; background: transparent; border-radius: 6px; }
  .pc-item:hover { background: var(--hover); }
  .pc-item.sel { font-weight: 600; }
  .pc-check { flex: 0 0 14px; font-size: 12px; color: var(--brand); }
  .pc-sym { margin-left: auto; font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }

  /* benchmark compare menu: search box + results / quick picks */
  .pc-menu-cmp { min-width: 230px; }
  .pc-cmp-input { box-sizing: border-box; width: 100%; margin-bottom: 4px; padding: 7px 9px;
    border: var(--bw) solid var(--hairline); border-radius: 6px; outline: none; background: transparent;
    font-family: var(--sans); font-size: 13px; font-weight: 500; color: var(--ink); }
  .pc-cmp-input:focus { border-color: var(--ink); }
  .pc-cmp-input::placeholder { color: var(--muted); }
  .pc-cmp-name { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pc-cmp-note { padding: 7px 9px; font-size: var(--fs-body); color: var(--muted); }
  .pc-count { font-family: var(--num); font-size: var(--fs-meta); font-weight: 600; line-height: 1;
    padding: 2px 6px; border-radius: 999px; background: var(--paper); color: var(--ink); border: 1px solid currentColor; }
  /* iOS focus-zoom guard for the in-menu search */
  @media (max-width: 700px) { .pc-cmp-input { font-size: 16px; } }

  /* active-benchmark chips under the toolbar */
  .pc-cmps { flex: 0 0 auto; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
  .pc-chip { display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
    font-family: var(--num); font-size: var(--fs-meta); font-weight: 600; color: var(--ink);
    padding: 3px 9px; background: transparent; border: var(--bw) solid var(--hairline); border-radius: 999px; }
  .pc-chip:hover { border-color: var(--ink); }
  .pc-chip-self { cursor: default; color: var(--muted); }
  .pc-dot { width: 8px; height: 8px; border-radius: 50%; border: 1px solid var(--ink); flex: 0 0 auto; }
  .pc-chip-x { font-size: 9px; opacity: .6; }

  /* metric toggle — system pills (text → outline hover → solid ink when on) */
  .pc-toggle { display: inline-flex; flex: 0 0 auto; gap: 2px; margin-left: auto; }
  .pc-toggle button { font-family: var(--sans); font-size: var(--fs-body); font-weight: 600; cursor: pointer;
    padding: 5px 12px; background: transparent; color: var(--muted);
    border: var(--bw) solid transparent; border-radius: 999px;
    transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .pc-toggle button:hover { color: var(--ink); border-color: var(--ink); }
  .pc-toggle button.on { background: var(--ink); color: var(--paper); border-color: var(--ink); }

  /* pan-y: vertical swipes keep scrolling the page; horizontal drags and the
     long-press scrub belong to the chart */
  .pc-canvas { flex: 1; min-height: 0; touch-action: pan-y; }

  /* range tabs — identical states to StockChart's .gf-range. No rule above them; the gap separates. */
  .pc-ranges { display: flex; align-items: center; gap: 2px; padding-top: 4px;
    /* 11 pills won't fit a phone — scroll the row sideways, no scrollbar */
    overflow-x: auto; scrollbar-width: none; -webkit-overflow-scrolling: touch; }
  .pc-ranges::-webkit-scrollbar { display: none; }
  .pc-ranges button { flex: 0 0 auto; }
  .pc-ranges button { font-family: var(--num); font-size: 11.5px; font-weight: 600; cursor: pointer; color: var(--muted);
    font-variant-numeric: tabular-nums;
    padding: 4px 11px; background: transparent; border: var(--bw) solid transparent; border-radius: 999px;
    transition: border-color .12s ease, background .12s ease, color .12s ease; }
  .pc-ranges button:hover { color: var(--ink); border-color: var(--ink); }
  .pc-ranges button.on { color: var(--paper); background: var(--ink); border-color: var(--ink); }

  .up { color: var(--gain); }
  .down { color: var(--loss); }

  /* phone: the readout drops under the toolbar on its own line so nothing clips */
  @media (max-width: 700px) {
    .pc-bar { flex-wrap: wrap; row-gap: 8px; }
    .pc-read { flex-basis: 100%; order: 1; padding-left: 2px; }
    .pc-ranges button { padding-inline: 9px; }
  }
</style>
