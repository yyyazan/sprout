<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { holdings, moves, loadHoldings, startMomentum, openStock, openSearch, cardToHolding, watchlist, loadWatchlist } from '$lib/stores.js';
  import { theme, toggleTheme } from '$lib/theme.js';
  import TickerBadge from './TickerBadge.svelte';

  const NAV = [
    { label: 'home', path: '/', glyph: '❖' },
    { label: 'log', path: '/trades', glyph: '⊞' },
    { label: 'lab', path: '/lab', glyph: '⚗' }
  ];
  function isActive(pathname, path) {
    return path === '/' ? pathname === '/' : pathname.startsWith(path);
  }
  onMount(() => { loadHoldings(); startMomentum(); loadWatchlist(); });

  let win = $state('day');   // 'day' | 'wk' — which move window the strips encode

  // Rail rows: every holding, heaviest position first (stable order so live
  // updates don't make rows jump around).
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

  function open(c) {
    openStock({ ticker: c.ticker, name: c.company_name, holding: cardToHolding(c) });
  }
</script>

<aside class="sidebar">
  <div class="brand brand-row">
    <span class="brand-title">sprout</span>
    <button class="theme-btn" onclick={toggleTheme} aria-label="Toggle light/dark theme" title="{$theme === 'dark' ? 'Light' : 'Dark'} mode">
      {$theme === 'dark' ? '☀' : '☾'}
    </button>
  </div>

  <nav class="nav">
    {#each NAV as item}
      <a href={item.path} class="nav-link" class:active={isActive($page.url.pathname, item.path)}>
        <div class="nav-item">
          <span class="nav-icon">{item.glyph}</span>
          <span class="nav-label">{item.label}</span>
        </div>
      </a>
    {/each}
  </nav>

  <button class="btn btn-line rail-search" onclick={() => openSearch()}>
    <span class="rs-icon" aria-hidden="true">⌕</span>
    <span class="rs-label">search</span>
    <kbd>⌘K</kbd>
  </button>

  <div class="rail-head">
    <span class="rh-title">Holdings</span>
    <div class="rh-win" role="group" aria-label="move window">
      <button class="btn btn-mono rh-btn" class:on={win === 'day'} onclick={() => (win = 'day')}>D</button>
      <button class="btn btn-mono rh-btn" class:on={win === 'wk'} onclick={() => (win = 'wk')}>W</button>
    </div>
  </div>

  <div class="rail">
    {#if $holdings === null}
      <div class="rail-empty">Loading…</div>
    {:else if rows.length === 0}
      <div class="rail-empty">No holdings yet.</div>
    {:else}
      {#each rows as c, i (c.ticker)}
        {@const mv = moveOf(c, win)}
        <button class="row" style="--i:{Math.min(i, 16)}" onclick={() => open(c)}>
          <span class="r-main">
            <span class="r-line">
              <TickerBadge sym={c.ticker} />
              <span class="r-day pct-pill {mv >= 0 ? 'up' : 'down'}">{pct(mv)}</span>
            </span>
            <span class="r-line r-sub">
              <span class="r-val">{usd(c.market_value)}</span>
              <span class="r-wt">{wt(c.position_pct)}</span>
            </span>
          </span>
        </button>
      {/each}
    {/if}

    {#if $watchlist?.length}
      <div class="wl-head">Watchlist</div>
      {#each $watchlist as w (w.ticker)}
        {@const wv = win === 'day' ? w.dayPct : w.weekPct}
        <button class="row wl-row" onclick={() => openStock({ ticker: w.ticker, name: w.name, holding: null })}>
          <span class="r-main">
            <span class="r-line">
              <TickerBadge sym={w.ticker} />
              <span class="r-day pct-pill {(wv ?? 0) >= 0 ? 'up' : 'down'}">{wv != null ? pct(wv) : '—'}</span>
            </span>
            <span class="r-line r-sub">
              <span class="r-val">{w.price != null ? '$' + w.price.toFixed(2) : '—'}</span>
            </span>
          </span>
        </button>
      {/each}
    {/if}
  </div>
</aside>

<style>
  .brand-row { display: flex; align-items: center; justify-content: space-between; }
  .theme-btn { width: 28px; height: 28px; display: grid; place-items: center; cursor: pointer;
    font-size: 14px; line-height: 1; color: var(--muted); background: transparent;
    border: var(--bw) solid var(--hairline); border-radius: 999px;
    transition: color .12s ease, border-color .12s ease, transform .12s ease; }
  .theme-btn:hover { color: var(--ink); border-color: var(--ink); transform: rotate(20deg); }

  /* rail search rides the global .btn .btn-line pill; layout extras only */
  .rail-search { width: 100%; justify-content: flex-start; margin: 12px 0 4px; padding: 8px 14px; }
  .rail-search .rs-icon { font-size: 14px; color: var(--muted); }
  .rail-search .rs-label { flex: 1; text-align: left; }
  .rail-search kbd { font-family: var(--mono); font-size: 9.5px; color: var(--muted);
    border: 1px solid var(--hairline); border-radius: 4px; padding: 1px 4px; }
  .rail-search:active kbd, .rail-search:active .rs-icon { color: var(--paper); }

  /* ── rail header: title + D/W move-window toggle (mini system pills) ── */
  .rail-head { display: flex; align-items: center; justify-content: space-between; margin: 14px 4px 7px; }
  .rh-title { font-family: var(--sans); font-size: 9.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }
  .rh-win { display: inline-flex; gap: 2px; }
  .rh-win :global(.rh-btn) { font-size: 9px; padding: 2px 8px; }

  /* scrollable holdings list — keep it scrollable but hide the scrollbar chrome */
  .rail { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; padding-bottom: 8px;
    scrollbar-width: none; -ms-overflow-style: none; }
  .rail::-webkit-scrollbar { width: 0; height: 0; display: none; }
  .rail-empty { padding: 10px 6px; font-family: var(--mono); font-size: 11px; color: var(--muted); }

  /* ── watched (non-held) tickers: same rows, no growth strip ── */
  .wl-head { margin: 14px 4px 5px; padding-top: 10px; font-family: var(--sans); font-size: 9.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em; color: var(--muted);
    border-top: 1.5px solid color-mix(in srgb, var(--ink) 13%, transparent); }
  .wl-row { animation: none; }

  /* ── a holding row: two stat lines. neo-brutalist states: static ink border on
     hover, full ink inversion while pressed. no sweeps, no washes. ── */
  .row { display: flex; align-items: stretch; gap: 10px; padding: 9px 12px;
    border: var(--bw) solid transparent; border-radius: var(--r);
    background: transparent; cursor: pointer; text-align: left; font: inherit;
    transition: border-color .12s ease, background .12s ease;
    animation: rise .42s cubic-bezier(.2, .8, .3, 1) backwards; animation-delay: calc(var(--i) * 26ms); }
  .row:hover { border-color: var(--ink); }
  .row:active { background: var(--ink); border-color: var(--ink); }
  .row:active .r-sym { color: var(--paper); }
  .row:active .r-val, .row:active .r-wt { color: var(--paper); opacity: .75; }

  .r-main { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; gap: 3px; }
  .r-line { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .r-sym { font-family: var(--mono); font-weight: 700; font-size: 13px; color: var(--ink); }
  .r-day { font-family: var(--mono); font-weight: 700; font-size: 12px; font-variant-numeric: tabular-nums; }
  .r-sub { opacity: .92; }
  .r-val { font-family: var(--mono); font-size: 11px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .r-wt { font-family: var(--mono); font-size: 10px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .up { color: var(--gain); }
  .down { color: var(--loss); }

  @keyframes rise { from { opacity: 0; transform: translateY(7px); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) {
    .row { animation: none; }
  }

  /* On mobile the sidebar collapses to a top nav bar — the rail would be huge there. */
  @media (max-width: 700px) {
    .rail, .rail-head, .rail-search { display: none; }
  }
</style>
