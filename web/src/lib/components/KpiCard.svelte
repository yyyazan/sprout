<script>
  import { formatValue, valueClass } from '$lib/format.js';
  let { label, value, kind = 'money', subtitle = null, size = 'small' } = $props();
</script>

<div class="glass-card kpi-card widget-{size}">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value {valueClass(value, kind)}">{formatValue(value, kind)}</div>
  {#if subtitle}<div class="kpi-subtitle">{subtitle}</div>{/if}
</div>
