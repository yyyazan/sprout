<script>
  // Mobile Home pane: garden hero (the brand moment) with the profile + theme
  // controls → search strip (the desktop stage's, folded in: idle button or
  // live input, results take the pane over) → KPI duo → portfolio chart →
  // month glance of the top holdings → rings → market pulse.
  import GardenView from '../GardenView.svelte';
  import BalanceCard from '../BalanceCard.svelte';
  import PnlCard from '../PnlCard.svelte';
  import PortfolioChart from '../PortfolioChart.svelte';
  import DividendRing from '../DividendRing.svelte';
  import AllocationRing from '../AllocationRing.svelte';
  import MarketPulse from '../MarketPulse.svelte';
  import TickerBadge from '../TickerBadge.svelte';
  import Sparkline from '../Sparkline.svelte';
  import MobileSearch from './MobileSearch.svelte';
  import ProfileMenu from '../ProfileMenu.svelte';
  import { theme, toggleTheme } from '$lib/theme.js';
  import { moves, holdings, portfolioDayMove, allTimeReturn, openStock, cardToHolding } from '$lib/stores.js';
  import { SHOW_GARDEN } from '$lib/config.js';

  let { d, garden, onSeeAll } = $props();
  let menuOpen = $state(false);
  const dayMove = $derived(d ? portfolioDayMove(d.cards, $moves) : { gain: null, pct: null });
  const allTime = $derived(allTimeReturn(d?.twr));

  // ── search: the strip owns the query; MobileSearch renders the results ──
  let searching = $state(false);
  let q = $state('');
  let input;
  function openSearch() { searching = true; queueMicrotask(() => input?.focus()); }
  function closeSearch() { searching = false; q = ''; }

  // ── month glance: top 5 by weight, each with its 21-session sparkline ──
  const GLANCE = 5;
  const glance = $derived(
    [...($holdings ?? d?.cards?.filter((c) => !c.is_joker) ?? [])]
      .sort((a, b) => (b.market_value ?? 0) - (a.market_value ?? 0))
      .slice(0, GLANCE)
  );
  const pct = (n) => n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + '%';
  const open = (c) => openStock({ ticker: c.ticker, name: c.company_name, holding: cardToHolding(c) });
</script>

<!-- full-bleed hero; the overlay clears the iOS status bar (standalone runs
     content under it via black-translucent) -->
<div class="mh-hero" class:mh-hero--flat={!SHOW_GARDEN}>
  {#if SHOW_GARDEN}
    <GardenView positions={garden.positions} period={garden.period} />
  {/if}
  <div class="mh-hero-overlay">
    <div class="greeting-title">{d.greeting}</div>
    <div class="mh-tools">
      <button class="mh-tool" onclick={toggleTheme} aria-label="Toggle light/dark theme">
        {$theme === 'dark' ? '☀' : '☾'}
      </button>
      <div class="mh-profile">
        <button class="mh-tool" type="button" aria-label="Account" aria-haspopup="menu"
          aria-expanded={menuOpen} onclick={() => (menuOpen = !menuOpen)}>
          <svg class="mh-person" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <circle cx="12" cy="8.5" r="3.6" /><path d="M5 20 c0 -4 3.2 -6.2 7 -6.2 s7 2.2 7 6.2" />
          </svg>
        </button>
        <ProfileMenu open={menuOpen} onClose={() => (menuOpen = false)} />
      </div>
    </div>
  </div>
</div>

{#if searching}
  <div class="strip strip-active">
    <span class="strip-icon" aria-hidden="true">⌕</span>
    <input bind:this={input} bind:value={q} type="search" placeholder="Search"
      autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
      enterkeyhint="search" aria-label="Search stocks" />
    <button class="strip-esc" onclick={closeSearch}>Cancel</button>
  </div>
  <MobileSearch {q} />
{:else}
  <button class="strip strip-idle" onclick={openSearch}>
    <span class="strip-icon" aria-hidden="true">⌕</span>
    <span class="strip-ph">Search</span>
  </button>
{/if}

<!-- the home body stays mounted under an open search so the chart never re-inits -->
<div class="mh-body" class:hidden={searching}>
  <div class="mh-kpis">
    <BalanceCard total={d.kpis.portfolio_value} equities={d.kpis.equities}
      dayGain={dayMove.gain} dayPct={dayMove.pct} ret={allTime.ret} vsSpy={allTime.vsSpy} />
    <PnlCard total={d.kpis.total_pnl} realized={d.kpis.realized_pnl} unrealized={d.kpis.unrealized_pnl} />
  </div>

  <div class="mh-chart">
    <PortfolioChart equity={d.equity_curve} spy={d.spy_curve} twr={d.twr} netInvested={d.net_invested} />
  </div>

  {#if glance.length}
    <section class="mh-glance">
      <div class="mh-glance-head">
        <span class="mh-title">Holdings, past month</span>
        <button class="btn btn-sm btn-quiet" onclick={onSeeAll}>See all</button>
      </div>
      {#each glance as c (c.ticker)}
        {@const m = $moves[c.ticker]}
        {@const mp = m?.month_pct}
        <button class="mh-row" onclick={() => open(c)}>
          <TickerBadge sym={c.ticker} />
          <span class="mh-name">{c.company_name}</span>
          <span class="mh-move {(mp ?? 0) >= 0 ? 'up' : 'down'}">
            <Sparkline values={m?.spark ?? []} />
            <span class="mh-pct">{pct(mp)}</span>
          </span>
        </button>
      {/each}
    </section>
  {/if}

  <div class="mh-rings">
    <DividendRing data={d.dividends} holdings={d.cards} />
    <AllocationRing holdings={d.cards.filter((c) => !c.is_joker)} />
  </div>

  <MarketPulse />
</div>

<style>
  .mh-hero { position: relative; margin: 0 -14px 14px; }
  .mh-hero-overlay { position: absolute; top: 0; left: 0; right: 0; z-index: 2; pointer-events: none;
    display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
    /* Safari's own top blur/gradient (standalone status bar and the in-tab
       chrome alike) reaches a bit past the safe-area inset itself — enough to
       clip through the top half of the 30px profile circle at the old 18px.
       +15px (half that circle) clears it. */
    padding: calc(33px + env(safe-area-inset-top)) 16px 0; }
  /* overlay is pointer-transparent so the garden stays scrollable; the tools opt back in */
  .mh-tools { display: flex; gap: 8px; pointer-events: auto; }
  .mh-profile { position: relative; display: flex; }
  .mh-tool { width: 30px; height: 30px; display: grid; place-items: center; cursor: pointer;
    font: inherit; font-size: 14px; line-height: 1; color: #1a1a1a; background: transparent;
    border: var(--bw) solid rgba(26, 26, 26, .4); border-radius: 999px; padding: 0; }
  .mh-person { width: 17px; height: 17px; display: block; }

  /* garden hidden (SHOW_GARDEN=false): overlay drops into flow, text/icons pick
     up theme color since there's no garden sky underneath anymore */
  .mh-hero--flat .mh-hero-overlay { position: static; pointer-events: auto; padding-bottom: 12px; }
  .mh-hero--flat .greeting-title { color: var(--text); }
  .mh-hero--flat .mh-tool { color: var(--text); border-color: color-mix(in srgb, var(--text) 40%, transparent); }

  .mh-body { display: flex; flex-direction: column; gap: 14px; margin-top: 14px; }
  .mh-body.hidden { display: none; }

  .mh-kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; --card-pad: 14px 16px; }

  /* PortfolioChart fills its stage on desktop; on the phone give it a fixed box */
  .mh-chart :global(.pc-chart-w) { flex: 0 0 300px; height: 300px; }

  /* month glance — the sidebar row grammar: badge, name, then the move */
  .mh-glance-head { display: flex; align-items: center; justify-content: space-between; padding: 4px 0 2px; }
  .mh-title { font-size: var(--fs-title); font-weight: 600; color: var(--ink); }
  .mh-row { width: 100%; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px;
    min-height: 48px; padding: 8px 0; border: 0; border-bottom: var(--bw) solid var(--hairline); border-radius: 0;
    background: transparent; cursor: pointer; text-align: left; font: inherit; color: var(--ink); }
  .mh-row:active { background: var(--hover); }
  .mh-name { min-width: 0; font-size: var(--fs-body); font-weight: 500; color: var(--muted);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mh-move { display: flex; align-items: center; gap: 10px; }
  .mh-pct { min-width: 64px; text-align: right; font-family: var(--num); font-size: var(--fs-body); font-weight: 500;
    font-variant-numeric: tabular-nums; }
  .up { color: var(--gain-ink); }
  .down { color: var(--loss-ink); }

  .mh-rings { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: center; }
</style>
