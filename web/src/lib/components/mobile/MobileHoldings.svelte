<script>
  // Mobile Holdings pane — the sidebar rail rebuilt for a full phone column:
  // richer rows (price + live move + value + weight), a D/W/M move window, and
  // the watchlist underneath. Same stores and live-momentum fallback as the rail.
  import { holdings, moves, watchlist, openStock, cardToHolding } from '$lib/stores.js';
  import TickerBadge from '../TickerBadge.svelte';

  const WINS = [['day', 'D'], ['wk', 'W'], ['mo', 'M']];
  let win = $state('day');

  const rows = $derived(
    [...($holdings ?? [])].sort((a, b) => (b.market_value ?? 0) - (a.market_value ?? 0))
  );

  // live move (fresh /api/momentum) with the frozen dashboard payload as fallback;
  // the month window only exists live
  const moveOf = (c, w) => {
    const live = $moves[c.ticker];
    if (w === 'mo') return live?.month_pct ?? null;
    const v = live ? (w === 'day' ? live.day_pct : live.week_pct) : (w === 'day' ? c.day_pct : c.week_pct);
    return v ?? 0;
  };
  const pct = (n) => n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + '%';
  const wt = (n) => (n ?? 0).toFixed(1) + '%';
  const usd = (n) => {
    if (n == null) return '—';
    const a = Math.abs(n);
    if (a >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'k';
    return '$' + Math.round(n);
  };
  const px = (n) => (n == null ? '—' : '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));

  function open(c) {
    openStock({ ticker: c.ticker, name: c.company_name, holding: cardToHolding(c) });
  }
</script>

<div class="mho-head">
  <span class="mho-title">Holdings</span>
  <div class="mho-win" role="group" aria-label="move window">
    {#each WINS as [k, label] (k)}
      <button class="btn btn-sm btn-mono" class:on={win === k} onclick={() => (win = k)}>{label}</button>
    {/each}
  </div>
</div>

{#if $holdings === null}
  <div class="mho-empty">Loading…</div>
{:else if rows.length === 0}
  <div class="mho-empty">No holdings yet.</div>
{:else}
  {#each rows as c (c.ticker)}
    {@const mv = moveOf(c, win)}
    <button class="mho-row" onclick={() => open(c)}>
      <span class="mho-main">
        <span class="mho-line">
          <TickerBadge sym={c.ticker} />
          <span class="mho-name">{c.company_name}</span>
        </span>
        <span class="mho-sub"><span>{usd(c.market_value)}</span><span>{wt(c.position_pct)}</span></span>
      </span>
      <span class="mho-right">
        <span class="mho-px">{px($moves[c.ticker]?.spot ?? c.current_price)}</span>
        <span class="pct-pill {(mv ?? 0) >= 0 ? 'up' : 'down'}">{pct(mv)}</span>
      </span>
    </button>
  {/each}
{/if}

{#if $watchlist?.length}
  <div class="mho-head mho-head-wl">
    <span class="mho-title">Watchlist</span>
  </div>
  {#each $watchlist as w (w.ticker)}
    {@const wv = win === 'day' ? w.dayPct : win === 'wk' ? w.weekPct : null}
    <button class="mho-row" onclick={() => openStock({ ticker: w.ticker, name: w.name, holding: null })}>
      <span class="mho-main">
        <span class="mho-line">
          <TickerBadge sym={w.ticker} />
          <span class="mho-name">{w.name}</span>
        </span>
      </span>
      <span class="mho-right">
        <span class="mho-px">{px(w.price)}</span>
        <span class="pct-pill {(wv ?? 0) >= 0 ? 'up' : 'down'}">{pct(wv)}</span>
      </span>
    </button>
  {/each}
{/if}

<style>
  .mho-head { display: flex; align-items: center; justify-content: space-between;
    padding: calc(20px + env(safe-area-inset-top)) 0 6px; }
  .mho-head-wl { padding-top: 22px; }
  .mho-title { font-size: var(--fs-title); font-weight: 600; color: var(--ink); }
  .mho-win { display: inline-flex; gap: 2px; }

  .mho-empty { padding: 14px 0; font-size: var(--fs-body); font-weight: 500; color: var(--muted); }

  /* ~56px touch rows: identity left, price + move right */
  .mho-row { width: 100%; display: flex; align-items: center; gap: 12px; min-height: 56px;
    padding: 10px 0; border: 0; border-bottom: var(--bw) solid var(--hairline); border-radius: 0;
    background: transparent; cursor: pointer; text-align: left; font: inherit; color: var(--ink); }
  .mho-row:active { background: var(--hover); }

  .mho-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
  .mho-line { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .mho-name { font-size: var(--fs-body); font-weight: 500; color: var(--muted); min-width: 0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mho-sub { display: flex; gap: 10px; font-family: var(--num); font-size: var(--fs-meta); font-weight: 500;
    color: var(--muted); font-variant-numeric: tabular-nums; }

  .mho-right { flex: 0 0 auto; display: flex; flex-direction: column; align-items: flex-end; gap: 5px; }
  .mho-px { font-family: var(--num); font-size: var(--fs-body); font-weight: 500; color: var(--ink);
    font-variant-numeric: tabular-nums; }
</style>
