<script>
  // Mobile Log pane — the two click-to-expand logger tiles (cash + trade),
  // full-width, with the shared searchable activity lists underneath
  // (ActivityLog — same component the desktop /trades page renders). Tiles
  // stay near the top so the iOS keyboard never covers their rising panels.
  import { onMount } from 'svelte';
  import CashGoalCard from '../CashGoalCard.svelte';
  import TradeTicket from '../TradeTicket.svelte';
  import ActivityLog from '../ActivityLog.svelte';
  import { api } from '$lib/api.js';
  import { trades as tradesStore, loadTrades } from '$lib/stores.js';

  let { d, refresh } = $props();

  // Trades come from the shared store (TradeTicket reads the same one, so the
  // pane doesn't fetch /api/trades a second time); transactions and realized
  // lots stay local.
  const trades = $derived($tradesStore ?? []);
  let txns = $state([]);
  let realized = $state([]);
  function loadActivity(force = false) {
    loadTrades(force);
    api.transactions().then((x) => (txns = x ?? [])).catch(() => { /* stays as-is */ });
    api.realized().then((r) => (realized = r ?? [])).catch(() => { /* stays as-is */ });
  }
  onMount(loadActivity);

  // refresh the dashboard payload AND this pane's activity lists after a save
  async function onSaved() {
    await refresh?.();
    loadActivity(true);
  }
</script>

<div class="ml-tiles">
  <CashGoalCard cash={d.kpis.cash} portfolioValue={d.kpis.portfolio_value}
    goalLabel="Monthly goal" goalCurrent={d.goal.current} goalTarget={d.goal.target}
    {onSaved} />
  <TradeTicket {onSaved} />
</div>

<ActivityLog {trades} {txns} {realized} onChanged={onSaved} />

<style>
  .ml-tiles { --card-pad: 14px 16px; display: flex; flex-direction: column; gap: 12px;
    padding-top: calc(18px + env(safe-area-inset-top)); }
  /* give the tiles enough body for their 60%-rise entry panels */
  .ml-tiles > :global(.glass-card) { min-height: 190px; }
</style>
