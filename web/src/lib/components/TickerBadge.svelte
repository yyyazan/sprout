<script>
  // Colored ticker pill — solid brand/hashed color with legible text.
  // Google-Finance style; the one place chrome is intentionally colored.
  // Solid = a company. A fund (index or otherwise) isn't a company, so it's the
  // same pill as an ink outline: no fill, ink border, ink text.
  import { tickerColor, textOn } from '$lib/tickerColor.js';
  import { kinds } from '$lib/stores.js';
  // fund: force it (the /design sample); otherwise the kinds store decides
  let { sym = '', size = 'sm', fund: forced = null } = $props();
  const fund = $derived(forced ?? !!$kinds[sym]);
  const bg = $derived(tickerColor(sym));
  const fg = $derived(textOn(bg));
  // a darker/saturated brick of the same hue sits straight down behind the
  // pill on md — no wrapper element needed since box-shadow already inherits
  // the pill's own border-radius. Left off sm: it's dense-list sized, where
  // a shadow just reads as noise.
  const brick = $derived(`color-mix(in srgb, ${bg} 60%, black)`);
</script>

{#if fund}
  <span class="tkr-badge tkr-{size} tkr-fund">{sym}</span>
{:else}
  <span class="tkr-badge tkr-{size}" style="background:{bg};color:{fg};--tkr-brick:{brick};">{sym}</span>
{/if}

<style>
  /* the one uppercase element in the system — caps means ticker, so caps get tracking */
  .tkr-badge { display: inline-block; font-family: var(--num); font-weight: 700;
    letter-spacing: .04em; border-radius: var(--r); line-height: 1.1; white-space: nowrap; }
  .tkr-sm { font-size: 11px; padding: 2px 7px; }
  /* 15% over the old 12.5/3/9 */
  .tkr-md { font-size: 14.4px; padding: 3.5px 10.5px; box-shadow: 0 3px 0 var(--tkr-brick); }
  /* the border is inset so a fund badge is the same size as a solid one; no brick under md */
  .tkr-fund { background: transparent; color: var(--ink); box-shadow: inset 0 0 0 var(--bw) var(--ink); }
  .tkr-md.tkr-fund { box-shadow: inset 0 0 0 var(--bw) var(--ink); }
</style>
