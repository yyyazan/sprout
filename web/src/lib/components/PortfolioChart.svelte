<script>
  // First-class interactive portfolio chart. The header reads PERFORMANCE over the
  // selected range — a deposit-stripped $ gain + the window's time-weighted return,
  // and the gap to SPY — so the range buttons (1W…ALL) drive the headline, not just
  // the zoom. Scrubbing the crosshair swaps it for the hovered day's value and its
  // return-to-date. A Value|Return toggle flips the plotted line between $ and
  // time-weighted %; adding benchmarks rebases everything to the window start.
  import { onMount } from 'svelte';
  import { createChart, AreaSeries, LineSeries, ColorType, CrosshairMode, LineStyle, PriceScaleMode } from 'lightweight-charts';
  import { theme } from '$lib/theme.js';
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
  let openMenu = $state(null);    // 'type' | 'compare' | null — toolbar dropdowns
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

  const RANGE_LABELS = { '1W': 'Past week', '1M': 'Past month', '3M': 'Past 3 months', '1Y': 'Past year', 'ALL': 'All-time' };

  // REST-state headline = performance over the visible window. The $ is deposit-
  // stripped (window value change minus net deposits in the window) so it reads as
  // earnings, not balance growth; the % is the window's time-weighted return, and
  // `vs` is the gap to SPY in percentage points.
  const lastRow = $derived(view.length ? view[view.length - 1] : null);
  const period = $derived.by(() => {
    if (!baseRow || !lastRow) return null;
    const deposits = baseRow.ni != null && lastRow.ni != null ? lastRow.ni - baseRow.ni : 0;
    const dollar = (lastRow.pv - baseRow.pv) - deposits;
    const youPct = twRet(lastRow, baseRow, 'pret');
    const spyPct = twRet(lastRow, baseRow, 'sret');
    return { dollar, youPct, spyPct, vs: youPct != null && spyPct != null ? youPct - spyPct : null };
  });

  // ── upcoming earnings (right header half) — own fetch, never blocks the chart ──
  let earnings = $state(null);   // null = loading · [] = none · [{ticker,date,past}]
  onMount(() => {
    api.earnings()
      .then((r) => { earnings = r?.items ?? []; })
      .catch(() => { earnings = []; });
  });
  const fmtEarn = (iso) => new Date(iso + 'T00:00:00')
    .toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  // "today" / "in Nd" for scheduled dates; past reports just say "reported"
  function earnWhen(e) {
    if (e.past) return 'reported';
    const days = Math.round((new Date(e.date + 'T00:00:00') - new Date().setHours(0, 0, 0, 0)) / 86400000);
    return days <= 0 ? 'today' : `in ${days}d`;
  }

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
  let mainData = [];        // the primary series' points — drives the touch scrub

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

  // Rebuild series whenever the window, mode, benchmarks, or theme changes.
  $effect(() => {
    if (!chart) return;
    const v = view, m = mode, base = baseRow, t = chartType;
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
      const you = t === 'line'
        ? chart.addSeries(LineSeries, { color: BRAND, lineWidth: 2, priceLineVisible: false, lastValueVisible: false })
        : chart.addSeries(AreaSeries, { lineColor: BRAND, lineWidth: 2,
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
        const main = t === 'line'
          ? chart.addSeries(LineSeries, { color: BRAND, lineWidth: 2, priceLineVisible: false, lastValueVisible: false })
          : chart.addSeries(AreaSeries, {
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

<!-- two widgets matching the stock view's grid language: header (split 2-up) + chart -->
<div class="pcg">
  <div class="pc-head-row">
  <section class="pc-w pc-head-w">
  <div class="pc-head">
    <div class="pc-read">
      {#if hoverRow && read}
        <!-- scrubbing a past point: that day's value + its return-to-date -->
        <div class="pc-label">{fmtDate(read.t)}</div>
        <div class="pc-value">{fmtUsd(read.pv)}</div>
        <div class="pc-delta">
          <span class="pc-muted">return {fmtPct(read.youPct)}{#if !comparing && read.spyPct != null} · SPY {fmtPct(read.spyPct)}{/if}</span>
        </div>
      {:else if period}
        <!-- at rest: performance over the visible range (deposit-stripped $ + TWR %) -->
        <div class="pc-label">{RANGE_LABELS[range] ?? 'Performance'}</div>
        <div class="pc-value {(period.dollar ?? 0) >= 0 ? 'up' : 'down'}">{fmtUsdSigned(period.dollar)}</div>
        <div class="pc-delta">
          <span class={(period.youPct ?? 0) >= 0 ? 'up' : 'down'}>{fmtPct(period.youPct)}</span>
          {#if !comparing && period.vs != null}
            <span class="pc-muted">vs SPY</span>
            <span class={period.vs >= 0 ? 'up' : 'down'}>{(period.vs >= 0 ? '+' : '') + period.vs.toFixed(1)}pp {period.vs >= 0 ? 'ahead' : 'behind'}</span>
          {/if}
        </div>
      {/if}
    </div>
  </div>
  </section>
  <!-- right half: next earnings dates across the holdings (6 max, 3×2 grid) -->
  <section class="pc-w pc-head-earn">
    <div class="pc-label">Upcoming earnings</div>
    {#if earnings === null}
      <div class="pe-note">loading…</div>
    {:else if earnings.length === 0}
      <div class="pe-note">no earnings dates</div>
    {:else}
      <div class="pe-grid">
        {#each earnings as e (e.ticker)}
          <div class="pe-cell" class:pe-past={e.past}>
            <span class="pe-tkr">{e.ticker}</span>
            <span class="pe-date">{fmtEarn(e.date)}</span>
            <span class="pe-when">{earnWhen(e)}</span>
          </div>
        {/each}
      </div>
    {/if}
  </section>
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
        <button class="pc-btn" class:active={openMenu === 'compare' || comparing} onclick={() => toggleMenu('compare')}>
          <span class="pc-ic" aria-hidden="true">⇄</span>Benchmark{#if comparing}<span class="pc-count">{benchmarks.length}</span>{/if}<span class="pc-cv" aria-hidden="true">▾</span>
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
  /* earnings half — same locked header height; 3×2 cells split by hairlines */
  .pc-head-earn { height: var(--title-h, 152px); display: flex; flex-direction: column;
    gap: 8px; padding: 12px 16px 14px; box-sizing: border-box; overflow: hidden; }
  .pe-note { font-family: var(--mono); font-size: 11px; color: var(--muted); }
  .pe-grid { flex: 1; min-height: 0; display: grid; grid-template-columns: repeat(3, 1fr);
    grid-template-rows: 1fr 1fr; column-gap: 14px; }
  .pe-cell { min-width: 0; display: flex; flex-direction: column; justify-content: center; gap: 1px;
    border-bottom: var(--bw) solid var(--hairline); }
  .pe-grid .pe-cell:nth-child(n + 4) { border-bottom: 0; }
  .pe-tkr { font-family: var(--mono); font-size: 11.5px; font-weight: 700; letter-spacing: .04em;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pe-date { font-family: var(--mono); font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums;
    white-space: nowrap; }
  .pe-when { font-family: var(--sans); font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .05em; color: var(--brand); white-space: nowrap; }
  .pe-past { opacity: .55; }
  .pe-past .pe-when { color: var(--muted); }
  .pc-chart-w { flex: 0 0 440px; min-height: 0; display: flex; flex-direction: column; gap: 10px;
    padding: 14px 16px; }
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
  .pc-item { display: flex; align-items: center; gap: 8px; width: 100%; cursor: pointer; text-align: left;
    font-family: var(--sans); font-size: 12.5px; font-weight: 600; color: var(--ink);
    padding: 7px 9px; border: 0; background: transparent; border-radius: 6px; }
  .pc-item:hover { background: var(--hover); }
  .pc-item.sel { font-weight: 700; }
  .pc-check { flex: 0 0 14px; font-size: 12px; color: var(--brand); }
  .pc-sym { margin-left: auto; font-family: var(--mono); font-size: 10px; color: var(--muted); }

  /* benchmark compare menu: search box + results / quick picks */
  .pc-menu-cmp { min-width: 230px; }
  .pc-cmp-input { box-sizing: border-box; width: 100%; margin-bottom: 4px; padding: 7px 9px;
    border: var(--bw) solid var(--hairline); border-radius: 6px; outline: none; background: transparent;
    font-family: var(--sans); font-size: 12.5px; font-weight: 600; color: var(--ink); }
  .pc-cmp-input:focus { border-color: var(--ink); }
  .pc-cmp-input::placeholder { color: var(--muted); font-weight: 500; }
  .pc-cmp-name { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pc-cmp-note { padding: 7px 9px; font-family: var(--mono); font-size: 11px; color: var(--muted); }
  .pc-count { font-family: var(--mono); font-size: 10px; font-weight: 700; line-height: 1;
    padding: 2px 6px; border-radius: 999px; background: var(--paper); color: var(--ink); border: 1px solid currentColor; }
  /* iOS focus-zoom guard for the in-menu search */
  @media (max-width: 700px) { .pc-cmp-input { font-size: 16px; } }

  /* active-benchmark chips under the toolbar */
  .pc-cmps { flex: 0 0 auto; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
  .pc-chip { display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
    font-family: var(--mono); font-size: 10.5px; font-weight: 700; color: var(--ink);
    padding: 3px 9px; background: transparent; border: var(--bw) solid var(--hairline); border-radius: 999px; }
  .pc-chip:hover { border-color: var(--ink); }
  .pc-chip-self { cursor: default; color: var(--muted); }
  .pc-dot { width: 8px; height: 8px; border-radius: 50%; border: 1px solid var(--ink); flex: 0 0 auto; }
  .pc-chip-x { font-size: 9px; opacity: .6; }

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
