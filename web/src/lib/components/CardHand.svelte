<script>
  import { onMount, tick } from 'svelte';
  let { cards } = $props();

  onMount(async () => {
    await import('$lib/three/cards.js');
    await tick();
    if (window.initCardHand) window.initCardHand();
  });
</script>

<div class="card-hand-band">
  <div class="card-hand" id="card-hand">
    {#each cards as c, i}
      <div class="portfolio-card suit-{c.suit}" data-index={i} data-suit={c.suit}>
        <div class="card-inner">
          {#if c.is_joker}
            <div class="corner corner-tl"><span class="corner-rank">★</span><span class="corner-suit"></span></div>
            <div class="corner corner-br"><span class="corner-rank">★</span><span class="corner-suit"></span></div>
            <div class="card-center joker-center">
              <div class="joker-star">★</div>
              <div class="joker-word">{#each 'JOKER' as ch}<span>{ch}</span>{/each}</div>
              <div class="card-pct">${c.cash_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
              <div class="card-pct-label">free cash</div>
            </div>
          {:else}
            <div class="corner corner-tl"><span class="corner-rank">{c.rank}</span><span class="corner-suit">{c.suit_symbol}</span></div>
            <div class="corner corner-br"><span class="corner-rank">{c.rank}</span><span class="corner-suit">{c.suit_symbol}</span></div>
            <div class="card-center">
              <div class="card-logo-wrap">
                {#if c.domain}
                  <img class="card-logo" src="https://icons.duckduckgo.com/ip3/{c.domain}.ico" alt="" referrerpolicy="no-referrer" />
                {/if}
                <div class="card-logo-fallback">{c.ticker.slice(0, 2).toUpperCase()}</div>
              </div>
              <div class="card-ticker">{c.ticker}</div>
              <div class="card-name">{c.company_name}</div>
              <div class="card-pct">{c.position_pct.toFixed(1)}%</div>
              <div class="card-pct-label">of portfolio</div>
            </div>
          {/if}
        </div>
      </div>
    {/each}
  </div>
</div>
