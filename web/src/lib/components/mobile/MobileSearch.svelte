<script>
  // Mobile Search pane — the heaviest-used surface on the phone, so it's a
  // persistent pane (not a ⌘K palette): sticky input on top, market results
  // while typing, and Recents → Holdings → Watchlist when the query is empty.
  // Debounce/sequence logic mirrors the desktop stage's inline search.
  import { api } from '$lib/api.js';
  import { holdings, watchlist, openSearchResult } from '$lib/stores.js';

  const RECENTS_KEY = 'sprout-recent-searches';
  const loadRecents = () => {
    try { return JSON.parse(localStorage.getItem(RECENTS_KEY)) ?? []; } catch { return []; }
  };

  let q = $state('');
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
</script>

<div class="ms-bar">
  <span class="ms-icon" aria-hidden="true">⌕</span>
  <input class="ms-input" type="search" bind:value={q}
    placeholder="Search any stock or ETF…"
    autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
    enterkeyhint="search" aria-label="Search stocks" />
  {#if loading}<span class="ms-spin" aria-hidden="true"></span>{/if}
  {#if q}<button class="ms-clear" onclick={() => (q = '')} aria-label="Clear search">✕</button>{/if}
</div>

{#if q.trim()}
  {#if !loading && results.length === 0}
    <div class="ms-empty">No matches for “{q.trim()}”.</div>
  {:else}
    <ul class="ms-list">
      {#each results as r (r.symbol)}
        <li><button class="ms-item" onclick={() => pick(r)}>
          <span class="ms-sym">{r.symbol}</span>
          <span class="ms-name">{r.name}</span>
          <span class="ms-meta">{r.type}{#if r.exchange} · {r.exchange}{/if}</span>
        </button></li>
      {/each}
    </ul>
  {/if}
{:else}
  {#if recents.length}
    <div class="ms-section">Recent</div>
    <ul class="ms-list">
      {#each recents as r (r.symbol)}
        <li><button class="ms-item" onclick={() => pick(r)}>
          <span class="ms-sym">{r.symbol}</span>
          <span class="ms-name">{r.name}</span>
          <span class="ms-meta">{r.type ?? ''}</span>
        </button></li>
      {/each}
    </ul>
  {/if}
  {#if heldRows.length}
    <div class="ms-section">Your holdings</div>
    <ul class="ms-list">
      {#each heldRows as r (r.symbol)}
        <li><button class="ms-item" onclick={() => pick(r)}>
          <span class="ms-sym">{r.symbol}</span>
          <span class="ms-name">{r.name}</span>
          <span class="ms-meta">{r.type}</span>
        </button></li>
      {/each}
    </ul>
  {/if}
  {#if watchRows.length}
    <div class="ms-section">Watchlist</div>
    <ul class="ms-list">
      {#each watchRows as r (r.symbol)}
        <li><button class="ms-item" onclick={() => pick(r)}>
          <span class="ms-sym">{r.symbol}</span>
          <span class="ms-name">{r.name}</span>
          <span class="ms-meta">{r.type}</span>
        </button></li>
      {/each}
    </ul>
  {/if}
  {#if !recents.length && !heldRows.length}
    <div class="ms-empty">Search the whole market — not just your holdings.</div>
  {/if}
{/if}

<style>
  /* sticky search bar: stays pinned while results scroll under it. Solid page
     background so list rows don't ghost through; clears the status bar. */
  .ms-bar { position: sticky; top: 0; z-index: 5; display: flex; align-items: center; gap: 10px;
    background: var(--bg); margin: 0 -14px; padding: calc(10px + env(safe-area-inset-top)) 14px 10px;
    border-bottom: var(--bw) solid var(--ink); }
  .ms-icon { font-size: 18px; color: var(--muted); flex: 0 0 auto; }
  /* 16px minimum so iOS Safari doesn't zoom the page on focus */
  .ms-input { flex: 1 1 auto; min-width: 0; border: 0; outline: 0; background: transparent;
    color: var(--text); font-family: var(--sans); font-size: 16px; font-weight: 600;
    -webkit-appearance: none; appearance: none; }
  .ms-input::placeholder { color: var(--muted); font-weight: 500; }
  .ms-input::-webkit-search-cancel-button { -webkit-appearance: none; }
  .ms-clear { flex: 0 0 auto; width: 26px; height: 26px; display: grid; place-items: center;
    border: var(--bw) solid var(--hairline); border-radius: 999px; background: transparent;
    color: var(--muted); font-size: 11px; cursor: pointer; }
  .ms-spin { flex: 0 0 auto; width: 13px; height: 13px;
    border: 2px solid color-mix(in srgb, var(--ink) 25%, transparent);
    border-top-color: var(--brand); border-radius: 50%; animation: ms-rot .6s linear infinite; }
  @keyframes ms-rot { to { transform: rotate(360deg); } }

  .ms-section { padding: 16px 2px 4px; font-family: var(--sans); font-size: 9.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }
  .ms-list { list-style: none; margin: 0; padding: 4px 0 0; }
  /* roomy 48px touch rows */
  .ms-item { width: 100%; display: flex; align-items: baseline; gap: 12px; min-height: 48px;
    padding: 12px 4px; cursor: pointer; border: 0; border-bottom: var(--bw) solid var(--hairline);
    border-radius: 0; background: transparent; color: var(--ink); text-align: left; font: inherit; }
  .ms-item:active { background: var(--hover); }
  .ms-sym { flex: 0 0 auto; font-family: var(--mono); font-weight: 700; font-size: 15px; min-width: 64px; }
  .ms-name { flex: 1; min-width: 0; font-family: var(--sans); font-size: 13px; color: var(--text);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ms-meta { flex: 0 0 auto; font-family: var(--mono); font-size: 10px; color: var(--muted);
    text-transform: uppercase; letter-spacing: .04em; }
  .ms-empty { padding: 22px 4px; font-family: var(--mono); font-size: 13px; color: var(--muted); }

  @media (prefers-reduced-motion: reduce) { .ms-spin { animation: none; } }
</style>
