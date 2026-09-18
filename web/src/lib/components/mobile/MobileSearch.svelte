<script>
  // Search results for the phone home — the strip that owns the query lives in
  // MobileHome; this is the list under it. Market results while typing,
  // Recent → Your holdings → Watchlist when the query is empty. Debounce and
  // sequencing mirror the desktop stage; rows are the shared .ss-* rules.
  import { api } from '$lib/api.js';
  import { holdings, watchlist, openSearchResult } from '$lib/stores.js';
  import TickerBadge from '../TickerBadge.svelte';

  let { q = '' } = $props();

  const RECENTS_KEY = 'sprout-recent-searches';
  const loadRecents = () => {
    try { return JSON.parse(localStorage.getItem(RECENTS_KEY)) ?? []; } catch { return []; }
  };

  let results = $state([]);
  let loading = $state(false);
  let recents = $state(loadRecents());

  let seq = 0;
  let timer = null;
  $effect(() => {
    const query = q.trim();
    if (timer) clearTimeout(timer);
    if (!query) { results = []; loading = false; return; }
    loading = true;
    const mine = ++seq;
    timer = setTimeout(async () => {
      try {
        const r = await api.search(query);
        if (mine !== seq) return;
        results = r.results ?? [];
      } catch {
        if (mine === seq) results = [];
      } finally {
        if (mine === seq) loading = false;
      }
    }, 180);
  });

  function pick(r) {
    if (!r) return;
    // remember the pick (dedupe by symbol, cap 8) for the empty-query state
    recents = [r, ...recents.filter((x) => x.symbol !== r.symbol)].slice(0, 8);
    try { localStorage.setItem(RECENTS_KEY, JSON.stringify(recents)); } catch {}
    // drop the keyboard before the sheet animates in
    document.activeElement?.blur?.();
    openSearchResult(r);
  }

  const heldRows = $derived(($holdings ?? []).map((c) => ({ symbol: c.ticker, name: c.company_name, type: 'Holding' })));
  const watchRows = $derived(($watchlist ?? []).map((w) => ({ symbol: w.ticker, name: w.name, type: 'Watching' })));

  const groups = $derived(q.trim()
    ? [{ title: null, rows: results }]
    : [
        { title: 'Recent', rows: recents },
        { title: 'Your holdings', rows: heldRows },
        { title: 'Watchlist', rows: watchRows },
      ].filter((g) => g.rows.length));
</script>

<div class="ms">
  {#if q.trim() && !loading && results.length === 0}
    <div class="ss-empty">No matches for “{q.trim()}”.</div>
  {:else if groups.length}
    {#each groups as g (g.title ?? 'results')}
      {#if g.title}<div class="ss-section">{g.title}</div>{/if}
      <ul class="ss-list">
        {#each g.rows as r (r.symbol)}
          <li>
            <button class="ss-item ms-item" onclick={() => pick(r)}>
              <span class="ss-sym"><TickerBadge sym={r.symbol} size="md" /></span>
              <span class="ss-name">{r.name}</span>
              <span class="ss-meta"><span>{r.type ?? ''}</span>{#if r.exchange}<span>{r.exchange}</span>{/if}</span>
            </button>
          </li>
        {/each}
      </ul>
    {/each}
  {:else if !q.trim()}
    <div class="ss-empty">Search the whole market, not just your holdings.</div>
  {/if}
</div>

<style>
  .ms { padding-top: 4px; }
  .ms :global(.ss-list) { padding: 0; }
  .ms :global(.ss-section) { padding: 14px 4px 4px; }
  .ms :global(.ss-empty) { padding: 18px 4px; }
  /* roomy touch rows; no hover state on the phone, a press tint instead */
  .ms-item { min-height: 48px; padding: 10px 4px; border-radius: 0;
    border-bottom: var(--bw) solid var(--hairline); }
  .ms-item:active { background: var(--hover); }
</style>
