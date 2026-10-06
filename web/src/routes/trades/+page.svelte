<script>
  // Desktop Log — the shared activity lists (same rows the mobile Log pane
  // renders), the realized FIFO lots and the previously held tickers, with the
  // cash + trade tiles in a rail beside them (above them once the page is too
  // narrow for two columns) so a fill can be logged without scrolling.
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
  let closed = $state([]);
  let error = $state(null);

  async function load(force = false) {
    try {
      [d, txns, realized, closed] = await Promise.all([
        api.dashboard(),
        api.transactions(),
        api.realized(),
        api.closed(),
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
    <div class="log dash-grid">
      <div class="log-main">
        <ActivityLog {trades} {txns} {realized} {closed} recent={8} onChanged={() => load(true)} />
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
  /* lists : rail : empty — the columns are the home grid's (.dash-grid in app.css),
     lists where the stage is, the tiles where the rail is, the rings' column left empty */
  .log-main { min-width: 0; }
  .log-rail { --card-pad: 14px 16px; display: flex; flex-direction: column; gap: 16px; min-width: 0;
    position: sticky; top: 24px; }
  /* one column: the rail leads, the tiles are what this page is for and the lists run long.
     Side by side they need body for their rising entry panels */
  @media (max-width: 1100px) {
    .log-rail { order: -1; position: static; flex-direction: row; }
    .log-rail > :global(.glass-card) { flex: 1 1 0; min-width: 0; min-height: 190px; }
  }
  @media (max-width: 700px) {
    .log-rail { flex-direction: column; }
  }
</style>
