<script>
  // Options module, lesson one: the payoff diagram. Single leg at expiry —
  // P/L per share vs the underlying price, with breakeven and the max
  // gain/loss that define every option position. Pure client-side math.
  // Next rungs: multi-leg spreads, then the greeks (time + vol, not expiry).
  let side = $state('long');   // 'long' | 'short'
  let kind = $state('call');   // 'call' | 'put'
  let strike = $state(100);
  let premium = $state(5);

  const pl = (S) => {
    const intrinsic = kind === 'call' ? Math.max(S - strike, 0) : Math.max(strike - S, 0);
    const long = intrinsic - premium;
    return side === 'long' ? long : -long;
  };

  const breakeven = $derived(kind === 'call' ? strike + premium : strike - premium);
  const maxGain = $derived.by(() => {
    if (side === 'long') return kind === 'call' ? 'unlimited' : `$${(strike - premium).toFixed(2)}`;
    return `$${Number(premium).toFixed(2)}`;
  });
  const maxLoss = $derived.by(() => {
    if (side === 'long') return `$${Number(premium).toFixed(2)}`;
    return kind === 'call' ? 'unlimited' : `$${(strike - premium).toFixed(2)}`;
  });

  // chart: S from 50% to 150% of strike
  const W = 320, H = 150, PAD = 8, N = 96;
  const chart = $derived.by(() => {
    const k = Number(strike) || 1;
    const lo = k * 0.5, hi = k * 1.5;
    const ys = Array.from({ length: N + 1 }, (_, i) => pl(lo + ((hi - lo) * i) / N));
    const yMin = Math.min(...ys), yMax = Math.max(...ys);
    const span = yMax - yMin || 1;
    const sx = (i) => PAD + (i / N) * (W - 2 * PAD);
    const sy = (v) => H - PAD - ((v - yMin) / span) * (H - 2 * PAD);
    return {
      line: ys.map((v, i) => `${i ? 'L' : 'M'}${sx(i).toFixed(1)},${sy(v).toFixed(1)}`).join(''),
      zero: sy(0),
      bex: yMin <= 0 && yMax >= 0 ? sx(((breakeven - lo) / (hi - lo)) * N) : null,
      kx: sx(((k - lo) / (hi - lo)) * N),
    };
  });
</script>

<div class="po-form">
  <div class="po-seg" role="group" aria-label="Side">
    <button class="btn btn-sm" class:on={side === 'long'} onclick={() => (side = 'long')}>long</button>
    <button class="btn btn-sm" class:on={side === 'short'} onclick={() => (side = 'short')}>short</button>
  </div>
  <div class="po-seg" role="group" aria-label="Type">
    <button class="btn btn-sm" class:on={kind === 'call'} onclick={() => (kind = 'call')}>call</button>
    <button class="btn btn-sm" class:on={kind === 'put'} onclick={() => (kind = 'put')}>put</button>
  </div>
  <label class="po-lbl">strike <input class="po-in" type="number" min="1" step="1" bind:value={strike} aria-label="Strike" /></label>
  <label class="po-lbl">premium <input class="po-in" type="number" min="0" step="0.5" bind:value={premium} aria-label="Premium" /></label>
</div>

<svg class="po-chart" viewBox="0 0 {W} {H}" preserveAspectRatio="none"
  aria-label="P/L at expiry vs underlying price">
  <line x1="0" y1={chart.zero} x2={W} y2={chart.zero} class="po-zero" />
  <line x1={chart.kx} y1="0" x2={chart.kx} y2={H} class="po-strike" />
  {#if chart.bex != null}<circle cx={chart.bex} cy={chart.zero} r="3.5" class="po-be" />{/if}
  <path d={chart.line} class="po-line" />
</svg>

<div class="po-stats">
  <span>breakeven <b>${breakeven.toFixed(2)}</b></span>
  <span>max gain <b class="up">{maxGain}</b></span>
  <span>max loss <b class="down">{maxLoss}</b></span>
</div>
<div class="po-note">P/L per share at expiry · dotted vertical = strike · dot = breakeven</div>

<style>
  .po-form { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
  .po-seg { display: inline-flex; gap: 4px; }
  .po-lbl { display: inline-flex; align-items: center; gap: 6px; font-family: var(--mono);
    font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }
  .po-in { box-sizing: border-box; width: 64px; height: 30px; padding: 0 9px;
    border: var(--bw) solid var(--ink); border-radius: var(--r); background: transparent; outline: none;
    color: var(--text); font-family: var(--mono); font-size: 12px; font-weight: 700;
    font-variant-numeric: tabular-nums; -moz-appearance: textfield; appearance: textfield; }
  .po-in::-webkit-outer-spin-button, .po-in::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

  .po-chart { width: 100%; height: 150px; display: block; }
  .po-line { fill: none; stroke: var(--brand); stroke-width: 2; }
  .po-zero { stroke: var(--hairline); stroke-width: 1; }
  .po-strike { stroke: var(--muted); stroke-width: 1; stroke-dasharray: 3 4; opacity: .6; }
  .po-be { fill: var(--ink); }

  .po-stats { display: flex; flex-wrap: wrap; gap: 6px 18px; font-family: var(--mono); font-size: 11px;
    font-weight: 500; color: var(--muted); }
  .po-stats b { font-weight: 800; color: var(--ink); font-variant-numeric: tabular-nums; }
  .po-stats b.up { color: var(--gain); }
  .po-stats b.down { color: var(--loss); }
  .po-note { font-family: var(--mono); font-size: 10.5px; color: var(--muted); }
</style>
