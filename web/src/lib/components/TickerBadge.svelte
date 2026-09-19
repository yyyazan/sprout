<script>
  // Colored ticker pill — solid brand/hashed color with legible text.
  // Google-Finance style; the one place chrome is intentionally colored.
  import { tickerColor, textOn } from '$lib/tickerColor.js';
  let { sym = '', size = 'sm' } = $props();
  const bg = $derived(tickerColor(sym));
  const fg = $derived(textOn(bg));
  // big: a darker/saturated brick of the same hue sits behind the pill,
  // offset like the system's --sh-pop press-shadow — no wrapper element
  // needed since box-shadow already inherits the pill's own border-radius.
  const brick = $derived(`color-mix(in srgb, ${bg} 60%, black)`);
</script>

<span class="tkr-badge tkr-{size}" style="background:{bg};color:{fg};--tkr-brick:{brick};">{sym}</span>

<style>
  /* the one uppercase element in the system — caps means ticker, so caps get tracking */
  .tkr-badge { display: inline-block; font-family: var(--num); font-weight: 700;
    letter-spacing: .04em; border-radius: var(--r); line-height: 1.1; white-space: nowrap; }
  .tkr-sm { font-size: 11px; padding: 2px 7px; }
  .tkr-md { font-size: 12.5px; padding: 3px 9px; }
  /* twice .tkr-md, brick-backed */
  .tkr-big { font-size: 25px; padding: 6px 18px; box-shadow: 6px 6px 0 var(--tkr-brick); }
</style>
