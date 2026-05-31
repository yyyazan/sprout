<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { equity } from '$lib/charts.js';
  import KpiCard from '$lib/components/KpiCard.svelte';
  import ProgressCard from '$lib/components/ProgressCard.svelte';
  import ChartCard from '$lib/components/ChartCard.svelte';
  import AllocationPanel from '$lib/components/AllocationPanel.svelte';
  import CardHand from '$lib/components/CardHand.svelte';
  import GardenView from '$lib/components/GardenView.svelte';

  let d = $state(null);
  let garden = $state(null);
  let error = $state(null);

  onMount(async () => {
    try {
      [d, garden] = await Promise.all([api.dashboard(), api.garden()]);
    } catch (e) {
      error = String(e);
    }
  });
</script>

{#if error}
  <div class="content"><p style="color:var(--loss)">Failed to load: {error}</p></div>
{:else if d && garden}
  <div class="content content-has-hero">
    <div class="page-hero">
      <GardenView positions={garden.positions} period={garden.period} />
      <div class="page-header-overlay">
        <div class="greeting-title">{d.greeting}</div>
      </div>
    </div>

    <CardHand cards={d.cards} />

    <div class="widget-grid">
      <KpiCard label="Cash" value={d.kpis.cash} kind="money" size="small" subtitle="available · incl. manual reconciliation offset" />
      <KpiCard label="S&P500 delta" value={d.kpis.spy_delta} kind="percent" size="small" subtitle="since inception" />
      <KpiCard label="Portfolio Value" value={d.kpis.portfolio_value} kind="money" size="medium" subtitle="equity + cash" />
      <AllocationPanel alloc={d.allocation} size="tall" />
      <ProgressCard label="goal" current={d.goal.current} target={d.goal.target} size="medium" />
      <KpiCard label="Total P&L" value={d.kpis.total_pnl} kind="money_compact" size="medium" subtitle="unrealized + realized" />
      <ChartCard title="Portfolio Value" chart={equity(d.equity_curve)} size="xl" />
    </div>
  </div>
{:else}
  <div class="content"><p style="color:var(--muted)">Loading…</p></div>
{/if}
