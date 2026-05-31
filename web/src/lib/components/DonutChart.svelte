<script>
  import { PALETTE } from '$lib/charts.js';

  // Allocation donut. Accepts {labels, values}. Presentation-only — callers
  // (AllocationPanel) render their own legend.
  let { labels, values } = $props();

  const R = 33.6;          // stroke centerline radius (viewBox 0..100)
  const SW = 16.8;         // stroke width -> 60% hole (inner/outer = 0.6)
  const C = 2 * Math.PI * R;

  let total = $derived(values.reduce((a, b) => a + (b > 0 ? b : 0), 0));

  // Cumulative arcs as dash segments, starting from 12 o'clock.
  let arcs = $derived.by(() => {
    let acc = 0;
    return values.map((v, i) => {
      const frac = total > 0 ? Math.max(v, 0) / total : 0;
      const seg = { len: frac * C, offset: -acc * C, color: PALETTE[i % PALETTE.length], label: labels[i] };
      acc += frac;
      return seg;
    });
  });
</script>

<svg class="donut" viewBox="0 0 100 100" role="img" aria-label="Allocation donut">
  <g transform="rotate(-90 50 50)">
    <circle cx="50" cy="50" r={R} fill="none" stroke="var(--border)" stroke-width={SW} opacity="0.4" />
    {#each arcs as a}
      <circle
        cx="50" cy="50" r={R} fill="none"
        stroke={a.color} stroke-width={SW}
        stroke-dasharray="{a.len} {C - a.len}"
        stroke-dashoffset={a.offset}
      >
        <title>{a.label}</title>
      </circle>
    {/each}
  </g>
</svg>
