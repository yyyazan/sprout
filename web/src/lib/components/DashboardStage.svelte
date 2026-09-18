<script>
  // The dashboard's MAIN widget — a stage with three modes instead of
  // full-screen overlays: the portfolio chart at rest, the stock view inline
  // when a holding/search result is opened, and an inline search panel for ⌘K.
  import PortfolioChart from './PortfolioChart.svelte';
  import StockPanel from './StockPanel.svelte';
  import TickerBadge from './TickerBadge.svelte';
  import { api } from '$lib/api.js';
  import { detail, searchOpen, holdings, closeStock, closeSearch, openSearch, openSearchResult } from '$lib/stores.js';

  let { equity = { x: [], y: [] }, spy = null, twr = null, netInvested = null } = $props();

  // search wins over an open stock view (⌘K should always summon the palette);
  // closing search falls back to the stock still in $detail, then the chart
  const mode = $derived($searchOpen ? 'search' : $detail ? 'stock' : 'portfolio');
  const atHome = $derived(mode === 'portfolio');

  // ── persistent search strip ──
  // Always the first thing in the stage, whatever's beneath it: an idle button
  // that opens search, or (in search mode) the live query input itself — same
  // shape and place either way, a Google-Finance-style top search bar.

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
<section class="stage" class:stage-portfolio={atHome}>
  <!-- persistent search strip: idle button (opens search) or the live query input -->
  {#if mode === 'search'}
    <div class="strip strip-active">
      <span class="strip-icon" aria-hidden="true">⌕</span>
      <input
        bind:this={input}
        bind:value={q}
        onkeydown={onKey}
        type="text"
        placeholder="Search"
        autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" />
      {#if loading}<span class="strip-spin" aria-hidden="true"></span>{/if}
      <button class="strip-esc" onclick={() => closeSearch()}>esc</button>
    </div>
  {:else}
    <button class="strip strip-idle" onclick={() => openSearch()}>
      <span class="strip-icon" aria-hidden="true">⌕</span>
      <span class="strip-ph">Search</span>
      <kbd class="strip-kbd">⌘K</kbd>
    </button>
  {/if}

  {#if mode === 'stock'}
    {#key $detail.ticker}
      <div class="stage-in stage-widgets">
        <StockPanel ticker={$detail.ticker} name={$detail.name} holding={$detail.holding} onClose={() => closeStock()} glyph="←" />
      </div>
    {/key}
  {:else if mode === 'search'}
    <div class="stage-in stage-search stage-card">
      {#if q.trim() && !loading && results.length === 0}
        <div class="ss-empty">No matches for “{q.trim()}”.</div>
      {:else if list.length}
        {#if !q.trim()}<div class="ss-section">Your holdings</div>{/if}
        <ul class="ss-list" role="listbox">
          {#each list as r, i (r.symbol)}
            <li>
              <button class="ss-item" class:active={i === active} role="option" aria-selected={i === active}
                      onmouseenter={() => (active = i)} onclick={() => pick(r)}>
                <span class="ss-sym"><TickerBadge sym={r.symbol} size="md" /></span>
                <span class="ss-name">{r.name}</span>
                <span class="ss-meta"><span>{r.type}</span>{#if r.exchange}<span>{r.exchange}</span>{/if}</span>
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
  .stage { min-height: 0; height: 100%; display: flex; flex-direction: column; gap: 16px; }
  /* portfolio chart: a fixed-height widget so a tall sibling (e.g. market news
     loading into the rail) can't stretch the shared grid row and grow the graph.
     stock + search modes keep height:100% (page-scrolling grid / bounded card). */
  .stage-portfolio { height: var(--stage-h, 520px); }

  /* ── persistent search strip ── */
  /* same box, same place, whatever mode the stage is in — idle button or live
     input, so opening/closing search never shifts anything else on the page */
  .strip { flex: 0 0 auto; display: flex; align-items: center; gap: 10px; min-width: 0;
    padding: 12px 16px; box-sizing: border-box; width: 100%; text-align: left;
    background: var(--surface); border: var(--bw) solid var(--ink); border-radius: var(--r);
    color: var(--ink); font: inherit; }
  .strip-idle { cursor: pointer; transition: box-shadow .12s ease, transform .12s ease; }
  .strip-idle:hover { box-shadow: var(--sh-pop); transform: translate(-1px, -1px); }
  .strip-idle:active { transform: none; box-shadow: none; }
  .strip-icon { font-size: 16px; color: var(--muted); flex: 0 0 auto; }
  .strip-ph { flex: 1; min-width: 0; font-size: 14px; font-weight: 500; color: var(--muted);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .strip-idle:hover .strip-ph { color: var(--ink); }
  .strip-kbd, .strip-esc { flex: 0 0 auto; font-family: var(--num); font-size: var(--fs-meta); font-weight: 500;
    line-height: 1; color: var(--muted); border: var(--bw) solid var(--muted); border-radius: 4px; padding: 3px 6px;
    background: transparent; }
  .strip-esc { cursor: pointer; }
  .strip-esc:hover { color: var(--ink); border-color: var(--ink); }
  .strip-active input { flex: 1; min-width: 0; border: 0; outline: 0; background: transparent;
    color: var(--text); font-size: 14px; font-weight: 500; }
  .strip-active input::placeholder { color: var(--muted); }
  .strip-spin { flex: 0 0 auto; width: 13px; height: 13px;
    border: 2px solid color-mix(in srgb, var(--ink) 25%, transparent);
    border-top-color: var(--brand); border-radius: 50%; animation: strip-rot .6s linear infinite; }
  @keyframes strip-rot { to { transform: rotate(360deg); } }

  /* search brings a card shell; stock mode is a bare widget grid; the chart card is its own chrome */
  .stage-card { background: var(--surface); border: var(--bw) solid var(--ink);
    border-radius: calc(var(--r) + 2px); box-shadow: var(--sh); overflow: hidden; }
  .stage-in { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column;
    animation: stage-in .18s ease; }
  @keyframes stage-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
  /* let the widget grid set its own height — the page scrolls, not the stage */
  .stage-widgets { display: block; min-height: 0; }
  .stage-chart { min-height: 0; }

  /* ── inline search results (the query input itself lives in .strip-active) ── */
  .stage-search { overflow: hidden; }
  .ss-list { list-style: none; margin: 0; padding: 6px; overflow-y: auto; flex: 1 1 auto; min-height: 0; }
  .ss-item { width: 100%; display: flex; align-items: baseline; gap: 12px; padding: 10px 12px; cursor: pointer;
    border: 0; border-radius: var(--r); background: transparent; color: var(--ink); text-align: left; font: inherit; }
  .ss-item.active { background: var(--hover); }
  .ss-sym { flex: 0 0 auto; min-width: 64px; }
  .ss-name { flex: 1; min-width: 0; font-size: 13px; font-weight: 500; color: var(--text);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ss-meta { flex: 0 0 auto; display: inline-flex; gap: 10px; font-size: var(--fs-meta); font-weight: 500; color: var(--muted); }
  .ss-empty { padding: 18px 18px 20px; font-size: 13px; font-weight: 500; color: var(--muted); }
  .ss-section { padding: 14px 18px 4px; font-size: var(--fs-body); font-weight: 600; color: var(--ink); }
</style>
