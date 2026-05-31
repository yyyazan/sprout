<script>
  import { formatValue } from '$lib/format.js';
  let { label, current, target, size = 'medium' } = $props();
  let pct = $derived(target ? Math.min(100, (current / target) * 100) : 0);
</script>

<div class="glass-card progress-card widget-{size}">
  <div class="kpi-label">{label}</div>
  <div class="progress-value">{formatValue(current, 'money')} / {formatValue(target, 'money')}</div>
  <div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div>
  <div class="progress-pct">{pct.toFixed(0)}%</div>
</div>
