<script>
  // Colored ticker pill — solid brand/hashed color with legible text.
  // Google-Finance style; the one place chrome is intentionally colored.
  import { tickerColor, textOn } from '$lib/tickerColor.js';
  let { sym = '', size = 'sm' } = $props();
  const bg = $derived(tickerColor(sym));
  const fg = $derived(textOn(bg));
</script>

<span class="tkr-badge tkr-{size}" style="background:{bg};color:{fg};">{sym}</span>

<style>
  .tkr-badge { display: inline-block; font-family: var(--mono); font-weight: 700;
    letter-spacing: .02em; border-radius: var(--r); line-height: 1.1; white-space: nowrap; }
  .tkr-sm { font-size: 11px; padding: 2px 7px; }
  .tkr-md { font-size: 12.5px; padding: 3px 9px; }
</style>
