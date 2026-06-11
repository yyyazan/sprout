<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import KpiCard from '$lib/components/KpiCard.svelte';
  import CashGoalCard from '$lib/components/CashGoalCard.svelte';
  import DividendWraith from '$lib/components/DividendWraith.svelte';
  import AllocationRing from '$lib/components/AllocationRing.svelte';
  import DashboardStage from '$lib/components/DashboardStage.svelte';
  import MarketPulse from '$lib/components/MarketPulse.svelte';
  import TradeTicket from '$lib/components/TradeTicket.svelte';
  import ResearchChat from '$lib/components/ResearchChat.svelte';
  import GardenView from '$lib/components/GardenView.svelte';
  import MobileDashboard from '$lib/components/mobile/MobileDashboard.svelte';
  import { primeHoldings } from '$lib/stores.js';
  import { isMobile } from '$lib/isMobile.js';

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
  {#if $isMobile}
    <!-- phone: dedicated tree (tab bar, sheet, safe areas). EXCLUSIVE with the
         desktop tree — the garden's #garden-root is a singleton. -->
    <MobileDashboard {d} {garden} {refresh} />
  {:else}
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
        <TradeTicket onSaved={refresh} />
        <div class="rail-duo rail-bare">
          <DividendWraith data={d.dividends} holdings={d.cards} />
          <AllocationRing holdings={d.cards.filter((c) => !c.is_joker)} />
        </div>
        <MarketPulse />
      </aside>

      <!-- rightmost column: mock research chat -->
      <aside class="dash-templates">
        <ResearchChat />
      </aside>
    </div>
  </div>
  {/if}
{:else}
  <div class="content"><p style="color:var(--muted)">Loading…</p></div>
{/if}

<style>
  /* stage : rail : chat = 2 : 1 : 1 (stage one unit narrower than before) */
  /* --stage-h = title card (--title-h) + gap (16) + chart box (440); keeps the
     portfolio stage the exact height of the stock view's header + chart stack */
  .dash { --stage-h: calc(var(--title-h) + 16px + 440px); display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr) minmax(240px, 1fr);
    gap: 16px; align-items: start; }
  .dash > :global(.stage) { min-height: var(--stage-h); }

  .dash-rail { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
  .rail-duo { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .rail-duo > :global(.glass-card) { padding: 12px 14px; }
  /* KPI duo locked to the title-card height so the top band lines up across columns
     (rail-bare = dividends + allocation, left to size themselves) */
  .rail-duo:not(.rail-bare) > :global(.glass-card) { height: var(--title-h); }
  /* dividends + allocation: intentionally chrome-less, side by side */
  .rail-bare { align-items: center; }

  /* rightmost column — mock research chat */
  .dash-templates { display: flex; flex-direction: column; gap: 16px; min-width: 0; }

  @media (max-width: 1280px) {
    /* drop the template column first; keep stage + rail at 2 : 1 */
    .dash { grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr); }
    .dash-templates { display: none; }
  }
  @media (max-width: 1100px) {
    .dash { grid-template-columns: 1fr; }
  }
  @media (max-width: 900px) {
    /* chart box shrinks to 340 (mirrors StockPanel) */
    .dash { --stage-h: calc(var(--title-h) + 16px + 340px); }
  }
  @media (max-width: 700px) {
    .rail-duo { gap: 12px; }
  }
</style>
