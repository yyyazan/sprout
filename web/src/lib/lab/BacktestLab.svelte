<script>
  // SMA-crossover backtest, the "hello world" of systematic strategies.
  // Runs server-side on the cached daily closes (/api/lab/backtest) and draws
  // strategy vs buy-and-hold. The lesson usually teaches itself: simple
  // technical rules rarely beat holding — and the costs aren't even modeled.
  import { api } from '$lib/api.js';
  import { holdings } from '$lib/stores.js';

  let ticker = $state('SPY');
  let fast = $state(20);
  let slow = $state(50);
  let years = $state(5);
  let d = $state(null);
  let error = $state(null);
  let busy = $state(false);

  async function run() {
    if (busy) return;
    busy = true; error = null;
    try {
      const r = await api.labBacktest({ ticker: ticker.trim().toUpperCase(), fast, slow, years });
      if (r?.ok) d = r; else { d = null; error = r?.error ?? 'backtest failed'; }
    } catch { d = null; error = 'backtest failed'; }
    finally { busy = false; }
  }

  // map both curves onto one viewBox with a shared y-scale
  const W = 640, H = 200, PAD = 6;
  function path(y, lo, hi) {
    const n = y.length;
    const sx = (i) => PAD + (i / (n - 1)) * (W - 2 * PAD);
    const sy = (v) => H - PAD - ((v - lo) / (hi - lo || 1)) * (H - 2 * PAD);
    return y.map((v, i) => `${i ? 'L' : 'M'}${sx(i).toFixed(1)},${sy(v).toFixed(1)}`).join('');
  }
  const chart = $derived.by(() => {
    if (!d) return null;
    const a = d.strategy.y, b = d.buy_hold.y;
    const lo = Math.min(...a, ...b), hi = Math.max(...a, ...b);
    const sy1 = H - PAD - ((1 - lo) / (hi - lo || 1)) * (H - 2 * PAD); // start = 1.0 baseline
    return { strat: path(a, lo, hi), hold: path(b, lo, hi), base: sy1 };
  });

  const sgn = (n) => (n > 0 ? '+' : '') + n + '%';
</script>

<div class="bt-form">
  <input class="bt-in bt-ticker" bind:value={ticker} placeholder="SPY" list="bt-tickers"
    style="text-transform:uppercase" autocomplete="off" spellcheck="false" aria-label="Ticker"
    onkeydown={(e) => { if (e.key === 'Enter') run(); }} />
  <datalist id="bt-tickers">
    <option value="SPY">S&P 500</option>
    {#each $holdings ?? [] as h (h.ticker)}<option value={h.ticker}>{h.company_name}</option>{/each}
  </datalist>
  <label class="bt-lbl">fast <input class="bt-in bt-num" type="number" min="2" max="200" bind:value={fast} aria-label="Fast SMA" /></label>
  <label class="bt-lbl">slow <input class="bt-in bt-num" type="number" min="3" max="300" bind:value={slow} aria-label="Slow SMA" /></label>
  <label class="bt-lbl">yrs <input class="bt-in bt-num" type="number" min="1" max="15" bind:value={years} aria-label="Years" /></label>
  <button class="btn btn-line btn-sm" onclick={run} disabled={busy}>{busy ? 'running…' : 'run'}</button>
</div>

{#if error}<div class="bt-err" role="alert">{error}</div>{/if}

{#if d && chart}
  <svg class="bt-chart" viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-label="Equity curves">
    <line x1="0" y1={chart.base} x2={W} y2={chart.base} class="bt-base" />
    <path d={chart.hold} class="bt-hold" />
    <path d={chart.strat} class="bt-strat" />
  </svg>
  <div class="bt-legend">
    <span class="bt-key bt-key-strat">SMA {d.params.fast}/{d.params.slow} on {d.ticker}</span>
    <span class="bt-key bt-key-hold">buy & hold</span>
  </div>
  <div class="bt-stats">
    <div><b class:up={d.stats.strat_return > 0} class:down={d.stats.strat_return < 0}>{sgn(d.stats.strat_return)}</b><span>strategy</span></div>
    <div><b class:up={d.stats.hold_return > 0} class:down={d.stats.hold_return < 0}>{sgn(d.stats.hold_return)}</b><span>buy & hold</span></div>
    <div><b>{d.stats.strat_max_dd}%</b><span>strat max dd</span></div>
    <div><b>{d.stats.hold_max_dd}%</b><span>hold max dd</span></div>
    <div><b>{d.stats.trades}</b><span>trades</span></div>
    <div><b>{d.stats.exposure_pct}%</b><span>time in market</span></div>
  </div>
  <div class="bt-note">signal trades next-day close (no look-ahead) · no fees, slippage, or taxes — reality is worse</div>
{:else if !error}
  <div class="bt-empty">pick a ticker and run — does a moving-average cross beat just holding?</div>
{/if}

<style>
  .bt-form { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
  .bt-in { box-sizing: border-box; height: 30px; padding: 0 9px; border: var(--bw) solid var(--ink);
    border-radius: var(--r); background: transparent; outline: none; color: var(--text);
    font-family: var(--mono); font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .bt-ticker { width: 90px; }
  .bt-num { width: 58px; -moz-appearance: textfield; appearance: textfield; }
  .bt-num::-webkit-outer-spin-button, .bt-num::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
  .bt-lbl { display: inline-flex; align-items: center; gap: 6px; font-family: var(--mono);
    font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }

  .bt-chart { width: 100%; height: 200px; display: block; }
  .bt-base { stroke: var(--hairline); stroke-width: 1; }
  .bt-strat { fill: none; stroke: var(--brand); stroke-width: 2; }
  .bt-hold { fill: none; stroke: var(--muted); stroke-width: 1.5; stroke-dasharray: 4 4; }

  .bt-legend { display: flex; gap: 18px; font-family: var(--mono); font-size: 10.5px; font-weight: 700; color: var(--muted); }
  .bt-key::before { content: ''; display: inline-block; width: 14px; height: 2px; margin-right: 6px; vertical-align: middle; }
  .bt-key-strat::before { background: var(--brand); }
  .bt-key-hold::before { background: var(--muted); }

  .bt-stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
  .bt-stats > div { display: flex; flex-direction: column; gap: 2px; padding: 8px 10px;
    border: var(--bw) solid var(--hairline); border-radius: var(--r); min-width: 0; }
  .bt-stats b { font-family: var(--mono); font-size: 15px; font-weight: 800; color: var(--ink);
    font-variant-numeric: tabular-nums; }
  .bt-stats b.up { color: var(--gain); }
  .bt-stats b.down { color: var(--loss); }
  .bt-stats span { font-family: var(--mono); font-size: 9px; font-weight: 700; color: var(--muted);
    text-transform: uppercase; letter-spacing: .08em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .bt-note, .bt-empty, .bt-err { font-family: var(--mono); font-size: 10.5px; color: var(--muted); }
  .bt-err { color: var(--loss); font-weight: 700; }

  @media (max-width: 900px) { .bt-stats { grid-template-columns: repeat(3, 1fr); } }
</style>
