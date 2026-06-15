<script>
  // CAPM regression of the real portfolio vs SPY (/api/lab/factors) with a
  // plain-English read on each number. First rung of the factor ladder —
  // Fama-French 3/5-factor is the planned upgrade once the Ken French data
  // library is wired in.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let d = $state(null);
  let error = $state(null);
  onMount(async () => {
    try {
      const r = await api.labFactors();
      if (r?.ok) d = r; else error = r?.error ?? 'failed';
    } catch { error = 'failed to load'; }
  });

  const betaRead = (b) =>
    b > 1.2 ? 'amplifies market moves — drawdowns will be bigger than SPY’s'
    : b < 0.8 ? 'muted vs the market — defensive tilt'
    : 'moves roughly with the market';
  const alphaRead = (a) =>
    a > 2 ? 'positive — but check R² before celebrating; low R² alpha is mostly noise'
    : a < -2 ? 'negative — the market explains your returns, minus a drag'
    : 'about zero — the honest retail baseline';
  const r2Read = (r) =>
    r > 0.8 ? 'the market explains nearly everything — you basically hold beta'
    : r < 0.4 ? 'mostly idiosyncratic — single-name risk dominates'
    : 'a mix of market and stock-specific risk';
</script>

{#if d}
  <div class="fl-grid">
    <div class="fl-cell">
      <span class="fl-num">{d.beta}</span>
      <span class="fl-lbl">beta</span>
      <span class="fl-read">{betaRead(d.beta)}</span>
    </div>
    <div class="fl-cell">
      <span class="fl-num" class:up={d.alpha_annual_pct > 0} class:down={d.alpha_annual_pct < 0}>
        {d.alpha_annual_pct > 0 ? '+' : ''}{d.alpha_annual_pct}%</span>
      <span class="fl-lbl">alpha / yr</span>
      <span class="fl-read">{alphaRead(d.alpha_annual_pct)}</span>
    </div>
    <div class="fl-cell">
      <span class="fl-num">{d.r_squared}</span>
      <span class="fl-lbl">R²</span>
      <span class="fl-read">{r2Read(d.r_squared)}</span>
    </div>
  </div>
  <div class="fl-row">
    <span>sharpe {d.sharpe_portfolio} <em>vs SPY {d.sharpe_spy}</em></span>
    <span>max drawdown {d.max_dd_portfolio_pct}% <em>vs SPY {d.max_dd_spy_pct}%</em></span>
    <span><em>{d.n_days} trading days</em></span>
  </div>
  <div class="fl-next">next: Fama-French 3-factor — how much "alpha" is just size/value exposure</div>
{:else if error}
  <div class="fl-err">{error}</div>
{:else}
  <div class="fl-err">regressing…</div>
{/if}

<style>
  .fl-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .fl-cell { display: flex; flex-direction: column; gap: 3px; padding: 10px 12px;
    border: var(--bw) solid var(--hairline); border-radius: var(--r); min-width: 0; }
  .fl-num { font-family: var(--mono); font-size: 22px; font-weight: 800; color: var(--ink);
    font-variant-numeric: tabular-nums; }
  .fl-num.up { color: var(--gain); }
  .fl-num.down { color: var(--loss); }
  .fl-lbl { font-family: var(--mono); font-size: 9.5px; font-weight: 700; color: var(--muted);
    text-transform: uppercase; letter-spacing: .1em; }
  .fl-read { font-family: var(--sans); font-size: 11px; line-height: 1.45; color: var(--muted); }

  .fl-row { display: flex; flex-wrap: wrap; gap: 6px 18px; font-family: var(--mono); font-size: 11px;
    font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; }
  .fl-row em { font-style: normal; color: var(--muted); font-weight: 500; }

  .fl-next { font-family: var(--mono); font-size: 10.5px; color: var(--muted);
    border-top: var(--bw) solid var(--hairline); padding-top: 8px; }
  .fl-err { font-family: var(--mono); font-size: 12px; color: var(--muted); }

  @media (max-width: 700px) { .fl-grid { grid-template-columns: 1fr; } }
</style>
