<script>
  // P&L snapshot mirroring BalanceCard: the Total (realized + unrealized) tinted
  // gain/loss on top, with the two components below in neutral ink so they read
  // as reference figures, not a second verdict. Shares the global .bal-* styles.
  // The third row is what the funds held cost a year (expense ratio x value); it
  // fetches on its own because the ratios come from Yahoo's slow fund data, and it
  // is simply absent when nothing held has a published ratio.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let { total, realized, unrealized, size = 'mini' } = $props();

  let fees = $state(null);   // null = loading · { annual: null } = no costed funds
  onMount(() => {
    api.fees().then((r) => { fees = r; }).catch(() => { fees = { annual: null }; });
  });
  const yearly = (v) => '$' + (v < 10 ? v.toFixed(2) : Math.round(v).toLocaleString('en-US'));
  const money = (v) =>
    v == null ? '—' : (v >= 0 ? '+$' : '−$') + Math.round(Math.abs(v)).toLocaleString('en-US');

  // An account with nothing in it hasn't gained anything — tinting a flat $0
  // green would read as a (tiny) win rather than "no history yet".
  const flat = $derived(!total && !realized && !unrealized);
</script>

<div class="glass-card kpi-card widget-{size}">
  <div class="bal-head">
    <div class="kpi-label">Profit &amp; loss</div>
    {#if flat}
      <div class="kpi-value">—</div>
    {:else}
      <div class="kpi-value {(total ?? 0) >= 0 ? 'kpi-value-up' : 'kpi-value-down'}">{money(total)}</div>
    {/if}
  </div>
  <div class="bal-rows">
    <div class="bal-row"><span class="bal-k">Realized</span><span class="bal-v">{money(realized)}</span></div>
    <div class="bal-row"><span class="bal-k">Unrealized</span><span class="bal-v">{money(unrealized)}</span></div>
    {#if fees === null}
      <div class="bal-row" aria-hidden="true"><span class="bal-k">Fees a year</span><span class="bal-v"><span class="skel skel-t" style="width:2.6em"></span></span></div>
    {:else if fees.annual != null}
      <div class="bal-row" title="Fund expense ratios, {fees.pct}% of what the funds are worth">
        <span class="bal-k">Fees a year</span><span class="bal-v">{yearly(fees.annual)}</span>
      </div>
    {/if}
  </div>
</div>
