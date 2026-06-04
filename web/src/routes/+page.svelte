<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import KpiCard from '$lib/components/KpiCard.svelte';
  import CashGoalCard from '$lib/components/CashGoalCard.svelte';
  import DividendWraith from '$lib/components/DividendWraith.svelte';
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

  // Re-pull the dashboard after a transaction is saved from the cash tile, so cash updates.
  async function refresh() {
    try {
      d = await api.dashboard();
    } catch (e) {
      error = String(e);
    }
  }
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

    <div class="pnl-strip">
      {#each Array.from({ length: 6 }) as _, i (i)}
        <KpiCard label="Total P&L" value={d.kpis.total_pnl} kind="money_compact" size="mini" subtitle="unrealized + realized" tone="gain" />
      {/each}
    </div>

    <MomentumDeck cards={d.cards}>
      {#snippet chart()}
        <PortfolioChart equity={d.equity_curve} spy={d.spy_curve} twr={d.twr} />
      {/snippet}
      {#snippet belowDeck()}
        <CashGoalCard cash={d.kpis.cash} portfolioValue={d.kpis.portfolio_value}
          goalLabel="monthly goal" goalCurrent={d.goal.current} goalTarget={d.goal.target}
          onSaved={refresh} />
        <DividendWraith data={d.dividends} holdings={d.cards} />
      {/snippet}
    </MomentumDeck>
  </div>
{:else}
  <div class="content"><p style="color:var(--muted)">Loading…</p></div>
{/if}
