<script>
  // Mobile Home pane: garden hero (the brand moment) → KPI duo → portfolio
  // chart → dividend/allocation rings → market pulse. The desktop's research
  // chat and card fan are intentionally absent on the phone.
  import GardenView from '../GardenView.svelte';
  import BalanceCard from '../BalanceCard.svelte';
  import PnlCard from '../PnlCard.svelte';
  import PortfolioChart from '../PortfolioChart.svelte';
  import DividendRing from '../DividendRing.svelte';
  import AllocationRing from '../AllocationRing.svelte';
  import MarketPulse from '../MarketPulse.svelte';
  import { theme, toggleTheme } from '$lib/theme.js';

  let { d, garden } = $props();
</script>

<!-- full-bleed hero; the greeting overlay clears the iOS status bar (standalone
     runs content under it via black-translucent) -->
<div class="mh-hero">
  <GardenView positions={garden.positions} period={garden.period} />
  <div class="mh-hero-overlay">
    <div class="greeting-title">{d.greeting}</div>
    <button class="mh-theme" onclick={toggleTheme} aria-label="Toggle light/dark theme">
      {$theme === 'dark' ? '☀' : '☾'}
    </button>
  </div>
</div>

<div class="mh-kpis">
  <BalanceCard total={d.kpis.portfolio_value} equities={d.kpis.equities} />
  <PnlCard total={d.kpis.total_pnl} realized={d.kpis.realized_pnl} unrealized={d.kpis.unrealized_pnl} />
</div>

<div class="mh-chart">
  <PortfolioChart equity={d.equity_curve} spy={d.spy_curve} twr={d.twr} netInvested={d.net_invested} />
</div>

<div class="mh-rings">
  <DividendRing data={d.dividends} holdings={d.cards} />
  <AllocationRing holdings={d.cards.filter((c) => !c.is_joker)} />
</div>

<MarketPulse />

<style>
  .mh-hero { position: relative; margin: 0 -14px 14px; }
  .mh-hero-overlay { position: absolute; top: 0; left: 0; right: 0; z-index: 2; pointer-events: none;
    display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
    padding: calc(12px + env(safe-area-inset-top)) 16px 0; }
  /* overlay is pointer-transparent so the garden stays scrollable; the theme
     button opts back in */
  .mh-theme { pointer-events: auto; width: 30px; height: 30px; display: grid; place-items: center;
    cursor: pointer; font-size: 14px; line-height: 1; color: #1a1a1a; background: transparent;
    border: 1px solid rgba(26, 26, 26, .4); border-radius: 999px; }

  .mh-kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
  .mh-kpis :global(.glass-card) { padding: 14px 16px; }

  /* PortfolioChart is built for the desktop stage (split header row, fixed
     --title-h, 440px chart). Phone overrides: single header (the earnings half
     stays desktop-only), self-sized header, shorter chart box. */
  .mh-chart { margin-bottom: 14px; }
  .mh-chart :global(.pc-head-row) { grid-template-columns: 1fr; gap: 0; }
  .mh-chart :global(.pc-head-earn) { display: none; }
  .mh-chart :global(.pc-head-w) { height: auto; min-height: 0; }
  .mh-chart :global(.pc-chart-w) { flex-basis: 300px; height: 300px; }

  .mh-rings { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: center;
    margin-bottom: 14px; }

  @media (prefers-reduced-motion: reduce) { .mh-theme { transition: none; } }
</style>
