<script>
  import { formatValue } from '$lib/format.js';
  // Portfolio Value snapshot: the Total, broken down to its invested portion
  // (Equities at live spot). Cash — the remainder — has its own goal card, so it
  // isn't repeated here. Leaves the chart hero to own the performance story.
  let { total, equities, size = 'mini' } = $props();
</script>

<div class="glass-card kpi-card widget-{size} bal">
  <div class="bal-head">
    <div class="kpi-label">Portfolio Value</div>
    <div class="kpi-value bal-total">{formatValue(total, 'money')}</div>
  </div>
  <div class="bal-rows">
    <div class="bal-row"><span class="bal-k">Equities</span><span class="bal-v">{formatValue(equities, 'money')}</span></div>
  </div>
</div>

<!-- .bal-* styles are global (app.css) and shared with PnlCard -->

