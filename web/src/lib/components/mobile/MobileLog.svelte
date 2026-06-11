<script>
  // Mobile Log pane — the two click-to-expand logger tiles (cash + trade),
  // full-width, with a read-only recent-activity list underneath for
  // save confirmation. Tiles stay near the top so the iOS keyboard never
  // covers their rising entry panels.
  import { onMount } from 'svelte';
  import CashGoalCard from '../CashGoalCard.svelte';
  import TradeTicket from '../TradeTicket.svelte';
  import { api } from '$lib/api.js';
  import { fmt } from '$lib/format.js';

  let { d, refresh } = $props();

  let trades = $state([]);
  let txns = $state([]);
  async function loadActivity() {
    try {
      [trades, txns] = await Promise.all([api.trades(), api.transactions()]);
    } catch { /* lists stay as-is */ }
  }
  onMount(loadActivity);

  // refresh the dashboard payload AND this pane's activity lists after a save
  async function onSaved() {
    await refresh?.();
    loadActivity();
  }

  const recentTrades = $derived(trades.slice(0, 8));
  const recentTxns = $derived(txns.slice(0, 5));
</script>

<div class="ml-tiles">
  <CashGoalCard cash={d.kpis.cash} portfolioValue={d.kpis.portfolio_value}
    goalLabel="monthly goal" goalCurrent={d.goal.current} goalTarget={d.goal.target}
    {onSaved} />
  <TradeTicket {onSaved} />
</div>

{#if recentTrades.length}
  <div class="ml-section">Recent trades</div>
  {#each recentTrades as t (t.date + t.ticker + t.action + t.shares)}
    <div class="ml-row">
      <span class="ml-sym">{t.ticker}</span>
      <span class="ml-kind {t.action === 'buy' ? 'up' : 'down'}">{t.action}</span>
      <span class="ml-fig">{fmt.shares(t.shares)} sh</span>
      <span class="ml-date">{t.date}</span>
    </div>
  {/each}
{/if}

{#if recentTxns.length}
  <div class="ml-section">Recent transactions</div>
  {#each recentTxns as x (x.date + x.direction + x.amount)}
    <div class="ml-row">
      <span class="ml-sym">{x.direction}</span>
      <span class="ml-fig {x.amount >= 0 ? 'up' : 'down'}">{fmt.signedMoney2(x.amount)}</span>
      <span class="ml-date">{x.date}</span>
    </div>
  {/each}
{/if}

<style>
  .ml-tiles { display: flex; flex-direction: column; gap: 12px;
    padding-top: calc(12px + env(safe-area-inset-top)); }
  /* give the tiles enough body for their 60%-rise entry panels */
  .ml-tiles > :global(.glass-card) { min-height: 190px; padding: 14px 16px; }

  .ml-section { padding: 18px 2px 6px; font-family: var(--sans); font-size: 9.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }
  .ml-row { display: flex; align-items: baseline; gap: 10px; min-height: 40px; padding: 9px 4px;
    border-bottom: var(--bw) solid var(--hairline); }
  .ml-sym { flex: 0 0 auto; font-family: var(--mono); font-size: 13px; font-weight: 700; }
  .ml-kind { flex: 0 0 auto; font-family: var(--sans); font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .06em; }
  .ml-fig { flex: 1 1 auto; text-align: right; font-family: var(--mono); font-size: 12px; font-weight: 700;
    font-variant-numeric: tabular-nums; }
  .ml-date { flex: 0 0 auto; font-family: var(--mono); font-size: 11px; color: var(--muted);
    font-variant-numeric: tabular-nums; }
  .up { color: var(--gain); }
  .down { color: var(--loss); }
</style>
