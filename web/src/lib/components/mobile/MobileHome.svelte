<script>
  // Mobile Home pane: garden hero (the brand moment) with the profile + theme
  // controls → search strip (the desktop stage's, folded in: idle button or
  // live input, results take the pane over) → KPI duo → portfolio chart →
  // Drivers for the chart's window → rings → market pulse.
  import GardenView from '../GardenView.svelte';
  import BalanceCard from '../BalanceCard.svelte';
  import PnlCard from '../PnlCard.svelte';
  import PortfolioChart from '../PortfolioChart.svelte';
  import DividendRing from '../DividendRing.svelte';
  import AllocationRing from '../AllocationRing.svelte';
  import MarketPulse from '../MarketPulse.svelte';
  import DriversCard from '../DriversCard.svelte';
  import MobileSearch from './MobileSearch.svelte';
  import ProfileMenu from '../ProfileMenu.svelte';
  import { theme, toggleTheme } from '$lib/theme.js';
  import { moves, portfolioDayMove, allTimeReturn } from '$lib/stores.js';
  import { SHOW_GARDEN } from '$lib/config.js';

  let { d, garden } = $props();
  let menuOpen = $state(false);
  const dayMove = $derived(d ? portfolioDayMove(d.cards, $moves) : { gain: null, pct: null });
  const allTime = $derived(allTimeReturn(d?.twr));

  // ── search: the strip owns the query; MobileSearch renders the results ──
  let searching = $state(false);
  let q = $state('');
  let input;
  function openSearch() { searching = true; queueMicrotask(() => input?.focus()); }
  function closeSearch() { searching = false; q = ''; }

  // the chart's window, which Drivers explains (range, pan)
  let win = $state(null);
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
        {#if $theme === 'dark'}
          <svg class="mh-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4" />
          </svg>
        {:else}
          <svg class="mh-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
            <path d="M19.5 14.5A7.5 7.5 0 0 1 9.5 4.5a7.5 7.5 0 1 0 10 10Z" />
          </svg>
        {/if}
      </button>
      <div class="mh-profile">
        <button class="mh-tool" type="button" aria-label="Account" aria-haspopup="menu"
          aria-expanded={menuOpen} onclick={() => (menuOpen = !menuOpen)}>
          <svg class="mh-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
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
    <span class="strip-icon" aria-hidden="true"></span>
    <input bind:this={input} bind:value={q} type="search" placeholder="Search"
      autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
      enterkeyhint="search" aria-label="Search stocks" />
    <button class="strip-esc" onclick={closeSearch}>Cancel</button>
  </div>
  <MobileSearch {q} />
{:else}
  <button class="strip strip-idle" onclick={openSearch}>
    <span class="strip-icon" aria-hidden="true"></span>
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

  <div class="chart-widget">
    <PortfolioChart equity={d.equity_curve} spy={d.spy_curve} twr={d.twr} netInvested={d.net_invested}
      onwindow={(w) => (win = w)} />
  </div>

  <DriversCard drivers={d.drivers} {win} variant="list" />

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
  .mh-icon { width: 17px; height: 17px; display: block; }

  /* garden hidden (SHOW_GARDEN=false): overlay drops into flow, text/icons pick
     up theme color since there's no garden sky underneath anymore */
  .mh-hero--flat .mh-hero-overlay { position: static; pointer-events: auto; padding-bottom: 12px; }
  .mh-hero--flat .greeting-title { color: var(--text); }
  .mh-hero--flat .mh-tool { color: var(--text); border-color: color-mix(in srgb, var(--text) 40%, transparent); }

  .mh-body { display: flex; flex-direction: column; gap: 14px; margin-top: 14px; }
  .mh-body.hidden { display: none; }

  .mh-kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; --card-pad: 14px 16px; }

  .mh-rings { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: center; }
</style>
