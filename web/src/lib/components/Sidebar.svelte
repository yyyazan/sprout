<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { holdings, moves, loadHoldings, startMomentum, openStock, cardToHolding, watchlist, loadWatchlist } from '$lib/stores.js';
  import { theme, toggleTheme } from '$lib/theme.js';
  import TickerBadge from './TickerBadge.svelte';
  import Sparkline from './Sparkline.svelte';
  import ProfileMenu from './ProfileMenu.svelte';

  let menuOpen = $state(false);

  const NAV = [
    { label: 'Home', path: '/' },
    { label: 'Log', path: '/trades' },
  ];
  function isActive(pathname, path) {
    return path === '/' ? pathname === '/' : pathname.startsWith(path);
  }
  onMount(() => { loadHoldings(); startMomentum(); loadWatchlist(); });

  const WINS = [['day', 'D'], ['wk', 'W'], ['mo', 'M']];
  let win = $state('mo');   // which move window the pills encode; the sparkline is always the past month

  // Rail rows: every holding, heaviest position first (stable order so live
  // updates don't make rows jump around).
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
  // the sparkline's own direction colors it — first close to spot
  const sparkUp = (sp) => !sp?.length || sp[sp.length - 1] >= sp[0];
  const pct = (n) => n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + '%';
  const px = (n) => n == null ? '—' : '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
    <div class="brand-actions">
      <div class="profile-wrap">
        <button class="btn-icon profile" type="button" aria-label="Account" aria-haspopup="menu"
          aria-expanded={menuOpen} onclick={() => (menuOpen = !menuOpen)}>
          <svg class="person" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <circle cx="12" cy="8.5" r="3.6" /><path d="M5 20 c0 -4 3.2 -6.2 7 -6.2 s7 2.2 7 6.2" />
          </svg>
        </button>
        <ProfileMenu open={menuOpen} onClose={() => (menuOpen = false)} />
      </div>
      <button class="btn-icon theme-btn" onclick={toggleTheme} aria-label="Toggle light/dark theme" title="{$theme === 'dark' ? 'Light' : 'Dark'} mode">
        {$theme === 'dark' ? '☀' : '☾'}
      </button>
    </div>
  </div>

  <nav class="nav">
    {#each NAV as item}
      <a href={item.path} class="nav-link" class:active={isActive($page.url.pathname, item.path)}>
        <div class="nav-item"><span class="nav-label">{item.label}</span></div>
      </a>
    {/each}
  </nav>

  <div class="rail-head">
    <span class="rh-title">Holdings</span>
    <div class="rh-win" role="group" aria-label="move window">
      {#each WINS as [k, label] (k)}
        <button class="btn btn-mono rh-btn" class:on={win === k} onclick={() => (win = k)}>{label}</button>
      {/each}
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
        {@const live = $moves[c.ticker]}
        <button class="row" style="--i:{Math.min(i, 16)}" onclick={() => open(c)}>
          <span class="r-col r-id">
            <TickerBadge sym={c.ticker} />
            <span class="r-sub"><span class="r-val">{usd(c.market_value)}</span><span class="r-wt">{wt(c.position_pct)}</span></span>
          </span>
          <span class="r-spark {sparkUp(live?.spark) ? 'up' : 'down'}">
            <Sparkline values={live?.spark ?? []} width={56} height={20} />
          </span>
          <span class="r-col r-fig">
            <span class="r-px">{px(live?.spot ?? c.current_price)}</span>
            <span class="r-day pct-pill {(mv ?? 0) >= 0 ? 'up' : 'down'}">{pct(mv)}</span>
          </span>
        </button>
      {/each}
    {/if}

    {#if $watchlist?.length}
      <div class="wl-head">Watchlist</div>
      {#each $watchlist as w (w.ticker)}
        {@const wv = win === 'day' ? w.dayPct : win === 'wk' ? w.weekPct : null}
        <button class="row wl-row" onclick={() => openStock({ ticker: w.ticker, name: w.name, holding: null })}>
          <span class="r-col r-id"><TickerBadge sym={w.ticker} /></span>
          <span class="r-spark"></span>
          <span class="r-col r-fig">
            <span class="r-px">{px(w.price)}</span>
            <span class="r-day pct-pill {(wv ?? 0) >= 0 ? 'up' : 'down'}">{pct(wv)}</span>
          </span>
        </button>
      {/each}
    {/if}
  </div>

  <!-- foot: just the design link now that profile lives up in the brand row -->
  <div class="foot">
    <a href="/design" class="btn btn-sm btn-quiet" class:on={isActive($page.url.pathname, '/design')}>Design</a>
  </div>
</aside>

<style>
  .brand-row { display: flex; align-items: center; justify-content: space-between; }
  .brand-actions { display: flex; align-items: center; gap: 8px; }
  .btn-icon { width: 28px; height: 28px; display: grid; place-items: center; cursor: pointer;
    padding: 0; background: transparent; border: 0; border-radius: 999px; }
  .theme-btn { font-size: 14px; line-height: 1; color: var(--muted);
    border: var(--bw) solid var(--hairline);
    transition: color .12s ease, border-color .12s ease, transform .12s ease; }
  .theme-btn:hover { color: var(--ink); border-color: var(--ink); transform: rotate(20deg); }

  /* foot — pinned under the rail; just the quiet design link now. */
  .foot { flex: 0 0 auto; margin-top: 10px; }
  .profile-wrap { position: relative; display: flex; }
  .profile { color: var(--muted); border: var(--bw) solid var(--hairline);
    transition: color .12s ease, border-color .12s ease; }
  .profile:hover { color: var(--ink); border-color: var(--ink); }
  .profile:active { background: var(--ink); color: var(--paper); border-color: var(--ink); }
  .person { width: 16px; height: 16px; display: block; }

  /* ── rail header: section title + D/W move-window toggle ── */
  /* 13px inset = row padding (12) + its 1px border, so headings sit on the badge edge */
  .rail-head { display: flex; align-items: center; justify-content: space-between; margin: 18px 13px 6px; }
  .rh-title { font-size: var(--fs-body); font-weight: 600; color: var(--ink); }
  .rh-win { display: inline-flex; gap: 2px; }
  .rh-win :global(.rh-btn) { font-size: 10px; padding: 2px 8px; }

  /* scrollable holdings list — keep it scrollable but hide the scrollbar chrome */
  .rail { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; padding-bottom: 8px;
    scrollbar-width: none; -ms-overflow-style: none; }
  .rail::-webkit-scrollbar { width: 0; height: 0; display: none; }
  .rail-empty { padding: 10px 6px; font-size: var(--fs-body); color: var(--muted); }

  /* ── watched (non-held) tickers: same rows; the heading alone separates the lists ── */
  .wl-head { margin: 18px 13px 6px; font-size: var(--fs-body); font-weight: 600; color: var(--ink); }
  .wl-row { animation: none; }

  /* ── a holding row: two stat lines. neo-brutalist states: static ink border on
     hover, full ink inversion while pressed. no sweeps, no washes. ── */
  .row { padding: 8px 10px;
    border: var(--bw) solid transparent; border-radius: var(--r);
    background: transparent; cursor: pointer; text-align: left; font: inherit;
    transition: border-color .12s ease, background .12s ease;
    animation: rise .42s cubic-bezier(.2, .8, .3, 1) backwards; animation-delay: calc(var(--i) * 26ms); }
  .row:hover { border-color: var(--ink); }
  .row:active { background: var(--ink); border-color: var(--ink); }
  .row:active .r-val, .row:active .r-wt, .row:active .r-px { color: var(--paper); }
  .row:active .r-val, .row:active .r-wt { opacity: .75; }

  /* identity | month sparkline | figures — the sparkline column is fixed so
     every row's line sits on the same axis; the figures column right-aligns */
  .row { display: grid; grid-template-columns: minmax(0, 1fr) 56px auto; align-items: center; gap: 8px; }
  .r-col { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
  .r-id { align-items: flex-start; }
  .r-fig { align-items: flex-end; }
  .r-sub { display: flex; gap: 6px; }
  .r-spark { display: flex; justify-content: center; }
  .r-px { font-family: var(--num); font-weight: 500; font-size: var(--fs-body); color: var(--ink); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .r-day { font-family: var(--num); font-weight: 500; font-size: var(--fs-meta); font-variant-numeric: tabular-nums; }
  .r-val, .r-wt { font-family: var(--num); font-weight: 500; font-size: var(--fs-meta); color: var(--muted); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .r-spark.up { color: var(--gain-ink); }
  .r-spark.down { color: var(--loss-ink); }

  @keyframes rise { from { opacity: 0; transform: translateY(7px); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) {
    .row { animation: none; }
  }

  /* On mobile the sidebar collapses to a top nav bar — the rail would be huge there. */
  @media (max-width: 700px) {
    .rail, .rail-head, .foot { display: none; }
  }
</style>
