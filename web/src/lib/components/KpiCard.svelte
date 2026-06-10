<script>
  import { formatValue, valueClass } from '$lib/format.js';
  // `tone` colours the FIGURE, not the card — flat fills read loud/childish next
  // to the rest of the system. 'brand' keeps the jade hero fill (used sparingly).
  let { label, value, kind = 'money', subtitle = null, size = 'small', tone = 'surface' } = $props();
  const fill = tone === 'brand' ? 'var(--brand)' : 'var(--surface)';
  const toneClass = tone === 'gain' ? 'up' : tone === 'loss' ? 'down' : '';
</script>

<div class="glass-card kpi-card widget-{size}" style="--fill:{fill}">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value {toneClass || (tone === 'surface' ? valueClass(value, kind) : '')}">{formatValue(value, kind)}</div>
  {#if subtitle}<div class="kpi-subtitle">{subtitle}</div>{/if}
</div>

<style>
  .kpi-value.up { color: var(--gain); }
  .kpi-value.down { color: var(--loss); }
</style>
