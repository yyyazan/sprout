<script>
  // Upcoming earnings across the holdings — next date per ticker, upcoming first
  // then recent-past (flagged). Own /api/earnings fetch so it never blocks the
  // chart. Lifted out of the portfolio chart header into its own rail card.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import TickerBadge from './TickerBadge.svelte';

  let earnings = $state(null);   // null = loading · [] = none · [{ticker,date,past}]
  onMount(() => {
    api.earnings()
      .then((r) => { earnings = r?.items ?? []; })
      .catch(() => { earnings = []; });
  });

  const fmtEarn = (iso) => new Date(iso + 'T00:00:00')
    .toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  // "today" / "in Nd" for scheduled dates; past reports just say "reported"
  function earnWhen(e) {
    if (e.past) return 'reported';
    const days = Math.round((new Date(e.date + 'T00:00:00') - new Date().setHours(0, 0, 0, 0)) / 86400000);
    return days <= 0 ? 'today' : `in ${days}d`;
  }
</script>

<div class="glass-card earn">
  <div class="kpi-label">Upcoming earnings</div>
  {#if earnings === null}
    <div class="earn-note">loading…</div>
  {:else if earnings.length === 0}
    <div class="earn-note">no earnings dates</div>
  {:else}
    <div class="earn-grid">
      {#each earnings as e (e.ticker)}
        <div class="earn-cell" class:earn-past={e.past}>
          <TickerBadge sym={e.ticker} />
          <span class="earn-date">{fmtEarn(e.date)}</span>
          <span class="earn-when">{earnWhen(e)}</span>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .earn { display: flex; flex-direction: column; gap: 6px; }
  .earn .kpi-label { margin-bottom: 0; }
  .earn-note { font-size: var(--fs-body); color: var(--muted); }
  .earn-grid { display: grid; grid-template-columns: repeat(3, 1fr); column-gap: 12px; row-gap: 12px; }
  .earn-cell { min-width: 0; display: flex; flex-direction: column; align-items: flex-start; gap: 3px; }
  .earn-date { font-family: var(--num); font-size: var(--fs-body); font-weight: 500; font-variant-numeric: tabular-nums;
    white-space: nowrap; margin-top: 2px; }
  .earn-when { font-size: var(--fs-meta); font-weight: 500; color: var(--muted); white-space: nowrap; }
  .earn-past { opacity: .5; }
</style>
