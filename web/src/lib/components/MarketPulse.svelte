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
  <div class="kpi-label">Market</div>
  {#if m === null}
    <div class="pulse-empty">Loading…</div>
  {:else}
    <div class="idx-row">
      {#each m.indices as ix (ix.symbol)}
        <button class="idx" onclick={() => openStock({ ticker: ix.symbol, name: ix.label, holding: null })}>
          <span class="idx-label">{ix.label}</span>
          <span class="idx-pct pct-pill {(ix.dayPct ?? 0) >= 0 ? 'up' : 'down'}">{pct(ix.dayPct)}</span>
          <span class="idx-px">{px(ix.price)}</span>
        </button>
      {/each}
    </div>
    {#if m.news?.length}
      <div class="pulse-news">
        {#each m.news as n}
          <a class="pn-item" href={n.url} target="_blank" rel="noopener noreferrer">
            <span class="pn-title">{n.title}</span>
            <span class="pn-meta"><span class="pn-src">{n.source}</span>{#if n.at}<span>{ago(n.at)} ago</span>{/if}</span>
          </a>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  .pulse { display: flex; flex-direction: column; gap: 6px; }
  .pulse .kpi-label { margin-bottom: 0; }
  .pulse-empty { font-size: var(--fs-body); color: var(--muted); }

  /* three cells — the gap separates, the % is the hero */
  .idx-row { display: grid; grid-template-columns: repeat(3, 1fr); column-gap: 12px; margin-top: 4px; }
  .idx { display: flex; flex-direction: column; gap: 3px; align-items: flex-start; min-width: 0; cursor: pointer;
    padding: 2px 0; font: inherit; text-align: left; color: var(--ink); background: transparent; border: 0; }
  .idx:hover .idx-label { color: var(--ink); }
  .idx-label { font-size: var(--fs-body); font-weight: 500; color: var(--muted); white-space: nowrap; transition: color .15s ease; }
  .idx-pct { font-family: var(--num); font-size: 16px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.1; }
  .idx-px { font-family: var(--num); font-size: var(--fs-meta); font-weight: 500; color: var(--muted); font-variant-numeric: tabular-nums; }

  /* headlines — always underlined, ink on hover. Hairlines between rows only. */
  .pulse-news { display: flex; flex-direction: column; margin-top: 8px; }
  .pn-item { display: flex; flex-direction: column; gap: 4px; min-width: 0; text-decoration: none; padding: 9px 0;
    border-top: var(--bw) solid var(--hairline); }
  .pn-item:first-child { border-top: 0; }
  .pn-title { font-size: var(--fs-body); font-weight: 500; line-height: 1.4; color: var(--ink);
    text-decoration: underline; text-underline-offset: 2.5px;
    text-decoration-color: color-mix(in srgb, var(--ink) 30%, transparent);
    transition: text-decoration-color .15s ease;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .pn-item:hover .pn-title { text-decoration-color: var(--ink); }
  /* source left, age right — the gap separates, no dot */
  .pn-meta { display: flex; justify-content: space-between; gap: 8px; font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  .pn-src { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .up { color: var(--gain); } .down { color: var(--loss); }
</style>
