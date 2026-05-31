<script>
  import { formatValue, valueClass } from '$lib/format.js';
  // `tone` paints the card a flat block: 'brand' (jade hero) / 'gain' / 'loss' / default white.
  // On a toned card the figure stays ink (no up/down colour — it would clash with the fill).
  let { label, value, kind = 'money', subtitle = null, size = 'small', tone = 'surface' } = $props();
  const FILL = { surface: 'var(--surface)', brand: 'var(--brand)', gain: 'var(--gain)', loss: 'var(--loss)' };
</script>

<div class="glass-card kpi-card widget-{size}" style="--fill:{FILL[tone] ?? 'var(--surface)'}">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value {tone === 'surface' ? valueClass(value, kind) : ''}">{formatValue(value, kind)}</div>
  {#if subtitle}<div class="kpi-subtitle">{subtitle}</div>{/if}
</div>
