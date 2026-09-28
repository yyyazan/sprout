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
{:else if $isMobile}
  {#if d}
    <!-- phone: dedicated tree (tab bar, sheet, safe areas). EXCLUSIVE with the
         desktop tree — the garden's #garden-root is a singleton. -->
    <MobileDashboard {d} {garden} {refresh} />
  {:else}
    <!-- phone skeleton: the home pane's stack (header, search, KPI duo, chart, driver rows) -->
    <div class="m-skel" aria-busy="true" aria-label="Loading">
      <div class="m-sk-head">
        <div class="greeting-title"><span class="skel skel-t" style="width:6.5em"></span></div>
        <span class="skel sk-tool"></span><span class="skel sk-tool"></span>
      </div>
      <div class="strip" aria-hidden="true"><span class="strip-icon"></span><span class="strip-ph">Search</span></div>
      <div class="rail-duo">
        {#each [0, 1] as i (i)}{@render kpiSkel()}{/each}
      </div>
      {@render chartSkel()}
      <div class="sk-rows">
        <div class="m-sk-glance"><span class="skel skel-t" style="width:40%"></span></div>
        {#each [0, 1, 2, 3, 4] as i (i)}{@render rowSkel()}{/each}
      </div>
    </div>
  {/if}
{:else}
  <!-- Desktop. The grid renders before the dashboard payload lands: parts that
       need it show a skeleton (real card chrome, bars for content, min-heights
       = the loaded cards' measured heights); the widgets that fetch their own
       data (trade ticket, earnings, market) mount right away and never remount. -->
  <div class="content content-has-hero" aria-busy={!d}>
    <div class="page-hero" class:page-hero--flat={!SHOW_GARDEN || !d}>
      {#if SHOW_GARDEN && d}
        <GardenView positions={garden.positions} period={garden.period} />
      {/if}
      <div class="page-header-overlay">
        <div class="greeting-title">{#if d}{d.greeting}{:else}<span class="skel skel-t" style="width:7em"></span>{/if}</div>
      </div>
    </div>

    <!-- stage (big, leftmost) · widget rail (mid) · template column (right) -->
    <div class="dash">
      {#if d}
        <DashboardStage equity={d.equity_curve} spy={d.spy_curve} twr={d.twr} netInvested={d.net_invested} drivers={d.drivers} />
      {:else}
        <section class="sk-stage" aria-hidden="true">
          <div class="strip"><span class="strip-icon"></span><span class="strip-ph">Search</span><kbd class="strip-kbd">⌘K</kbd></div>
          <div class="glass-card sk-title"></div>
          {@render chartSkel()}
        </section>
      {/if}

      <aside class="dash-rail">
        <div class="rail-duo">
          {#if d}
            <BalanceCard total={d.kpis.portfolio_value} equities={d.kpis.equities}
              dayGain={dayMove.gain} dayPct={dayMove.pct} ret={allTime.ret} vsSpy={allTime.vsSpy} />
            <PnlCard total={d.kpis.total_pnl} realized={d.kpis.realized_pnl} unrealized={d.kpis.unrealized_pnl} />
          {:else}
            {#each [0, 1] as i (i)}{@render kpiSkel()}{/each}
          {/if}
        </div>
        {#if d}
          <CashGoalCard cash={d.kpis.cash} portfolioValue={d.kpis.portfolio_value}
            goalLabel="Monthly goal" goalCurrent={d.goal.current} goalTarget={d.goal.target}
            onSaved={refresh} />
        {:else}
          <div class="glass-card sk-card" style="min-height:149px" aria-hidden="true">
            <span class="skel skel-t" style="width:24%"></span><span class="skel sk-hero"></span>
            <span class="skel skel-t" style="width:36%"></span><span class="skel sk-bar"></span>
          </div>
        {/if}
        <TradeTicket onSaved={refresh} />
        <EarningsCard />
        <MarketPulse />
      </aside>

      <!-- right column — dividends + allocation rings (chrome-less) -->
      <aside class="dash-templates">
        {#if d}
          <div class="tmpl-ring"><DividendRing data={d.dividends} holdings={d.cards} /></div>
          <div class="tmpl-ring"><AllocationRing holdings={d.cards.filter((c) => !c.is_joker)} /></div>
        {:else}
          {#each [0, 1] as i (i)}<div class="tmpl-ring sk-ringcell" aria-hidden="true"><span class="skel sk-ring"></span></div>{/each}
        {/if}
      </aside>
    </div>
  </div>
{/if}

{#snippet kpiSkel()}
  <div class="glass-card kpi-card sk-card sk-kpi">
    <span class="skel skel-t" style="width:58%"></span>
    <span class="skel sk-hero"></span>
    <span class="skel skel-t" style="width:80%"></span>
    <span class="skel skel-t" style="width:64%"></span>
  </div>
{/snippet}

{#snippet chartSkel()}
  <div class="chart-widget sk-chart">
    <div class="sk-tools"><span class="skel sk-pill" style="width:92px"></span><span class="skel sk-pill" style="width:104px"></span></div>
    <span class="skel sk-plot"></span>
    <span class="skel sk-pill" style="width:62%"></span>
  </div>
{/snippet}

{#snippet rowSkel()}
  <div class="sk-row"><span class="skel sk-badge"></span><span class="skel skel-t" style="width:46%"></span><span class="skel skel-t" style="width:18%;margin-left:auto"></span></div>
{/snippet}

<style>
  /* stage : rail : templates = 2 : 1 : 0.7. The stage sizes itself: home and
     the stock view are the same title card + .chart-widget stack. */
  .dash { display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(312px, 1.05fr) minmax(180px, 0.7fr);
    gap: 16px; align-items: start; }

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
  @media (max-width: 700px) {
    .rail-duo { gap: 12px; }
  }

  /* ── loading skeleton (see app.css .skel) ── */
  .sk-stage { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
  .sk-title { min-height: var(--title-h); }
  .sk-card { display: flex; flex-direction: column; gap: 10px; }
  .rail-duo > .sk-kpi { min-height: 174px; justify-content: flex-start; }
  .sk-hero { width: 62%; height: 24px; }
  .sk-bar { height: 14px; border-radius: 999px; margin-top: auto; }
  .sk-chart { display: flex; flex-direction: column; gap: 10px; }
  .sk-tools { display: flex; gap: 8px; }
  .sk-pill { height: 24px; border-radius: 999px; }
  .sk-plot { flex: 1; border-radius: var(--r); }
  .sk-row { display: flex; align-items: center; gap: 10px; min-height: 40px; border-bottom: var(--bw) solid var(--hairline); }
  .sk-row:last-child { border-bottom: 0; }
  .sk-badge { width: 44px; height: 18px; flex: 0 0 auto; }
  .sk-ringcell { align-items: center; justify-content: center; }
  .sk-ringcell > .sk-ring { flex: 0 0 auto; width: 160px; height: 160px; border-radius: 50%; background: none;
    border: 15px solid color-mix(in srgb, var(--ink) 10%, transparent); }

  /* phone: the home pane's padding and rhythm (MobileHome) */
  .m-skel { display: flex; flex-direction: column; gap: 14px;
    padding: calc(33px + env(safe-area-inset-top)) 14px 24px; --card-pad: 14px 16px; }
  .m-skel .rail-duo { gap: 12px; }
  /* header row = MobileHome's (greeting + two 30px tool rings, 12 below) */
  .m-sk-head { display: flex; align-items: flex-start; gap: 8px; height: 42px; }
  .m-sk-head .greeting-title { margin-right: auto; }
  .sk-tool { width: 30px; height: 30px; border-radius: 50%; }
  .m-skel .rail-duo > .sk-kpi { min-height: 174px; }
  .m-sk-glance { height: 30px; display: flex; align-items: center; }
  .sk-rows { display: flex; flex-direction: column; }
  .sk-rows .sk-row { min-height: 48px; }
</style>
