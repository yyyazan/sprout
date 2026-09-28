<script>
  // Drivers: which positions made the chart's move. The chart says what
  // happened; this says why. Follows the chart's window (range, pan,
  // drag-measure) by diffing the per-ticker cumulative $ P&L the dashboard
  // payload already carries (api/serialize._drivers), so no extra request.
  // The rows sum to the chart's drag-measure $ (net of deposits); a ticker's
  // contribution is realized + unrealized, closed positions included.
  //
  // variant 'tile' = the desktop stage's title card (headline left, bars right)
  // variant 'list' = the phone home section under the chart (header + rows)
  import TickerBadge from './TickerBadge.svelte';
  import { RANGE_LABELS } from '$lib/chartKit.svelte.js';
  import { holdings, openSearchResult } from '$lib/stores.js';

  let { drivers = null, win = null, variant = 'tile' } = $props();

  const UP = 3, DOWN = 2, SLOTS = UP + DOWN;   // rows shown; a short side lends its slots
  const MIN = 0.5;                            // under 50¢ isn't a driver

  // date string → row index on the drivers calendar (same dates as the equity curve)
  const index = $derived(new Map((drivers?.x ?? []).map((t, i) => [t, i])));

  // last row on or before an ISO date (the chart can hand us a weekend/holiday edge)
  function rowAt(t) {
    const x = drivers?.x ?? [];
    if (!x.length || !t) return -1;
    const hit = index.get(t);
    if (hit != null) return hit;
    let lo = 0, hi = x.length - 1, ans = -1;
    while (lo <= hi) { const m = (lo + hi) >> 1; if (x[m] <= t) { ans = m; lo = m + 1; } else hi = m - 1; }
    return ans;
  }

  const at = (arr, i) => (i < 0 ? 0 : arr[i] ?? 0);

  // every ticker's $ contribution over the window, biggest gain first
  const contribs = $derived.by(() => {
    const series = drivers?.series ?? {};
    if (!win) return [];
    const i0 = rowAt(win.from), i1 = rowAt(win.to);
    if (i1 < 0) return [];
    return Object.entries(series)
      .map(([t, s]) => ({ t, c: at(s, i1) - at(s, i0) }))
      .filter((r) => Math.abs(r.c) >= MIN)
      .sort((a, b) => b.c - a.c);
  });

  const total = $derived(contribs.reduce((a, r) => a + r.c, 0));
  const gains = $derived(contribs.filter((r) => r.c > 0));
  const losses = $derived(contribs.filter((r) => r.c < 0).reverse());   // worst first

  // top gains then worst losses; a side with fewer than its share lends the rest
  const rows = $derived.by(() => {
    const nUp = Math.min(gains.length, Math.max(UP, SLOTS - losses.length));
    const nDown = Math.min(losses.length, SLOTS - nUp);
    return [...gains.slice(0, nUp), ...losses.slice(0, nDown).reverse()];
  });
  const peak = $derived(Math.max(1e-9, ...rows.map((r) => Math.abs(r.c))));

  // "MU and SNDK made 71% of the gains": the two that did most of the move's own direction
  const say = $derived.by(() => {
    if (!contribs.length) return 'Nothing moved in this window';
    const lead = total >= 0 ? gains : losses;
    const word = total >= 0 ? 'gains' : 'losses';
    if (!lead.length) return '';
    const top = lead.slice(0, 2);
    const names = top.map((r) => r.t).join(' and ');
    if (lead.length <= top.length) return `${names} made all of the ${word}`;
    const gross = lead.reduce((a, r) => a + Math.abs(r.c), 0);
    const share = Math.round((top.reduce((a, r) => a + Math.abs(r.c), 0) / gross) * 100);
    return `${names} made ${share}% of the ${word}`;
  });

  // window label: the range's words, or the dates when panned/measured
  const short = (iso, year) => {
    const d = new Date(iso + 'T00:00:00');
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', ...(year ? { year: 'numeric' } : {}) });
  };
  const label = $derived.by(() => {
    if (!win) return '';
    if (!win.custom) return RANGE_LABELS[win.range] ?? '';
    const yr = win.from.slice(0, 4) !== win.to.slice(0, 4);
    return `${short(win.from, yr)} → ${short(win.to, yr)}`;
  });

  const money = (v) => (v >= 0 ? '+$' : '−$') + Math.round(Math.abs(v)).toLocaleString('en-US');
  const tone = (v) => (v >= 0 ? 'up' : 'down');

  function open(t) {
    const c = ($holdings ?? []).find((h) => h.ticker === t);
    openSearchResult({ symbol: t, name: c?.company_name ?? t });
  }

  const empty = $derived(!drivers?.x?.length || !Object.keys(drivers?.series ?? {}).length);
</script>

{#snippet list()}
  <div class="dr-rows">
    {#each rows as r (r.t)}
      <button class="dr-row" onclick={() => open(r.t)}
        aria-label="{r.t} {r.c >= 0 ? 'added' : 'took'} {money(r.c)} {label}">
        <span class="dr-tkr"><TickerBadge sym={r.t} /></span>
        <span class="dr-track"><span class="dr-bar {tone(r.c)}" style="width:{(Math.abs(r.c) / peak) * 100}%"></span></span>
        <span class="dr-v {tone(r.c)}">{money(r.c)}</span>
      </button>
    {/each}
  </div>
{/snippet}

{#if variant === 'tile'}
  <section class="glass-card dr-tile">
    <div class="dr-lead">
      <div>
        <div class="kpi-label">Drivers</div>
        {#if empty}
          <div class="kpi-value">—</div>
        {:else}
          <div class="kpi-value {contribs.length ? (total >= 0 ? 'kpi-value-up' : 'kpi-value-down') : ''}">{contribs.length ? money(total) : '$0'}</div>
          <div class="bal-day"><span class="bal-day-when">{label}</span></div>
        {/if}
      </div>
      <p class="dr-say">{empty ? 'Log a trade to see what drives your returns' : say}</p>
    </div>
    {#if !empty && rows.length}{@render list()}{/if}
  </section>
{:else if !empty}
  <section class="dr-section">
    <div class="dr-head">
      <span class="dr-title">Drivers, {label}</span>
      {#if contribs.length}<span class="dr-total {tone(total)}">{money(total)}</span>{/if}
    </div>
    {#if rows.length}
      {@render list()}
      <p class="dr-say dr-say-list">{say}</p>
    {:else}
      <p class="dr-say dr-say-list">{say}</p>
    {/if}
  </section>
{/if}

<style>
  /* ── desktop tile: the stage's title card (--title-h), headline | bars ── */
  .dr-tile { --card-pad: 14px 16px; min-height: var(--title-h, 152px); box-sizing: border-box;
    display: grid; grid-template-columns: minmax(170px, 1fr) minmax(0, 1.5fr); gap: 24px; }
  .dr-lead { display: flex; flex-direction: column; justify-content: space-between; gap: 10px; min-width: 0; }
  .dr-say { margin: 0; font-size: var(--fs-body); font-weight: 500; color: var(--muted); line-height: 1.35; }

  /* rows: badge · bar · amount. Bars grow from the left, length ∝ |$|, tinted
     by sign, largest gain on top and largest loss at the bottom. */
  .dr-rows { display: flex; flex-direction: column; justify-content: center; gap: 2px; min-width: 0; }
  .dr-row { display: grid; grid-template-columns: 58px minmax(0, 1fr) 68px; align-items: center; gap: 10px;
    width: 100%; min-height: 23px; padding: 1px 6px; box-sizing: border-box;
    border: 0; border-radius: var(--r); background: transparent; color: var(--ink);
    font: inherit; text-align: left; cursor: pointer; }
  .dr-row:hover { background: var(--hover); }
  .dr-tkr { display: flex; }
  .dr-track { position: relative; height: 8px; }
  .dr-bar { position: absolute; left: 0; top: 0; bottom: 0; min-width: 2px; border-radius: 999px;
    transition: width .2s ease; }
  .dr-bar.up { background: var(--gain); }
  .dr-bar.down { background: var(--loss); }
  .dr-v { font-family: var(--num); font-size: var(--fs-body); font-weight: 500; text-align: right;
    font-variant-numeric: tabular-nums; white-space: nowrap; }
  .up { color: var(--gain-ink); }
  .down { color: var(--loss-ink); }
  @media (prefers-reduced-motion: reduce) { .dr-bar { transition: none; } }

  /* very narrow: headline over rows */
  @media (max-width: 520px) { .dr-tile { grid-template-columns: 1fr; } }

  /* ── phone: a home-pane section in the month-glance grammar ── */
  .dr-section { display: flex; flex-direction: column; }
  .dr-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; padding: 4px 0 6px; }
  .dr-title { font-size: var(--fs-title); font-weight: 600; color: var(--ink); }
  .dr-total { font-family: var(--num); font-size: var(--fs-title); font-weight: 600; font-variant-numeric: tabular-nums; }
  .dr-section .dr-rows { gap: 0; }
  .dr-section .dr-row { min-height: 44px; padding: 0;
    border-bottom: var(--bw) solid var(--hairline); border-radius: 0; }
  .dr-section .dr-row:active { background: var(--hover); }
  .dr-section .dr-row:hover { background: transparent; }
  .dr-say-list { padding-top: 8px; }
</style>
