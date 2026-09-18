<script>
  // Desktop Log — the shared activity lists (same rows the mobile Log pane
  // renders) plus the realized FIFO lots, with the cash + trade tiles in a
  // rail beside them so a fill can be logged without leaving the page.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import ActivityLog from '$lib/components/ActivityLog.svelte';
  import CashGoalCard from '$lib/components/CashGoalCard.svelte';
  import TradeTicket from '$lib/components/TradeTicket.svelte';
  import { trades as tradesStore, loadTrades } from '$lib/stores.js';

  // trades come from the shared store — the trade tile reads the same one and
  // refreshes it after a save, so the list updates without a second fetch
  const trades = $derived($tradesStore ?? []);
  let d = $state(null);
  let txns = $state([]);
  let realized = $state([]);
  let error = $state(null);

  async function load(force = false) {
    try {
      [d, txns, realized] = await Promise.all([
        api.dashboard(),
        api.transactions(),
        api.realized(),
        loadTrades(force)
      ]);
    } catch (e) {
      error = String(e);
    }
  }
  onMount(load);
  const onSaved = () => load(true);
</script>

<div class="content">
  <div class="page-title">Log</div>
  {#if error}
    <p style="color:var(--loss)">Failed to load: {error}</p>
  {:else}
    <div class="log">
      <div class="log-main">
        <ActivityLog {trades} {txns} {realized} recent={8} />
      </div>
      <aside class="log-rail">
        {#if d}
          <CashGoalCard cash={d.kpis.cash} portfolioValue={d.kpis.portfolio_value}
            goalLabel="Monthly goal" goalCurrent={d.goal.current} goalTarget={d.goal.target}
            {onSaved} />
        {/if}
        <TradeTicket {onSaved} />
      </aside>
    </div>
  {/if}
</div>

<style>
  /* lists : rail — the rail is the same band as the dashboard's */
  .log { display: grid; grid-template-columns: minmax(0, 1fr) minmax(312px, 380px); gap: 16px 40px; align-items: start; }
  .log-main { min-width: 0; }
  .log-rail { --card-pad: 14px 16px; display: flex; flex-direction: column; gap: 16px; min-width: 0;
    position: sticky; top: 24px; }
  /* the tiles need body for their rising entry panels */
  .log-rail > :global(.glass-card) { min-height: 190px; }
  @media (max-width: 1100px) {
    .log { grid-template-columns: 1fr; }
    .log-rail { position: static; flex-direction: row; }
    .log-rail > :global(.glass-card) { flex: 1 1 0; min-width: 0; }
  }
  @media (max-width: 700px) {
    .log-rail { flex-direction: column; }
  }
</style>
