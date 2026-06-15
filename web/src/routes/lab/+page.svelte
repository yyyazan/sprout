<script>
  // Lab — the contained retail-quant learning bench. Curriculum + one card per
  // discipline; "live" cards run against real data (cached prices, the actual
  // portfolio), "soon" cards are scaffolds with their build path written down.
  // Desktop-first like the planned Research surface; nothing here ever places
  // a broker order (paper trading is the hard ceiling).
  import LabCard from '$lib/lab/LabCard.svelte';
  import CurriculumLab from '$lib/lab/CurriculumLab.svelte';
  import FactorLab from '$lib/lab/FactorLab.svelte';
  import BacktestLab from '$lib/lab/BacktestLab.svelte';
  import PayoffLab from '$lib/lab/PayoffLab.svelte';
</script>

<div class="content">
  <div class="page-title">Lab</div>
  <p class="lab-sub">where strategies go to be disproven — backtest, measure, and only then believe</p>

  <div class="lab-grid">
    <LabCard title="Curriculum" status="live"
      blurb="The path, in order. Tick things off as they click.">
      <CurriculumLab />
    </LabCard>

    <LabCard title="Factors · CAPM" status="live"
      blurb="Your actual portfolio regressed against SPY — how much is market, how much is you.">
      <FactorLab />
    </LabCard>

    <LabCard title="Backtest · SMA crossover" status="live" wide
      blurb="The simplest systematic strategy there is, on real price history. Spoiler: holding usually wins.">
      <BacktestLab />
    </LabCard>

    <LabCard title="Options · payoff" status="live"
      blurb="Every option position is a shape. Learn the four basic ones before touching the greeks.">
      <PayoffLab />
    </LabCard>

    <LabCard title="Screener" status="soon"
      blurb="Filter the market by factor characteristics instead of vibes.">
      <div class="lab-stub">
        {#each ['P/E < 15', 'mom 6m > 0', 'mkt cap > $1B', 'div yield > 2%'] as chip (chip)}
          <span class="lab-chip">{chip}</span>
        {/each}
      </div>
      <div class="lab-plan">build: yfinance bulk fundamentals → DuckDB over the Parquet store → rank by factor score</div>
    </LabCard>

    <LabCard title="Auto-trading · paper" status="soon"
      blurb="Signals become orders only on paper. The Lab never touches a broker — that rule doesn't bend.">
      <ol class="lab-steps">
        <li>strategy emits signal <em>(backtest above)</em></li>
        <li>position sizing caps it <em>(Kelly / vol target)</em></li>
        <li>paper ledger records the fill <em>(reuses the trades schema)</em></li>
        <li>weekly review vs benchmark <em>(factors panel)</em></li>
      </ol>
      <div class="lab-plan">build: paper_trades table + a scheduled signal run · kill switch before anything else</div>
    </LabCard>
  </div>
</div>

<style>
  .lab-sub { margin: -6px 0 18px; font-family: var(--mono); font-size: 11.5px; color: var(--muted); }

  .lab-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start;
    max-width: 1100px; }
  @media (max-width: 1100px) { .lab-grid { grid-template-columns: 1fr; } }

  .lab-stub { display: flex; flex-wrap: wrap; gap: 6px; }
  .lab-chip { font-family: var(--mono); font-size: 10.5px; font-weight: 700; color: var(--muted);
    padding: 4px 9px; border: var(--bw) dashed var(--muted); border-radius: 999px; opacity: .8; }

  .lab-steps { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 5px;
    font-family: var(--sans); font-size: 12px; color: var(--text); }
  .lab-steps em { font-style: normal; color: var(--muted); }

  .lab-plan { font-family: var(--mono); font-size: 10.5px; color: var(--muted);
    border-top: var(--bw) solid var(--hairline); padding-top: 8px; }
</style>
