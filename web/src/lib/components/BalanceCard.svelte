<script>
  import { formatValue } from '$lib/format.js';
  // Portfolio Value snapshot: the Total + today's change, broken down to its
  // invested portion (Equities at live spot). Cash — the remainder — has its own
  // goal card, so it isn't repeated here.
  // dayGain/dayPct = today's aggregate intraday change (computed by the parent
  // from live holdings; see portfolioDayMove in stores.js).
  let { total, equities, size = 'mini', dayGain = null, dayPct = null } = $props();
  const tone = dayGain == null ? '' : dayGain >= 0 ? 'up' : 'down';
  const dGain = (v) => (v == null ? '—' : (v >= 0 ? '+$' : '−$') + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
  const dPct = (v) => (v == null ? '' : (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(2) + '%');
</script>

<div class="glass-card kpi-card widget-{size} bal">
  <div class="bal-head">
    <div class="kpi-label">Portfolio Value</div>
    <div class="kpi-value bal-total">{formatValue(total, 'money')}</div>
    <div class="bal-day {tone}">
      <span class="bal-day-amt">{dGain(dayGain)}</span>
      <span class="pct-pill {tone}">{dPct(dayPct)}</span>
      <span class="bal-day-when">today</span>
    </div>
  </div>
  <div class="bal-rows">
    <div class="bal-row"><span class="bal-k">Equities</span><span class="bal-v">{formatValue(equities, 'money')}</span></div>
  </div>
</div>

<!-- .bal-* styles are global (app.css) and shared with PnlCard -->

