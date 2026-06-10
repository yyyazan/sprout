<script>
  // Market pulse — "how's the market" at a glance. Three index cells split by
  // hairlines (big day-% as the hero figure), then market headlines as
  // neo-brutalist underlined links.
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { openStock } from '$lib/stores.js';

  let m = $state(null);
  onMount(async () => {
    try { m = await api.market(); } catch { m = { indices: [], news: [] }; }
  });

  const pct = (n) => (n == null ? '—' : (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(2) + '%');
  const px = (n) => (n == null ? '—' : n >= 1000 ? Math.round(n).toLocaleString('en-US') : n.toFixed(2));
  const ago = (at) => {
    if (at == null) return '';
    const s = Date.now() / 1000 - at;
    if (s < 3600) return Math.max(1, Math.round(s / 60)) + 'm';
    if (s < 86400) return Math.round(s / 3600) + 'h';
    return Math.round(s / 86400) + 'd';
  };
</script>

<div class="glass-card pulse">
  <div class="pulse-h">market</div>
  {#if m === null}
    <div class="pulse-empty">Loading…</div>
  {:else}
    <div class="idx-row">
      {#each m.indices as ix (ix.symbol)}
        <button class="idx" onclick={() => openStock({ ticker: ix.symbol, name: ix.label, holding: null })}>
          <span class="idx-label">{ix.label}</span>
          <span class="idx-pct {(ix.dayPct ?? 0) >= 0 ? 'up' : 'down'}">{pct(ix.dayPct)}</span>
          <span class="idx-px">{px(ix.price)}</span>
        </button>
      {/each}
    </div>
    {#if m.news?.length}
      <div class="pulse-news">
        {#each m.news as n}
          <a class="pn-item" href={n.url} target="_blank" rel="noopener noreferrer">
            <span class="pn-title">{n.title}</span>
            <span class="pn-meta">{n.source}{#if n.at} · {ago(n.at)} ago{/if}</span>
          </a>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  .pulse { display: flex; flex-direction: column; gap: 12px; padding: 13px 15px 14px; }
  .pulse-h { font-family: var(--sans); font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .12em; color: var(--muted); }
  .pulse-empty { font-family: var(--mono); font-size: 11px; color: var(--muted); }

  /* three cells split by hairlines — no boxes, the % is the hero */
  .idx-row { display: grid; grid-template-columns: repeat(3, 1fr); }
  .idx { display: flex; flex-direction: column; gap: 3px; align-items: flex-start; min-width: 0; cursor: pointer;
    padding: 2px 0 2px 12px; font: inherit; text-align: left; color: var(--ink);
    background: transparent; border: 0; border-left: var(--bw) solid var(--hairline);
    transition: border-color .15s ease; }
  .idx:first-child { border-left: 0; padding-left: 0; }
  .idx:hover { border-left-color: var(--ink); }
  .idx:hover .idx-label { color: var(--ink); }
  .idx-label { font-family: var(--sans); font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .06em; color: var(--muted); white-space: nowrap; transition: color .15s ease; }
  .idx-pct { font-family: var(--mono); font-size: 17px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1; }
  .idx-px { font-family: var(--mono); font-size: 10px; color: var(--muted); font-variant-numeric: tabular-nums; }

  /* headlines — neo-brutalist links: always underlined, ink on hover */
  .pulse-news { display: flex; flex-direction: column; border-top: var(--bw) solid var(--hairline); padding-top: 4px; }
  .pn-item { display: flex; flex-direction: column; gap: 3px; min-width: 0; text-decoration: none; padding: 8px 0;
    border-top: var(--bw) solid var(--hairline); }
  .pn-item:first-child { border-top: 0; }
  .pn-title { font-family: var(--sans); font-size: 11.5px; font-weight: 600; line-height: 1.4; color: var(--ink);
    text-decoration: underline; text-underline-offset: 2.5px;
    text-decoration-color: color-mix(in srgb, var(--ink) 30%, transparent);
    transition: text-decoration-color .15s ease;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .pn-item:hover .pn-title { text-decoration-color: var(--ink); }
  .pn-meta { font-family: var(--mono); font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }

  .up { color: var(--gain); } .down { color: var(--loss); }
</style>
