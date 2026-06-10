<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import KpiCard from '$lib/components/KpiCard.svelte';
  import CashGoalCard from '$lib/components/CashGoalCard.svelte';
  import DividendWraith from '$lib/components/DividendWraith.svelte';
  import AllocationRing from '$lib/components/AllocationRing.svelte';
  import DashboardStage from '$lib/components/DashboardStage.svelte';
  import MarketPulse from '$lib/components/MarketPulse.svelte';
  import GardenView from '$lib/components/GardenView.svelte';
  import { primeHoldings } from '$lib/stores.js';

  let d = $state(null);
  let garden = $state(null);
  let error = $state(null);

  onMount(async () => {
    try {
      [d, garden] = await Promise.all([api.dashboard(), api.garden()]);
      primeHoldings(d.cards);          // share holdings with the sidebar rail
    } catch (e) {
      error = String(e);
    }
  });

  // Re-pull the dashboard after a transaction is saved from the cash tile, so cash updates.
  async function refresh() {
    try {
      d = await api.dashboard();
      primeHoldings(d.cards);
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

    <!-- stage (big, leftmost) · widget rail (mid) · template column (right) -->
    <div class="dash">
      <DashboardStage equity={d.equity_curve} spy={d.spy_curve} twr={d.twr} />

      <aside class="dash-rail">
        <div class="rail-duo">
          <KpiCard label="Portfolio Value" value={d.kpis.portfolio_value} kind="money" size="mini" subtitle="stocks + cash" />
          <KpiCard label="Total P&L" value={d.kpis.total_pnl} kind="money_compact" size="mini" subtitle="unrealized + realized"
            tone={d.kpis.total_pnl >= 0 ? 'gain' : 'loss'} />
        </div>
        <CashGoalCard cash={d.kpis.cash} portfolioValue={d.kpis.portfolio_value}
          goalLabel="monthly goal" goalCurrent={d.goal.current} goalTarget={d.goal.target}
          onSaved={refresh} />
        <div class="rail-duo rail-bare">
          <DividendWraith data={d.dividends} holdings={d.cards} />
          <AllocationRing holdings={d.cards.filter((c) => !c.is_joker)} />
        </div>
        <MarketPulse />
      </aside>

      <!-- scaffolding column: empty slots to design future widgets into -->
      <aside class="dash-templates">
        {#each [{ h: 'tall' }, { h: 'short' }, { h: 'short' }] as t, i (i)}
          <button class="tpl tpl-{t.h}" type="button" aria-label="Empty widget slot">
            <span class="tpl-plus" aria-hidden="true">+</span>
            <span class="tpl-label">widget</span>
          </button>
        {/each}
      </aside>
    </div>
  </div>
{:else}
  <div class="content"><p style="color:var(--muted)">Loading…</p></div>
{/if}

<style>
  /* stage : rail : templates = 2 : 1 : 1 (stage one unit narrower than before) */
  .dash { display: grid; grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr) minmax(240px, 1fr);
    gap: 16px; align-items: start; }
  .dash > :global(.stage) { min-height: 520px; }

  .dash-rail { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
  .rail-duo { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .rail-duo > :global(.glass-card) { padding: 12px 14px; }
  /* dividends + allocation: intentionally chrome-less, side by side */
  .rail-bare { align-items: center; }

  /* template column — dashed placeholder slots to build future widgets into */
  .dash-templates { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
  .tpl { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
    width: 100%; box-sizing: border-box; cursor: pointer; color: var(--muted);
    background: color-mix(in srgb, var(--paper) 55%, transparent);
    border: 2px dashed color-mix(in srgb, var(--ink) 28%, transparent); border-radius: var(--r);
    transition: border-color .14s ease, color .14s ease, transform .12s ease, background .14s ease; }
  .tpl:hover { border-color: var(--ink); color: var(--ink); transform: translateY(-2px);
    background: color-mix(in srgb, var(--paper) 80%, transparent); }
  .tpl-tall { min-height: 224px; }
  .tpl-short { min-height: 150px; }
  .tpl-plus { font-family: var(--sans); font-size: 26px; font-weight: 400; line-height: 1; }
  .tpl-label { font-family: var(--sans); font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .14em; }

  @media (max-width: 1280px) {
    /* drop the template column first; keep stage + rail at 2 : 1 */
    .dash { grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr); }
    .dash-templates { display: none; }
  }
  @media (max-width: 1100px) {
    .dash { grid-template-columns: 1fr; }
    .dash > :global(.stage) { min-height: 480px; }
  }
  @media (max-width: 700px) {
    .rail-duo { gap: 12px; }
  }
</style>
