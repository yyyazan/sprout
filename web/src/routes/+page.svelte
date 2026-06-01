<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import KpiCard from '$lib/components/KpiCard.svelte';
  import SparkValueCard from '$lib/components/SparkValueCard.svelte';
  import ProgressCard from '$lib/components/ProgressCard.svelte';
  import MomentumDeck from '$lib/components/MomentumDeck.svelte';
  import PortfolioChart from '$lib/components/PortfolioChart.svelte';
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

    <div class="kpi-strip">
      <SparkValueCard label="Portfolio Value" value={d.kpis.portfolio_value} series={d.equity_curve.y} subtitle="since inception" />
      <KpiCard label="Total P&L" value={d.kpis.total_pnl} kind="money_compact" size="strip" subtitle="unrealized + realized" tone="gain" />
      <KpiCard label="S&P500 delta" value={d.kpis.spy_delta} kind="percent" size="strip" subtitle="since inception" />
      <KpiCard label="Cash" value={d.kpis.cash} kind="money" size="strip"
        subtitle={d.kpis.portfolio_value ? `${((d.kpis.cash / d.kpis.portfolio_value) * 100).toFixed(0)}% of portfolio` : 'available'} />
      <ProgressCard label="goal" current={d.goal.current} target={d.goal.target} size="strip" />
    </div>

    <MomentumDeck cards={d.cards}>
      {#snippet chart()}
        <PortfolioChart equity={d.equity_curve} spy={d.spy_curve} twr={d.twr} />
      {/snippet}
    </MomentumDeck>
  </div>
{:else}
  <div class="content"><p style="color:var(--muted)">Loading…</p></div>
{/if}
im/r