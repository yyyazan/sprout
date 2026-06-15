<script>
  // P&L snapshot mirroring BalanceCard: the Total (realized + unrealized) tinted
  // gain/loss on top, with the two components below in neutral ink so they read
  // as reference figures, not a second verdict. Shares the global .bal-* styles.
  let { total, realized, unrealized, size = 'mini' } = $props();
  const money = (v) =>
    v == null ? '—' : (v >= 0 ? '+$' : '−$') + Math.round(Math.abs(v)).toLocaleString('en-US');
</script>

<div class="glass-card kpi-card widget-{size}">
  <div class="bal-head">
    <div class="kpi-label">P&amp;L</div>
    <div class="kpi-value bal-total {(total ?? 0) >= 0 ? 'kpi-value-up' : 'kpi-value-down'}">{money(total)}</div>
  </div>
  <div class="bal-rows">
    <div class="bal-row"><span class="bal-k">Realized</span><span class="bal-v">{money(realized)}</span></div>
    <div class="bal-row"><span class="bal-k">Unrealized</span><span class="bal-v">{money(unrealized)}</span></div>
  </div>
</div>
