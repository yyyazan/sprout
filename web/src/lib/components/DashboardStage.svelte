<script>
  // The dashboard's MAIN widget — a stage with three modes instead of
  // full-screen overlays: the portfolio chart at rest, the stock view inline
  // when a holding/search result is opened, and an inline search panel for ⌘K.
  import PortfolioChart from './PortfolioChart.svelte';
  import StockPanel from './StockPanel.svelte';
  import { api } from '$lib/api.js';
  import { detail, searchOpen, holdings, closeStock, closeSearch, openSearchResult } from '$lib/stores.js';

  let { equity = { x: [], y: [] }, spy = null, twr = null, netInvested = null } = $props();

  // search wins over an open stock view (⌘K should always summon the palette);
  // closing search falls back to the stock still in $detail, then the chart
  const mode = $derived($searchOpen ? 'search' : $detail ? 'stock' : 'portfolio');

  // ── inline search (same behavior as the ⌘K palette, no scrim) ──
  let q = $state('');
  let results = $state([]);
  let active = $state(0);
  let loading = $state(false);
  let input = $state();

  const quick = $derived(($holdings ?? []).map((c) => ({ symbol: c.ticker, name: c.company_name, type: 'Holding' })));
  const list = $derived(q.trim() ? results : quick);

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
        active = 0;
      } catch {
        if (mine === seq) results = [];
      } finally {
        if (mine === seq) loading = false;
      }
    }, 180);
  });

  // focus the input each time search mode opens; reset stale queries
  $effect(() => {
    if (mode === 'search') {
      q = '';
      queueMicrotask(() => input?.focus());
    }
  });

  function pick(r) { if (r) openSearchResult(r); }
  function onKey(e) {
    if (e.key === 'Escape') { closeSearch(); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, list.length - 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); }
    else if (e.key === 'Enter') { e.preventDefault(); pick(list[active]); }
  }
</script>

<!-- stock mode renders the widget grid bare on the page paper; search keeps a card shell -->
<section class="stage" class:stage-card={mode === 'search'} class:stage-portfolio={mode === 'portfolio'}>
  {#if mode === 'stock'}
    {#key $detail.ticker}
      <div class="stage-in stage-widgets">
        <StockPanel ticker={$detail.ticker} name={$detail.name} holding={$detail.holding} onClose={() => closeStock()} glyph="←" />
      </div>
    {/key}
  {:else if mode === 'search'}
    <div class="stage-in stage-search">
      <div class="ss-bar">
        <span class="ss-icon" aria-hidden="true">⌕</span>
        <input
          bind:this={input}
          bind:value={q}
          onkeydown={onKey}
          type="text"
          placeholder="Search any stock — ticker or company…"
          autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
        {#if loading}<span class="ss-spin" aria-hidden="true"></span>{/if}
        <button class="ss-esc" onclick={() => closeSearch()}>esc</button>
      </div>
      {#if q.trim() && !loading && results.length === 0}
        <div class="ss-empty">No matches for “{q.trim()}”.</div>
      {:else if list.length}
        {#if !q.trim()}<div class="ss-section">Your holdings</div>{/if}
        <ul class="ss-list" role="listbox">
          {#each list as r, i (r.symbol)}
            <li>
              <button class="ss-item" class:active={i === active} role="option" aria-selected={i === active}
                      onmouseenter={() => (active = i)} onclick={() => pick(r)}>
                <span class="ss-sym">{r.symbol}</span>
                <span class="ss-name">{r.name}</span>
                <span class="ss-meta">{r.type}{#if r.exchange} · {r.exchange}{/if}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else if !q.trim()}
        <div class="ss-empty">Search the whole market — not just your holdings.</div>
      {/if}
    </div>
  {:else}
    <div class="stage-in stage-chart">
      <PortfolioChart {equity} {spy} {twr} {netInvested} />
    </div>
  {/if}
</section>

<style>
  .stage { min-height: 0; height: 100%; display: flex; flex-direction: column; }
  /* portfolio chart: a fixed-height widget so a tall sibling (e.g. market news
     loading into the rail) can't stretch the shared grid row and grow the graph.
     stock + search modes keep height:100% (page-scrolling grid / bounded card). */
  .stage-portfolio { height: var(--stage-h, 520px); }
  /* search brings a card shell; stock mode is a bare widget grid; the chart card is its own chrome */
  .stage-card { background: var(--surface); border: var(--bw) solid var(--ink);
    border-radius: calc(var(--r) + 2px); box-shadow: var(--sh); overflow: hidden; }
  .stage-in { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column;
    animation: stage-in .18s ease; }
  @keyframes stage-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
  /* let the widget grid set its own height — the page scrolls, not the stage */
  .stage-widgets { display: block; min-height: 0; }
  .stage-chart { min-height: 0; }

  /* ── inline search ── */
  .stage-search { overflow: hidden; }
  .ss-bar { display: flex; align-items: center; gap: 10px; padding: 14px 16px; border-bottom: var(--bw) solid var(--ink); }
  .ss-icon { font-size: 18px; color: var(--muted); }
  .ss-bar input { flex: 1; border: 0; outline: 0; background: transparent; color: var(--text);
    font-family: var(--sans); font-size: 17px; font-weight: 600; min-width: 0; }
  .ss-bar input::placeholder { color: var(--muted); font-weight: 500; }
  .ss-esc { font-family: var(--mono); font-size: 10px; color: var(--muted); border: 1.5px solid var(--muted);
    border-radius: 4px; padding: 1px 5px; background: transparent; cursor: pointer; }
  .ss-spin { width: 13px; height: 13px; border: 2px solid color-mix(in srgb, var(--ink) 25%, transparent);
    border-top-color: var(--brand); border-radius: 50%; animation: ss-rot .6s linear infinite; }
  @keyframes ss-rot { to { transform: rotate(360deg); } }
  .ss-list { list-style: none; margin: 0; padding: 6px; overflow-y: auto; flex: 1 1 auto; min-height: 0; }
  .ss-item { width: 100%; display: flex; align-items: baseline; gap: 12px; padding: 10px 12px; cursor: pointer;
    border: 0; border-radius: var(--r); background: transparent; color: var(--ink); text-align: left; font: inherit; }
  .ss-item.active { background: var(--hover); }
  .ss-sym { flex: 0 0 auto; font-family: var(--mono); font-weight: 700; font-size: 14px; min-width: 64px; }
  .ss-name { flex: 1; min-width: 0; font-family: var(--sans); font-size: 13px; color: var(--text);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ss-meta { flex: 0 0 auto; font-family: var(--mono); font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
  .ss-empty { padding: 18px 18px 20px; font-family: var(--mono); font-size: 13px; color: var(--muted); }
  .ss-section { padding: 12px 18px 2px; font-family: var(--sans); font-size: 9.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }
</style>
