<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import BalanceCard from '$lib/components/BalanceCard.svelte';
  import PnlCard from '$lib/components/PnlCard.svelte';
  import EarningsCard from '$lib/components/EarningsCard.svelte';
  import CashGoalCard from '$lib/components/CashGoalCard.svelte';
  import DividendRing from '$lib/components/DividendRing.svelte';
  import AllocationRing from '$lib/components/AllocationRing.svelte';
  import DashboardStage from '$lib/components/DashboardStage.svelte';
  import MarketPulse from '$lib/components/MarketPulse.svelte';
  import TradeTicket from '$lib/components/TradeTicket.svelte';
  import GardenView from '$lib/components/GardenView.svelte';
  import MobileDashboard from '$lib/components/mobile/MobileDashboard.svelte';
  import { primeHoldings, moves, portfolioDayMove, allTimeReturn } from '$lib/stores.js';
  import { isMobile } from '$lib/isMobile.js';
  import { SHOW_GARDEN } from '$lib/config.js';

  let d = $state(null);
  let error = $state(null);

  // Garden data is a subset of the dashboard payload (cards minus jokers +
  // period), so derive it instead of a second /api/garden request. The
  // standalone /garden debug route still fetches that endpoint directly.
  const garden = $derived(
    d ? { positions: d.cards.filter((c) => !c.is_joker), period: d.period } : null
  );

  // today's aggregate intraday change — live via the momentum store, card fallback
  const dayMove = $derived(d ? portfolioDayMove(d.cards, $moves) : { gain: null, pct: null });
  const allTime = $derived(allTimeReturn(d?.twr));

  // Re-pull the dashboard after a transaction is saved from the cash tile, so cash updates.
  // Also the poll tick below, so the equity curve / stats widget stays live.
  let lastFetch = 0;
  async function refresh() {
    try {
      d = await api.dashboard();
      primeHoldings(d.cards);          // share holdings with the sidebar rail
      lastFetch = Date.now();
    } catch (e) {
      error = String(e);
    }
  }

  // Poll like the momentum store does (see startMomentum in stores.js): pause
  // while the tab is hidden, catch up immediately on refocus if stale.
  const DASHBOARD_POLL_MS = 60_000;
  onMount(() => {
    refresh();

    const onVisible = () => {
      if (!document.hidden && Date.now() - lastFetch > DASHBOARD_POLL_MS) refresh();
    };
    document.addEventListener('visibilitychange', onVisible);
    const timer = setInterval(() => { if (!document.hidden) refresh(); }, DASHBOARD_POLL_MS);

    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      clearInterval(timer);
    };
  });
</script>

{#if error}
  <div class="content"><p style="color:var(--loss)">Failed to load: {error}</p></div>
{:else if d}
  {#if $isMobile}
    <!-- phone: dedicated tree (tab bar, sheet, safe areas). EXCLUSIVE with the
         desktop tree — the garden's #garden-root is a singleton. -->
    <MobileDashboard {d} {garden} {refresh} />
  {:else}
  <div class="content content-has-hero">
    <div class="page-hero" class:page-hero--flat={!SHOW_GARDEN}>
      {#if SHOW_GARDEN}
        <GardenView positions={garden.positions} period={garden.period} />
      {/if}
      <div class="page-header-overlay">
        <div class="greeting-title">{d.greeting}</div>
      </div>
    </div>

    <!-- stage (big, leftmost) · widget rail (mid) · template column (right) -->
    <div class="dash">
      <DashboardStage equity={d.equity_curve} spy={d.spy_curve} twr={d.twr} netInvested={d.net_invested} />

      <aside class="dash-rail">
        <div class="rail-duo">
          <BalanceCard total={d.kpis.portfolio_value} equities={d.kpis.equities}
            dayGain={dayMove.gain} dayPct={dayMove.pct} ret={allTime.ret} vsSpy={allTime.vsSpy} />
          <PnlCard total={d.kpis.total_pnl} realized={d.kpis.realized_pnl} unrealized={d.kpis.unrealized_pnl} />
        </div>
        <CashGoalCard cash={d.kpis.cash} portfolioValue={d.kpis.portfolio_value}
          goalLabel="Monthly goal" goalCurrent={d.goal.current} goalTarget={d.goal.target}
          onSaved={refresh} />
        <TradeTicket onSaved={refresh} />
        <EarningsCard />
        <MarketPulse />
      </aside>

      <!-- right column — dividends + allocation rings (chrome-less) -->
      <aside class="dash-templates">
        <div class="tmpl-ring"><DividendRing data={d.dividends} holdings={d.cards} /></div>
        <div class="tmpl-ring"><AllocationRing holdings={d.cards.filter((c) => !c.is_joker)} /></div>
      </aside>
    </div>
  </div>
  {/if}
{:else}
  <div class="content"><p style="color:var(--muted)">Loading…</p></div>
{/if}

<style>
  /* stage : rail : templates = 2 : 1 : 0.7 */
  /* --stage-h = the stock view's header (--title-h) + gap (16) + chart box (440);
     at home the portfolio strip + chart card fill the same height */
  .dash { --stage-h: calc(var(--title-h) + 16px + 440px); display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(312px, 1.05fr) minmax(180px, 0.7fr);
    gap: 16px; align-items: start; }
  .dash > :global(.stage) { min-height: var(--stage-h); }

  /* right column — the two rings; drops away first when the viewport tightens */
  .dash-templates { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
  /* dividends + allocation rings, framed as widgets in the right column */
  .tmpl-ring { height: 190px; padding: 10px; display: flex; }
  .tmpl-ring > :global(*) { flex: 1; min-width: 0; }

  .dash-rail { --card-pad: 14px 16px; display: flex; flex-direction: column; gap: 16px; min-width: 0; }
  .rail-duo { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }
  /* KPI duo: at least the title-card height (grid stretch keeps the pair equal) */
  .rail-duo > :global(.glass-card) { min-height: var(--title-h); }

  /* template column drops first; stage + rail keep the 2:1 split */
  @media (max-width: 1280px) {
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
