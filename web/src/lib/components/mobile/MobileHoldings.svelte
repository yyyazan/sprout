<script>
  // Mobile Holdings pane — the sidebar rail rebuilt for a full phone column:
  // richer rows (price + live move + value + weight), D/W move window, and the
  // watchlist underneath. Same stores and live-momentum fallback as the rail.
  import { holdings, moves, watchlist, openStock, cardToHolding } from '$lib/stores.js';

  let win = $state('day');   // 'day' | 'wk'

  const rows = $derived(
    [...($holdings ?? [])].sort((a, b) => (b.market_value ?? 0) - (a.market_value ?? 0))
  );

  // live move (fresh /api/momentum) with the frozen dashboard payload as fallback
  const moveOf = (c, w) => {
    const live = $moves[c.ticker];
    const v = live ? (w === 'day' ? live.day_pct : live.week_pct) : (w === 'day' ? c.day_pct : c.week_pct);
    return v ?? 0;
  };
  const pct = (n) => (n >= 0 ? '+' : '−') + Math.abs(n ?? 0).toFixed(2) + '%';
  const wt = (n) => (n ?? 0).toFixed(1) + '%';
  const usd = (n) => {
    if (n == null) return '—';
    const a = Math.abs(n);
    if (a >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'k';
    return '$' + Math.round(n);
  };
  const px = (n) => (n == null ? '—' : '$' + n.toFixed(2));

  function open(c) {
    openStock({ ticker: c.ticker, name: c.company_name, holding: cardToHolding(c) });
  }
</script>

<div class="mho-head">
  <span class="mho-title">Holdings</span>
  <div class="mho-win" role="group" aria-label="move window">
    <button class="btn btn-mono mho-btn" class:on={win === 'day'} onclick={() => (win = 'day')}>D</button>
    <button class="btn btn-mono mho-btn" class:on={win === 'wk'} onclick={() => (win = 'wk')}>W</button>
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
          <b class="mho-sym">{c.ticker}</b>
          <span class="mho-name">{c.company_name}</span>
        </span>
        <span class="mho-line mho-sub">
          <span class="mho-val">{usd(c.market_value)} · {wt(c.position_pct)}</span>
        </span>
      </span>
      <span class="mho-right">
        <span class="mho-px">{px(c.current_price)}</span>
        <span class="mho-day {mv >= 0 ? 'up' : 'down'}">{pct(mv)}</span>
      </span>
    </button>
  {/each}
{/if}

{#if $watchlist?.length}
  <div class="mho-wl-head">Watchlist</div>
  {#each $watchlist as w (w.ticker)}
    <button class="mho-row" onclick={() => openStock({ ticker: w.ticker, name: w.name, holding: null })}>
      <span class="mho-main">
        <span class="mho-line">
          <b class="mho-sym">{w.ticker}</b>
          <span class="mho-name">{w.name}</span>
        </span>
      </span>
      <span class="mho-right">
        <span class="mho-px">{w.price != null ? '$' + w.price.toFixed(2) : '—'}</span>
        <span class="mho-day {(w.dayPct ?? 0) >= 0 ? 'up' : 'down'}">{w.dayPct != null ? pct(w.dayPct) : '—'}</span>
      </span>
    </button>
  {/each}
{/if}

<style>
  .mho-head { display: flex; align-items: center; justify-content: space-between;
    padding: calc(12px + env(safe-area-inset-top)) 2px 8px; }
  .mho-title { font-family: var(--sans); font-size: 9.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }
  .mho-win { display: inline-flex; gap: 2px; }
  .mho-win :global(.mho-btn) { font-size: 10px; padding: 4px 12px; }

  .mho-wl-head { margin-top: 18px; padding: 10px 2px 8px; font-family: var(--sans); font-size: 9.5px;
    font-weight: 700; text-transform: uppercase; letter-spacing: .12em; color: var(--muted);
    border-top: 1.5px solid color-mix(in srgb, var(--ink) 13%, transparent); }

  .mho-empty { padding: 14px 4px; font-family: var(--mono); font-size: 12px; color: var(--muted); }

  /* ~56px touch rows: identity left, price + move right */
  .mho-row { width: 100%; display: flex; align-items: center; gap: 12px; min-height: 56px;
    padding: 10px 4px; border: 0; border-bottom: var(--bw) solid var(--hairline); border-radius: 0;
    background: transparent; cursor: pointer; text-align: left; font: inherit; color: var(--ink); }
  .mho-row:active { background: var(--hover); }

  .mho-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
  .mho-line { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
  .mho-sym { font-family: var(--mono); font-weight: 700; font-size: 15px; color: var(--ink); flex: 0 0 auto; }
  .mho-name { font-family: var(--sans); font-size: 12px; color: var(--muted); min-width: 0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mho-val { font-family: var(--mono); font-size: 11px; color: var(--muted); font-variant-numeric: tabular-nums; }

  .mho-right { flex: 0 0 auto; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
  .mho-px { font-family: var(--mono); font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .mho-day { font-family: var(--mono); font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .up { color: var(--gain); }
  .down { color: var(--loss); }
</style>
