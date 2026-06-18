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
  <div class="earn-h">Upcoming earnings</div>
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
  .earn { display: flex; flex-direction: column; gap: 10px; padding: 13px 15px 14px; }
  .earn-h { font-family: var(--sans); font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .12em; color: var(--muted); }
  .earn-note { font-family: var(--mono); font-size: 11px; color: var(--muted); }
  /* 3×2 cells split by hairlines, same language as MarketPulse */
  .earn-grid { display: grid; grid-template-columns: repeat(3, 1fr); column-gap: 12px; row-gap: 10px; }
  .earn-cell { min-width: 0; display: flex; flex-direction: column; align-items: flex-start; gap: 3px; }
  .earn-date { font-family: var(--mono); font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums;
    white-space: nowrap; }
  .earn-when { font-family: var(--sans); font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .05em; color: var(--brand); white-space: nowrap; }
  .earn-past { opacity: .55; }
  .earn-past .earn-when { color: var(--muted); }
</style>
