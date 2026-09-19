<script>
  import { formatValue } from '$lib/format.js';
  // Portfolio Value snapshot: the Total + today's change, broken down to its
  // invested portion (Equities at live spot) and the all-time time-weighted
  // return vs SPY. Cash — the remainder — has its own goal card, so it isn't
  // repeated here.
  // dayGain/dayPct = today's aggregate intraday change (computed by the parent
  // from live holdings; see portfolioDayMove in stores.js).
  // ret/vsSpy = all-time TWR % and the gap to SPY in pp (allTimeReturn in stores.js).
  let { total, equities, size = 'mini', dayGain = null, dayPct = null, ret = null, vsSpy = null } = $props();
  // An account holding nothing has no move to report: a green +$0.00 reads as a
  // win, and "vs SPY" would claim an empty portfolio is beating the market when
  // it's really just SPY's own drift over the window.
  const flat = $derived(!total && !equities);
  // $derived, not a plain const: dayGain updates live from the momentum poll.
  const tone = $derived(flat || dayGain == null ? '' : dayGain >= 0 ? 'up' : 'down');
  const dGain = (v) => (v == null ? '—' : (v >= 0 ? '+$' : '−$') + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
  const dPct = (v) => (v == null ? '' : (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(2) + '%');
  const sPct = (v, d = 1) => (v == null ? '—' : (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d));
</script>

<div class="glass-card kpi-card widget-{size} bal">
  <div class="bal-head">
    <div class="kpi-label">Portfolio value</div>
    <div class="kpi-value">{formatValue(total, 'money')}</div>
    <div class="bal-day {tone}">
      {#if flat}
        <span class="bal-day-amt">—</span>
      {:else}
        <span class="bal-day-amt">{dGain(dayGain)}</span>
        <span class="pct-pill {tone}">{dPct(dayPct)}</span>
      {/if}
    </div>
  </div>
  <div class="bal-rows">
    <div class="bal-row"><span class="bal-k">Equities</span><span class="bal-v">{formatValue(equities, 'money')}</span></div>
    <div class="bal-row">
      <span class="bal-k">All-time</span>
      <span class="bal-v {flat || ret == null ? '' : ret >= 0 ? 'up' : 'down'}">{flat ? '—' : sPct(ret) + '%'}</span>
    </div>
    <div class="bal-row">
      <span class="bal-k">vs SPY</span>
      <span class="bal-v {flat || vsSpy == null ? '' : vsSpy >= 0 ? 'up' : 'down'}">{flat ? '—' : sPct(vsSpy) + '%'}</span>
    </div>
  </div>
</div>

<!-- .bal-* styles are global (app.css) and shared with PnlCard -->
<style>
  .bal-v.up { color: var(--gain); }
  .bal-v.down { color: var(--loss); }
</style>
