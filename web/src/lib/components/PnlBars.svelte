<script>
  import { GAIN, LOSS } from '$lib/charts.js';
  import { fmt } from '$lib/format.js';

  // Unrealized P&L by ticker — diverging horizontal bars around a center zero.
  // Negatives grow left, positives grow right; bar length is |value| / maxAbs.
  // Long bars (no room for an outside label) get the label drawn inside, in white.
  let { tickers, values } = $props();

  const INSIDE_AT = 40; // half-track % beyond which the label goes inside the bar

  let maxAbs = $derived(Math.max(1, ...values.map((v) => Math.abs(v))));
  let rows = $derived(
    tickers.map((t, i) => {
      const v = values[i];
      const pct = (Math.abs(v) / maxAbs) * 50; // half-track is 50%
      return { ticker: t, value: v, pct, gain: v >= 0, color: v >= 0 ? GAIN : LOSS, inside: pct >= INSIDE_AT };
    })
  );
</script>

<div class="pnl-bars">
  {#each rows as r}
    <div class="pnl-row">
      <span class="pnl-ticker">{r.ticker}</span>
      <div class="pnl-track">
        <span class="pnl-zero"></span>
        <span
          class="pnl-bar"
          style="background:{r.color}; width:{r.pct}%; {r.gain ? 'left:50%' : `right:50%`}"
        ></span>
        <span
          class="pnl-val"
          class:left={!r.gain}
          class:inside={r.inside}
          style="color:{r.inside ? '#fff' : r.color}; {r.gain
            ? `left:calc(50% + ${r.pct}% ${r.inside ? '- 6px' : '+ 6px'})`
            : `right:calc(50% + ${r.pct}% ${r.inside ? '- 6px' : '+ 6px'})`}"
        >{fmt.signedMoney2(r.value)}</span>
      </div>
    </div>
  {/each}
</div>
