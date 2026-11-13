<script>
  // Plan projection plot. Plain SVG rather than lightweight-charts: it's a future
  // path with a filled range and a stacked "put in" area, none of which LWC draws,
  // and SVG reads the theme tokens directly so it flips with the theme for free.
  //   points   = project() output: { date, putIn, mid, lo, hi }
  //   baseline = expected path at the user's actual rate (dashed), or null
  //   hover    = index of the hovered month, null at rest (bindable)
  //   marks    = income changes [{ i, label }]: a dashed rule at that month, the
  //              new take-home over it
  //   showHysa = draw the HYSA balance (points[].hysa) as its own line
  import ChartTip from './chart/ChartTip.svelte';
  import { usd0, usdShort, niceTicks, monthLabel } from '$lib/plan.js';

  let { points, baseline = null, marks = [], showHysa = false, hover = $bindable(null) } = $props();

  let w = $state(0), h = $state(0);
  // top room for the income-change labels when there are any
  const PAD = $derived({ t: marks.length ? 22 : 8, r: 52, b: 22, l: 2 });
  const iw = $derived(Math.max(0, w - PAD.l - PAD.r));
  const ih = $derived(Math.max(0, h - PAD.t - PAD.b));

  const top = $derived(Math.max(...points.map((p) => p.hi), ...(baseline ?? [0]), 1));
  const ticks = $derived(niceTicks(top));
  const yMax = $derived(ticks[ticks.length - 1] || top);
  const n = $derived(points.length - 1);

  const x = (i) => PAD.l + (n ? (i / n) * iw : 0);
  const y = (v) => PAD.t + ih - (v / yMax) * ih;

  const line = (vals) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
  const area = (vals) => `${line(vals)}L${x(n).toFixed(1)},${y(0).toFixed(1)}L${x(0).toFixed(1)},${y(0).toFixed(1)}Z`;

  const midD = $derived(line(points.map((p) => p.mid)));
  const midArea = $derived(area(points.map((p) => p.mid)));
  const putArea = $derived(area(points.map((p) => p.putIn)));
  const putLine = $derived(line(points.map((p) => p.putIn)));
  const bandD = $derived(
    line(points.map((p) => p.hi)) +
      points.slice().reverse().map((p, k) => `L${x(n - k).toFixed(1)},${y(p.lo).toFixed(1)}`).join('') + 'Z'
  );
  const baseD = $derived(baseline ? line(baseline) : null);
  const hysaD = $derived(showHysa ? line(points.map((p) => p.hysa)) : null);

  // a label each January, thinned so they never crowd (~70px apart)
  const years = $derived.by(() => {
    // a centred label this close to the left edge gets cut off, so skip it
    const jans = points.map((p, i) => ({ i, d: p.date })).filter((p) => p.d.getMonth() === 0 && x(p.i) >= PAD.l + 16);
    const every = Math.max(1, Math.ceil(jans.length / Math.max(1, Math.floor(iw / 70))));
    return jans.filter((_, k) => k % every === 0);
  });

  function move(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const i = Math.round(((e.clientX - r.left - PAD.l) / iw) * n);
    hover = Math.max(0, Math.min(n, i));
  }

  const hp = $derived(hover == null ? null : points[hover]);
</script>

<div class="plc" bind:clientWidth={w} bind:clientHeight={h}>
  {#if w && h}
    <svg width={w} height={h} role="img" aria-label="Projected balance"
      onpointermove={move} onpointerdown={move} onpointerleave={() => (hover = null)}>
      <defs>
        <linearGradient id="plc-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" style="stop-color: var(--brand); stop-opacity: .18" />
          <stop offset="1" style="stop-color: var(--brand); stop-opacity: 0" />
        </linearGradient>
      </defs>

      {#each ticks as t}
        <line class="grid" x1={PAD.l} x2={PAD.l + iw} y1={y(t)} y2={y(t)} />
        <text class="ax" x={w - 4} y={y(t)} text-anchor="end" dominant-baseline="middle">{usdShort(t)}</text>
      {/each}
      {#each years as yr}
        <text class="ax" x={x(yr.i)} y={h - 4} text-anchor="middle">{yr.d.getFullYear()}</text>
      {/each}

      <path class="band" d={bandD} />
      <path d={midArea} fill="url(#plc-fill)" />
      <path class="put" d={putArea} />
      <path class="put-line" d={putLine} />
      {#if baseD}<path class="base" d={baseD} />{/if}
      {#if hysaD}<path class="hysa" d={hysaD} />{/if}
      <path class="mid" d={midD} />

      {#each marks as k (k.i)}
        <line class="mark" x1={x(k.i)} x2={x(k.i)} y1={PAD.t - 4} y2={PAD.t + ih} />
        <text class="ax mark-t" x={x(k.i)} y={PAD.t - 8}
          text-anchor={x(k.i) > PAD.l + iw - 30 ? 'end' : 'middle'}>{k.label}</text>
      {/each}

      {#if hp}
        <line class="cross" x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={PAD.t + ih} />
        <circle class="dot" cx={x(hover)} cy={y(hp.mid)} r="3.5" />
      {/if}
    </svg>
    {#if hp}
      <ChartTip x={x(hover)} y={y(hp.mid)} value={usd0(hp.mid)} sub={monthLabel(hp.date)} />
    {/if}
  {/if}
</div>

<style>
  .plc { position: absolute; inset: 0; }
  svg { display: block; touch-action: pan-y; cursor: crosshair; }
  .grid { stroke: var(--hairline); stroke-width: 1; }
  .ax { fill: var(--muted); font-family: var(--num); font-size: 11px; font-variant-numeric: tabular-nums; }
  .band { fill: color-mix(in srgb, var(--brand) 12%, transparent); stroke: none; }
  .put { fill: color-mix(in srgb, var(--ink) 9%, transparent); }
  .put-line { fill: none; stroke: var(--muted); stroke-width: 1; }
  .base { fill: none; stroke: var(--ink); stroke-width: 1; stroke-dasharray: 3 4; opacity: .7; }
  .hysa { fill: none; stroke: var(--blue); stroke-width: 1.5; stroke-linejoin: round; }
  .mark { stroke: var(--muted); stroke-width: 1; stroke-dasharray: 2 3; }
  .mark-t { fill: var(--ink); }
  .mid { fill: none; stroke: var(--brand); stroke-width: 2; stroke-linejoin: round; }
  .cross { stroke: var(--ink); stroke-width: 1; }
  .dot { fill: var(--brand); stroke: var(--paper); stroke-width: 1.5; }
</style>
